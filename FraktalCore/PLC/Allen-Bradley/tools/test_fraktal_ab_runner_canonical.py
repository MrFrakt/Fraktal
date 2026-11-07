"""Shared runner C5b3 offline qualification: tower, seed preservation, disconnect lifecycle and genealogy."""
from __future__ import annotations

import contextlib
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import fraktal_ab_access as access
import fraktal_ab_canonical_live as live
import fraktal_ab_canonical_reader as reader
import fraktal_ab_declaration as decl
import fraktal_ab_fixture_reads as views
import fraktal_ab_genealogy_demo as legacy_genealogy
import fraktal_ab_genealogy_execute as genealogy_execute
import fraktal_ab_genealogy_s6_collapse_demo as profile
import fraktal_ab_generate as gen
import fraktal_ab_harness_documents as host_docs
from fraktal_ab_harness_process import attach
from fraktal_ab_harness_seed import record as record_seed
from fraktal_ab_live_medium import FileMedium
import fraktal_ab_mailbox as mb
import fraktal_ab_part_execute as part_execute
import fraktal_ab_press_execute as px
import fraktal_ab_signal_tower as tower
import fraktal_ab_tower_execute as tower_execute
from test_fraktal_ab_canonical_live import Clock, Replay
from test_fraktal_ab_harness_documents import Reader as ConfigViewReader

ROOT = Path(__file__).resolve().parents[4]
SESSION = ROOT / 'Specification/AllenBradley/Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04/Session'
APP = profile.application()


class CanonicalSignalTower(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = reader.load_json(SESSION / 'capture_canonical.json.gz')
        cls.expected = reader.snapshot(deepcopy(cls.capture))['values']

    def setUp(self):
        self.clock, self.replay, self.counters = Clock(), Replay(self.capture), []

        def counter(_):
            self.counters.append(1)
            return 0 if len(self.counters) == 1 else 2

        row_reader = live.CanonicalRowReader(self.capture, live.LeafBody(self.replay.raw), counter,
                                             clock_ns=self.clock, sleep=self.clock.sleep)
        read_row = row_reader.read_row

        def fresh(*args, **kwargs):
            self.counters.clear()
            return read_row(*args, **kwargs)

        row_reader.read_row = fresh
        self.session = views.FixtureReads(APP, row_reader)
        self.bound = patch.object(views, '_session', return_value=self.session)
        self.bound.start()
        self.addCleanup(self.bound.stop)

    def test_signal_tower_reads_exact_canonical_leaves_and_matches_sealed_capture(self):
        snap = tower_execute.snapshot(object(), APP)
        wanted_paths = {'Press/MachineState', *(f'Press/SignalTower/{n}' for n in tower.OUTPUTS)}
        self.assertEqual(set(self.replay.calls), wanted_paths)
        self.assertEqual(snap['MachineState'], self.expected['Press/MachineState'])
        for name in tower.OUTPUTS:
            self.assertIs(snap[f'SignalTower/{name}'], self.expected[f'Press/SignalTower/{name}'])

    def test_signal_tower_rejects_invalid_machine_state_or_non_boolean_lamp(self):
        original = views.values
        for bad_path, bad_val in (('Press/MachineState', 99),
                                  ('Press/MachineState', True),
                                  ('Press/SignalTower/TestActive', 1)):
            def corrupt(comm, paths, *, bad_path=bad_path, bad_val=bad_val, **kw):
                held = dict(original(comm, paths, **kw))
                held[bad_path] = bad_val
                return held

            with self.subTest(path=bad_path, value=bad_val), \
                    patch.object(views, 'values', side_effect=corrupt), \
                    self.assertRaisesRegex(ValueError, 'signal tower snapshot'):
                views.signal_tower(object(), app=APP)


class SeedDocumentsAndPreservation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.reader = ConfigViewReader()
        self.expected, self.epoch = host_docs.expected_documents(self.reader, 'Press')
        self.seed_dir = self.base / 'original-medium'
        medium = FileMedium(self.seed_dir / 'live')
        for key, wanted in self.expected.items():
            # Simulate an earlier image revision (0x112233) whose values must be preserved.
            header = dict(wanted['header'], configRev=0x112233, schema=1, created=100, clock=1)
            records = [dict(r, rev=0x112233) for r in wanted['records'].values()]
            medium.write(key, [header, *records])
        # Unconfirmed file on disk must never be read.
        (self.seed_dir / 'live' / ('f' * 64 + '.jsonl')).write_text('not in index', encoding='ascii')
        self.manifest_path = self.base / 'seed-manifest.json'
        record_seed(self.seed_dir, self.manifest_path, serial='601FC87B', root='Press')
        self.manifest_sha = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest().upper()

    def test_seed_documents_reads_pinned_manifest_and_compares_across_revisions(self):
        docs = host_docs.seed_documents('601FC87B', 'Press',
                                        manifest=self.manifest_path, digest=self.manifest_sha)
        self.assertEqual(set(docs), set(self.expected))
        preserved, previous_revs, current_rev = host_docs.compare_seed_documents(docs, self.expected)
        self.assertTrue(all(preserved.values()))
        self.assertEqual(previous_revs, {k: 0x112233 for k in self.expected})
        self.assertEqual(current_rev, 0xABCDEF)

    def test_seed_documents_and_comparison_reject_tamper_or_value_drift(self):
        with self.assertRaisesRegex(ValueError, 'manifest hash differs'):
            host_docs.seed_documents('601FC87B', 'Press',
                                     manifest=self.manifest_path, digest='00' * 32)
        docs = host_docs.seed_documents('601FC87B', 'Press',
                                        manifest=self.manifest_path, digest=self.manifest_sha)
        drifted = deepcopy(self.expected)
        drifted['Press.model2']['records']['recipe.value']['value'] = '999'
        preserved, _, _ = host_docs.compare_seed_documents(docs, drifted)
        self.assertFalse(preserved['Press.model2'])
        missing = dict(docs)
        missing.pop('Press.line')
        preserved_missing, prev_missing, _ = host_docs.compare_seed_documents(missing, self.expected)
        self.assertFalse(preserved_missing['Press.line'])
        self.assertIsNone(prev_missing['Press.line'])


class FakeLease:
    def __init__(self, name, store=None, originals_ok=True):
        self.name = name
        self.store = store
        self._closed = False
        self.failure = ''
        self._alive = True
        self._originals_ok = originals_ok

    def alive(self):
        return not self._closed and self._alive

    def originals_unchanged(self):
        return self._originals_ok

    def close(self):
        self._closed = True
        self._alive = False


class FakePLC:
    def __init__(self, controller, name):
        self.controller = controller
        self.name = name
        self.IPAddress = '127.0.0.1'
        self.ProcessorSlot = 0
        self.ConnectionSize = 4000
        self.SocketTimeout = 5
        self.closed = False
        self.conn = NS(close=self._close_conn)

    def _close_conn(self):
        self.closed = True
        self.controller.events.append(('close', self.name))

    def Close(self):
        return self.conn.close()

    def GetDeviceProperties(self):
        if self.closed:
            raise AssertionError(f'GetDeviceProperties on closed {self.name}')
        self.controller.events.append(('device_properties', self.name))
        return NS(Status='Success', Value=NS(
            SerialNumber='0x601FC87B',
            ProductName='Emulate 5580 Controller',
            Revision='38.11'))

    def Read(self, tag):
        if self.closed:
            raise AssertionError(f'Read on closed {self.name}')
        self.controller.events.append(('read', self.name, tag))
        return NS(Status='Success', Value=self.controller.tags[tag])

    def Write(self, tag, value):
        if self.closed:
            raise AssertionError(f'Write on closed {self.name}')
        self.controller.events.append(('write', self.name, tag, value))
        self.controller.tags[tag] = value
        self.controller.on_stimulus(tag, value)
        return NS(Status='Success', Value=value)


class SimulatedCollapsedController:
    """Deterministic in-memory model of the collapsed genealogy/tower station."""
    def __init__(self, base: Path, *, disconnect_elapsed: float = 3.25):
        self.base = base
        self.disconnect_elapsed = disconnect_elapsed
        self.now = 100.0
        self.events = []
        self.plc_instances = []
        self.host_leases = []
        self.gateway_leases = []
        self.binds = 0
        self.tags = {tag: 0 for tag in gen.externally_writable(APP)}
        self.mode = px.MODE_AUTO
        self.running = 0
        self.complete = 0
        self.error = 0
        self.error_id = 0
        self.aborted = 0
        self.cycle_count = 0
        self.good_count = 0
        self.scrap_count = 0
        self.rework_count = 0
        self.decision_id = 0
        self.current_level = 0
        self.required = [0] * 16
        self.test_active = False
        self.machine_state = 1
        self.part_present = 0
        self.part_uid = ''
        self.verdict = 0
        self.part_reason = 0
        self.parents = []
        self.host_seq = 0
        self.host_ring = []
        self.uid_counter = 0
        self.config_view = ConfigViewReader()
        self.expected_docs, self.config_rev = host_docs.expected_documents(self.config_view, APP.name)
        self.seed_dir = self.base / 'seed-source'
        medium = FileMedium(self.seed_dir / 'live')
        for key, wanted in self.expected_docs.items():
            header = dict(wanted['header'], configRev=0x223344, schema=1, created=50, clock=1)
            rows = [dict(r, rev=0x223344) for r in wanted['records'].values()]
            medium.write(key, [header, *rows])
        self.seed_manifest = self.base / 'seed-manifest.json'
        record_seed(self.seed_dir, self.seed_manifest, serial='601FC87B', root=APP.name)
        self.seed_sha = hashlib.sha256(self.seed_manifest.read_bytes()).hexdigest().upper()
        self.denied_key = 9101
        self.not_ready_key = 9102

    def new_plc(self):
        plc = FakePLC(self, f'plc-{len(self.plc_instances) + 1}')
        self.plc_instances.append(plc)
        self.events.append(('open', plc.name))
        return plc

    def sleep(self, seconds):
        self.events.append(('sleep', seconds))
        if seconds >= 3.0:
            # Verify all client connections (except the idle read-only observer) are closed!
            active_clients = [p.name for p in self.plc_instances
                              if not p.closed and p is not self._observer_plc]
            if active_clients:
                raise AssertionError(f'client connections still open during disconnect: {active_clients}')
            for lease in (*self.gateway_leases, *self.host_leases):
                if not lease._closed:
                    raise AssertionError(f'owned lease {lease.name} still running during disconnect')
            self.test_active = False
            self.now += self.disconnect_elapsed
        else:
            self.now += seconds

    @property
    def _observer_plc(self):
        return self.plc_instances[1] if len(self.plc_instances) >= 2 else None

    def bind_session(self, comm, app, expect_serial):
        if comm.comm.closed:
            raise AssertionError('bind_session on closed PLC')
        self.binds += 1
        self.events.append(('bind_s1', comm.comm.name, expect_serial))
        controller = self
        manifest_hash = views.manifest_hash(app)

        from fraktal_ab_host_service_binding import SERVICES

        class FakeRowReader:
            def __init__(self):
                self._manifest = dict(
                    controller.config_view._manifest,
                    hostServiceBindings=[dict(RootSymbol=app.name, Service=SERVICES['HostEvents'],
                                              CanonicalRoot=f'{app.name}/HostEvents')],
                )

            def manifest_identity(self):
                controller.events.append(('manifest_pin', comm.comm.name))
                return dict(Valid=True, Truncated=False, ContentHash=manifest_hash)

            def command_keys(self, root):
                return {access.DENIED: controller.denied_key, gen.UNIT_NOT_READY_KEY: controller.not_ready_key}

            def host_status(self, root):
                return dict(Restoring=False)

            def read_row(self, paths, private=()):
                if comm.comm.closed:
                    raise AssertionError(f'read_row on closed {comm.comm.name}')
                controller.events.append(('read_row', comm.comm.name, tuple(paths)))
                if set(paths).issubset(set(controller.config_view.values)):
                    return {'values': {p: controller.config_view.values[p] for p in paths}, 'private': {}}
                vals = {p: controller.canonical_value(p) for p in paths}
                priv = {}
                if private:
                    for sym, members in private.items():
                        priv[sym] = {m: controller.private_value(m) for m in members}
                return {'values': vals, 'private': priv}

        session = views.FixtureReads(app, FakeRowReader(), expected_serial=expect_serial)
        views.connection_state(comm)._fraktal_fixture_reads = session
        return session

    def restore_configuration(self, comm, app):
        state = views.connection_state(comm)
        store = self.base / f'isolated-store-{len(self.host_leases) + 1}'
        medium = FileMedium(store / 'live')
        for key, wanted in self.expected_docs.items():
            medium.write(key, [dict(wanted['header'], schema=1, created=99, clock=1),
                               *wanted['records'].values()])
        lease = FakeLease(f'host-{len(self.host_leases) + 1}', store=store)
        self.host_leases.append(lease)
        attach(comm, 'host', lease)
        state._fraktal_host_lease = lease
        self.events.append(('host_bound', comm.comm.name, str(store)))
        return dict(wasRestoring=False, restoring=False, medium=str(store / 'live'),
                    confirmedKeys=sorted(self.expected_docs), health={'state': 'serving'})

    def emit_event(self, kind, *, subject='', value='', verdict=0, reason=0, parents=()):
        self.host_seq += 1
        part_uid = self.part_uid if 1 <= kind <= 4 else ''
        self.host_ring.append(dict(
            Sequence=self.host_seq, Kind=kind, StationPath=APP.name,
            PartUid=part_uid, Subject=subject, Value=value,
            Stamp='2026-11-07T12:00:00Z', TimeSynchronized=True,
            Verdict=verdict, ReasonCode=reason,
            ParentCount=len(parents),
            Parents=list(parents) + [''] * (2 - len(parents)),
        ))
        if len(self.host_ring) > APP.host_event_capacity:
            self.host_ring.pop(0)

    def on_stimulus(self, tag, value):
        if tag == px.TWO_HAND and value == 1 and self.running and self.mode == px.MODE_AUTO:
            # Start AUTO cycle according to injected stimuli!
            self.uid_counter += 1
            self.part_uid = f'PART-{self.uid_counter:04d}'
            self.part_present = 1
            self.parents = []
            self.emit_event(1)  # received
            self.emit_event(8, subject='Fixture.BlankLot', value='20261018')
            if self.tags[px.FAULT['PartSlide']]:
                first_out = next(iter(APP.reasons.values()))
                self.running = 0
                self.error = 1
                self.error_id = first_out
                self.machine_state = 4
                self.part_present = 0
                self.emit_event(4, reason=first_out)
                return
            if self.tags[px.HOLD['PressRam']]:
                self.machine_state = 2  # PRODUCING
                return
            if self.tags[px.FAULT['PressRam']]:
                self.emit_event(2)
                self.emit_event(7, subject='Fixture.UpperDie', value='314')
                self.decision_id = 1
                self.machine_state = 2
                return
            self._finish_good_cycle()
        elif tag == px.HOLD['PressRam'] and value == 0 and self.running and self.part_present:
            self._finish_good_cycle()
        elif tag == px.FAULT['PressRam'] and value == 0 and self.running and self.decision_id == 0 and self.part_present:
            # Handled NOK completes after decision answer + fault clear
            reason = next(iter(APP.reasons.values()))
            self.verdict = 2
            self.part_reason = reason
            self.part_present = 0
            self.parents = []
            self.scrap_count += 1
            self.cycle_count += 1
            self.running = 0
            self.complete = 1
            self.machine_state = 1
            self.emit_event(3, verdict=2, reason=reason)
            self.emit_event(10, verdict=2, reason=reason)

    def _finish_good_cycle(self):
        import fraktal_ab_text_resource_demo as text_demo
        self.emit_event(2)
        self.emit_event(7, subject='Fixture.UpperDie', value='314')
        self.emit_event(8, subject=text_demo.SUBJECT, value=text_demo.VALUE)
        self.parents = list(legacy_genealogy.PARENTS)
        self.verdict = 1
        self.part_reason = 0
        self.part_present = 0
        self.good_count += 1
        self.cycle_count += 1
        self.running = 0
        self.complete = 1
        self.machine_state = 1
        self.emit_event(3, verdict=1, parents=self.parents)

    def handle_command(self, comm, kind, *, app, settle, **arguments):
        if comm.comm.closed:
            raise AssertionError('command on closed connection')
        if not getattr(comm, '_writable', True):
            raise AssertionError('read-only observer must never issue commands')
        comm.guard()
        children = getattr(views.connection_state(comm), '_fraktal_child_leases', None) or {}
        if 'gateway' not in children:
            gw_lease = FakeLease(f'gw-{len(self.gateway_leases) + 1}')
            self.gateway_leases.append(gw_lease)
            attach(comm, 'gateway', gw_lease)
        self.events.append(('command', comm.comm.name, kind))
        if kind == mb.LOGIN:
            self.current_level = 4
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.LOGOUT:
            self.current_level = 0
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.SET_ACCESS_LEVEL:
            gate = int(arguments['IntValue'])
            self.required[gate] = int(arguments['TextValue'])
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.LAMP_TEST:
            if self.current_level < self.required[2]:
                return dict(sequence=1, accepted=False, diagnosticKey=self.denied_key)
            if self.running or self.test_active:
                return dict(sequence=1, accepted=False, diagnosticKey=self.not_ready_key)
            self.test_active = True
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.STOP:
            if self.part_present:
                self.part_present = 0
                self.parents = []
                self.emit_event(4)
            self.running = 0
            self.aborted = 1 if self.running else 0
            self.machine_state = 1
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.OPERATOR_RESET:
            self.error = 0
            self.error_id = 0
            self.aborted = 0
            self.complete = 0
            self.machine_state = 1
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.SET_MODE:
            new_mode = int(arguments['IntValue'])
            if self.part_present and new_mode != self.mode:
                self.part_present = 0
                self.parents = []
                self.emit_event(4)
            self.mode = new_mode
            self.running = 0
            self.complete = 0
            self.error = 0
            self.aborted = 0
            self.machine_state = 1
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.START:
            if self.mode == px.MODE_HOME:
                self.running = 0
                self.complete = 1
            else:
                self.running = 1
                self.complete = 0
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.DECISION_ANSWER:
            self.decision_id = 0
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        return dict(sequence=1, accepted=True, diagnosticKey=0)

    def canonical_value(self, path):
        prefix = APP.name + '/'
        rel = path[len(prefix):]
        if rel == 'ModeActivePublished':
            return self.mode
        if rel == 'CurrentStep/StepNo':
            return 100
        if rel == 'Status/ConfigRev':
            return self.config_rev
        if rel == 'GoodCount':
            return self.good_count
        if rel == 'NokCount':
            return self.scrap_count
        if rel == 'ReworkCount':
            return self.rework_count
        if rel == 'MachineState':
            return self.machine_state
        if rel.startswith('SignalTower/'):
            name = rel.split('/', 1)[1]
            if name == 'TestActive':
                return self.test_active
            if self.test_active:
                return True
            if name == 'Red':
                return self.machine_state == 4
            if name == 'Green':
                return self.machine_state == 2
            if name == 'Blue':
                return self.decision_id != 0
            if name == 'Horn':
                if self.machine_state == 4 and self.error_id:
                    sym = next(k for k, v in APP.reasons.items() if v == self.error_id)
                    import fraktal_ab_reasons as reasons
                    return reasons.of(APP, sym).priority == 2 and APP.signal_tower.horn_on_high
                return False
            return False
        if rel == 'Part/Present':
            return bool(self.part_present)
        if rel == 'Part/Uid':
            return self.part_uid
        if rel == 'Part/CarrierKind':
            return 1
        if rel == 'Part/ParentCapacity':
            return 2
        if rel == 'Part/ParentCount':
            return len(self.parents)
        if rel == 'Part/Parents[1]':
            return self.parents[0] if len(self.parents) >= 1 else ''
        if rel == 'Part/Parents[2]':
            return self.parents[1] if len(self.parents) >= 2 else ''
        if rel == 'Part/Result/Verdict':
            return self.verdict
        if rel == 'Part/Result/ReasonCode':
            return self.part_reason
        if rel == 'Part/Result/StationPath':
            return APP.name
        if rel == 'Part/Result/TimeSynchronized':
            return True
        if rel == 'Part/Result/Stamp':
            return '2026-11-07T12:00:00Z'
        if rel.startswith('Part/Result/Records['):
            if rel.endswith('/Value'):
                return 100
            if rel.endswith('/InTol'):
                return True
            if rel.endswith('/Name') or rel.endswith('/Unit'):
                return 'x'
            return 0
        if rel.startswith('HostEvents/'):
            sub = rel[len('HostEvents/'):]
            cap = APP.host_event_capacity
            count = len(self.host_ring)
            head = (self.host_seq - 1) % cap + 1 if count else 0
            meta = dict(
                SchemaVersion=5, Head=head, Count=count, Capacity=cap,
                Wrapped=self.host_seq > cap, NewestSequence=self.host_seq,
                DataRevision=max(2, self.host_seq * 2), EpochLow=1, EpochHigh=1,
                Failed=0, RingHead=head, GenealogyCapacity=2,
            )
            if sub in meta:
                return meta[sub]
            slot = int(sub.split('Ring[', 1)[1].split(']', 1)[0])
            field = sub.split(']/', 1)[1]
            # Map ring slot to event in self.host_ring
            offset = (slot - 1 - (head - count)) % cap
            event = self.host_ring[offset]
            if field.startswith('Parents['):
                idx = int(field.split('[', 1)[1].split(']', 1)[0]) - 1
                return event['Parents'][idx]
            return event[field]
        if rel.startswith('ConfigPersist/'):
            return False
        return 0

    def private_value(self, member):
        mapping = {
            'Mailbox_DiagnosticKey': 0,
            'Unit_Aborted': self.aborted,
            'Unit_Complete': self.complete,
            'Unit_CycleCount': self.cycle_count,
            'Unit_DecisionId': self.decision_id,
            'Unit_Error': self.error,
            'Unit_ErrorID': self.error_id,
            'Unit_Running': self.running,
            'TwoHand_OutImm_Armed': int(self.tags[px.TWO_HAND] == 0),
            'PressRam_OutImm_Held': int(self.tags[px.HOLD['PressRam']] != 0 and self.running != 0),
            'AccessState_CurrentLevel': self.current_level,
            'AccessState_LoginBusy': 0,
            'AccessState_Required': list(self.required),
        }
        return mapping[member]


class RunnerLifecycleAndGenealogy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.creds = self.base / 'creds.json'
        user_name = APP.access_users[0].name
        self.creds.write_text(json.dumps({'users': [{'user': user_name, 'pin': '1234', 'level': 4}]}), encoding='utf-8')
        self.account = {'user': user_name, 'pin': '1234', 'level': 4}

    def test_collapsed_guarded_forbids_direct_mailbox_writes_and_observer_forbids_all_writes(self):
        sim = SimulatedCollapsedController(self.base)
        with patch.object(views, 'bind', side_effect=sim.bind_session):
            comm = part_execute.Guarded(sim.new_plc(), 0x601FC87B, APP, plc_factory=sim.new_plc)
            comm.guard()
            for forbidden in (mb.request_tag_name(APP) + '.Kind',
                              mb.request_tag_name(APP) + '.ConfigSet.SetName'):
                with self.assertRaises(part_execute.FixtureRefused):
                    comm.Write(forbidden, 1)
            obs = comm.open_observer()
            try:
                self.assertEqual(obs.allowed, frozenset())
                with self.assertRaises(part_execute.FixtureRefused):
                    obs.Write(px.AIR_OK, 1)
            finally:
                obs.Close()
            comm.Close()

    def test_full_collapsed_genealogy_and_tower_lifecycle_preserves_disconnect_and_restores(self):
        sim = SimulatedCollapsedController(self.base, disconnect_elapsed=3.25)
        output = self.base / 'evidence.json'
        args = NS(execute_fixture=True, expect_serial='601FC87B',
                  credential_file=self.creds, output=output, core_regressions=True)
        env = {'FRAKTAL_HARNESS_HOST_SEED': str(sim.seed_manifest),
               'FRAKTAL_HARNESS_HOST_SEED_SHA256': sim.seed_sha}
        with patch.dict('os.environ', env), \
                patch.object(views, 'bind', side_effect=sim.bind_session), \
                patch.object(views, 'command', side_effect=sim.handle_command), \
                patch.object(host_docs, 'restore_configuration', side_effect=sim.restore_configuration), \
                patch.object(host_docs, 'ready', return_value={'restoring': False}), \
                patch.object(tower_execute.time, 'monotonic', side_effect=lambda: sim.now), \
                patch.object(tower_execute.time, 'sleep', side_effect=sim.sleep), \
                patch.object(part_execute.time, 'monotonic', side_effect=lambda: sim.now), \
                patch.object(part_execute.time, 'sleep', side_effect=sim.sleep):
            rc = tower_execute.execute_fixture(
                args, APP, self.account,
                run_type=genealogy_execute.GenealogyRun,
                schema='fraktal.ab.genealogy-live-fixture',
                plc_factory=sim.new_plc,
            )
        self.assertEqual(rc, 0)
        evidence = json.loads(output.read_text(encoding='utf-8'))
        self.assertTrue(evidence['restored'])
        self.assertTrue(evidence['policyRestored'])
        self.assertEqual(evidence['manifestHash'], views.manifest_hash(APP))
        self.assertTrue(evidence['final']['originalMediumUnchanged'])
        self.assertTrue(evidence['final']['liveDocumentsVerified'])
        cases = [r.get('case') for r in evidence['rows']]
        for required_case in ('configuration_preserved', 'logged_out_manual_refusal',
                              'manual_independent_of_power', 'all_outputs_active',
                              'active_test_refusal', 'logout_disconnect_timeout',
                              'producing', 'busy_test_refusal', 'rationalized_fault', 'operator_decision'):
            self.assertIn(required_case, cases)
        disconnect_row = next(r for r in evidence['rows'] if r.get('case') == 'logout_disconnect_timeout')
        self.assertEqual(disconnect_row['disconnectedSeconds'], 3.2)
        self.assertLess(disconnect_row['observedSeconds'], 4.0)
        # Verify 3 distinct PLC connections: phase 1, read-only observer, phase 2; all closed at exit!
        self.assertEqual(len(sim.plc_instances), 3)
        self.assertTrue(all(p.closed for p in sim.plc_instances))
        self.assertEqual(len(sim.host_leases), 2)
        self.assertTrue(all(l._closed for l in sim.host_leases))
        # Verify zero controller reads/writes occurred during the 3.2 s sleep
        sleep_idx = sim.events.index(('sleep', 3.2))
        self.assertEqual(sim.events[sleep_idx - 1], ('close', 'plc-1'))
        self.assertEqual(sim.events[sleep_idx + 1][0:2], ('read_row', 'plc-2'))
        # Verify all 3 languages ran in core_regressions with genealogyChecksPassed
        genealogy_rows = [r for r in evidence['rows'] if r.get('genealogyChecksPassed')]
        self.assertEqual({r['language'] for r in genealogy_rows}, set(decl.RENDITIONS))
        self.assertTrue(all(r['passed'] for r in genealogy_rows))
        # Also verify Run.verify_sink uses collapsed manifest_hash and Cursor cleanly
        sink_probe = self.base / 'sink-probe.json'
        with patch.object(views, 'bind', side_effect=sim.bind_session):
            sink_comm = part_execute.Guarded(sim.new_plc(), 0x601FC87B, APP, plc_factory=sim.new_plc)
            try:
                sink_comm.guard()
                sink_ev = dict(serial='601FC87B', rows=[])
                sink_run = part_execute.Run(sink_comm, APP, self.account, sink_ev)
                sink_run.verify_sink(sink_probe)
                self.assertTrue(sink_ev['sink']['rejectedWithoutAdvance'])
                self.assertEqual(sink_ev['sink']['replayedAfterReopen'], 0)
                self.assertEqual(sink_ev['sink']['cursor']['source'], '601FC87B:' + views.manifest_hash(APP))
            finally:
                sink_comm.Close()

    def test_disconnect_expiry_over_4s_fails_and_finally_still_opens_phase2_to_restore(self):
        sim = SimulatedCollapsedController(self.base, disconnect_elapsed=4.05)
        output = self.base / 'expired-late.json'
        args = NS(execute_fixture=True, expect_serial='601FC87B',
                  credential_file=self.creds, output=output, core_regressions=False)
        env = {'FRAKTAL_HARNESS_HOST_SEED': str(sim.seed_manifest),
               'FRAKTAL_HARNESS_HOST_SEED_SHA256': sim.seed_sha}
        with patch.dict('os.environ', env), \
                patch.object(views, 'bind', side_effect=sim.bind_session), \
                patch.object(views, 'command', side_effect=sim.handle_command), \
                patch.object(host_docs, 'restore_configuration', side_effect=sim.restore_configuration), \
                patch.object(host_docs, 'ready', return_value={'restoring': False}), \
                patch.object(tower_execute.time, 'monotonic', side_effect=lambda: sim.now), \
                patch.object(tower_execute.time, 'sleep', side_effect=sim.sleep), \
                patch.object(part_execute.time, 'monotonic', side_effect=lambda: sim.now), \
                patch.object(part_execute.time, 'sleep', side_effect=sim.sleep):
            with self.assertRaisesRegex(part_execute.FixtureRefused, 'did not expire'):
                tower_execute.execute_fixture(args, APP, self.account, plc_factory=sim.new_plc)
        evidence = json.loads(output.read_text(encoding='utf-8'))
        self.assertTrue(evidence['restored'])
        self.assertIn('did not expire', evidence['error'])
        self.assertTrue(all(p.closed for p in sim.plc_instances))

    def test_latched_lease_failure_never_restarts_or_clears_failure(self):
        sim = SimulatedCollapsedController(self.base)
        output = self.base / 'lease-failed.json'
        args = NS(execute_fixture=True, expect_serial='601FC87B',
                  credential_file=self.creds, output=output, core_regressions=False)
        env = {'FRAKTAL_HARNESS_HOST_SEED': str(sim.seed_manifest),
               'FRAKTAL_HARNESS_HOST_SEED_SHA256': sim.seed_sha}

        def fail_mid_run(run):
            run.login()
            run.restore_configuration()
            sim.host_leases[0].failure = 'adapter reported a failed service'
            run.comm.close_phase()

        with patch.dict('os.environ', env), \
                patch.object(views, 'bind', side_effect=sim.bind_session), \
                patch.object(views, 'command', side_effect=sim.handle_command), \
                patch.object(host_docs, 'restore_configuration', side_effect=sim.restore_configuration), \
                patch.object(host_docs, 'ready', return_value={'restoring': False}):
            with self.assertRaisesRegex(part_execute.FixtureRefused, 'latched failure'):
                tower_execute.execute_fixture(args, APP, self.account,
                                              exercise_rows=fail_mid_run, plc_factory=sim.new_plc)
        # Never opened phase 2 or restarted the failed HostLease; failure stays latched; child closed on exit!
        self.assertEqual(len(sim.plc_instances), 1)
        self.assertEqual(len(sim.host_leases), 1)
        self.assertEqual(sim.host_leases[0].failure, 'adapter reported a failed service')
        self.assertTrue(sim.host_leases[0]._closed)
        evidence = json.loads(output.read_text(encoding='utf-8'))
        self.assertFalse(evidence['restored'])

    def test_genealogy_cli_accepts_legacy_and_collapsed_declarations_only(self):
        out = self.base / 'cli-out.json'
        for decl_name in ('fraktal_ab_genealogy_demo', 'fraktal_ab_genealogy_s6_collapse_demo'):
            with patch.object(genealogy_execute.station, 'module_name', return_value=decl_name), \
                    patch.object(genealogy_execute.station, 'application', return_value=APP), \
                    patch.object(tower_execute, 'execute_fixture', return_value=0) as exec_mock:
                rc = genealogy_execute.main(['--execute-fixture', '--expect-serial', '601FC87B',
                                             '--credential-file', str(self.creds), '--output', str(out)])
                self.assertEqual(rc, 0)
                exec_mock.assert_called_once()
        with patch.object(genealogy_execute.station, 'module_name', return_value='fraktal_ab_press_demo'), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            genealogy_execute.main(['--execute-fixture', '--expect-serial', '601FC87B',
                                    '--credential-file', str(self.creds), '--output', str(out)])


if __name__ == '__main__':
    unittest.main()
