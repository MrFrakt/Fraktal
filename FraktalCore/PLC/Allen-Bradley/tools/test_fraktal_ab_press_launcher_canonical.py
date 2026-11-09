"""Standalone canonical press launcher (fraktal_ab_press_canonical_execute.py) C5b3 offline qualification."""
from __future__ import annotations

import contextlib
from functools import partial
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import fraktal_ab_access as access
import fraktal_ab_config_read_view as read_view
import fraktal_ab_declaration as decl
import fraktal_ab_document_revision as doc_rev
import fraktal_ab_fixture_reads as views
import fraktal_ab_generate as gen
import fraktal_ab_harness_documents as host_docs
from fraktal_ab_harness_process import attach
import fraktal_ab_live as legacy_live
from fraktal_ab_live_medium import FileMedium, content as doc_content
import fraktal_ab_mailbox as mb
import fraktal_ab_part_execute as part_execute
import fraktal_ab_press_canonical_echo38 as legacy_press
import fraktal_ab_press_canonical_execute as walk
import fraktal_ab_press_execute as px
import fraktal_ab_press_s6_collapse_echo38 as collapse_press
import fraktal_ab_press_s6_shelving_echo38 as shelving_press
import fraktal_ab_sets as sets
import fraktal_ab_tower_execute as tower_execute
from test_fraktal_ab_runner_canonical import FakeLease, FakePLC


class RealPressConfigView:
    """Exact V6.8 ConfigView + model catalog emitted by a downloaded press image."""

    def __init__(self, app: decl.Application, *, revision: int = 17):
        self.app = app
        self.revision = revision
        self.prefix = read_view.canonical_root(app)
        self._manifest = dict(
            legacyContentHash=doc_rev.identity(app),
            readServices=read_view.descriptors(app),
        )
        codes = [m.code for m in app.models]
        active_code = app.default_model or (codes[0] if codes else '')
        active_ordinal = codes.index(active_code) + 1 if active_code in codes else 0
        active_model = app.models[active_ordinal - 1] if active_ordinal else None

        records = {}
        for rec in app.records:
            records[rec.name] = {}
            for mem in rec.members:
                if rec.par_cfg and active_model is not None and mem.name in active_model.values:
                    records[rec.name][mem.name] = active_model.values[mem.name]
                else:
                    records[rec.name][mem.name] = mem.initial
        banks = [
            {
                mem.name: model.values.get(mem.name, mem.initial)
                for rec in app.records
                for mem in rec.members
            }
            for model in app.models
        ]
        self.legacy_capture = legacy_live.Capture(
            restoring=True,
            records=records,
            banks=banks,
            codes=codes,
            model_ordinal=active_ordinal,
        )

        editable = gen.editable_values(app)
        defs = []
        val_rows = []
        for idx, (_ordinal, rec, mem) in enumerate(editable):
            scoped = gen.is_model_scoped(app, rec, mem.name)
            defs.append(dict(
                DefinitionIndex=idx,
                WriteKey=mem.write_key,
                ConfigKind=sets.config_kind(rec),
                ValueType=sets.value_type(mem),
                ModelScoped=scoped,
            ))
            val_rows.append((idx, 0, '', str(int(records[rec.name][mem.name]))))

        if any(d['ModelScoped'] for d in defs):
            for bank_idx, model in enumerate(app.models, 1):
                bank = banks[bank_idx - 1]
                for idx, (_ordinal, _rec, mem) in enumerate(editable):
                    if defs[idx]['ModelScoped']:
                        val_rows.append((idx, bank_idx, model.code, str(int(bank[mem.name]))))

        self.values = {
            f'{self.prefix}/SchemaVersion': 1,
            f'{self.prefix}/RootIdentity': app.name,
            f'{self.prefix}/Revision': revision,
            f'{self.prefix}/DefinitionCount': len(defs),
            f'{self.prefix}/ValueCount': len(val_rows),
            f'{app.name}/AvailableModelCount': len(codes),
            f'{app.name}/Model/ModelCode': active_code,
            f'{app.name}/Status/ConfigRev': revision,
            f'{app.name}/ConfigPersist/RestoreLost': False,
            f'{app.name}/ConfigPersist/Failed': False,
            f'{app.name}/ConfigPersist/Pending': False,
        }
        for i, code in enumerate(codes, 1):
            self.values[f'{app.name}/AvailableModels[{i}]/ModelCode'] = code
        for d in defs:
            i = d['DefinitionIndex']
            for k, v in d.items():
                self.values[f'{self.prefix}/Definitions[{i}]/{k}'] = v
        for pos, (def_idx, bank, code, text) in enumerate(val_rows):
            for k, v in dict(
                DefinitionIndex=def_idx,
                ModelOrdinal=bank,
                ModelCode=code,
                ValueText=text,
                Readable=True,
                Revision=revision,
            ).items():
                self.values[f'{self.prefix}/Values[{pos}]/{k}'] = v

    def read_row(self, paths):
        return {'values': {p: self.values[p] for p in paths}, 'private': {}}


class SimulatedCollapsedPressController:
    """Deterministic in-memory model of the collapsed press station (no Part, no Tower)."""

    def __init__(self, app: decl.Application, base: Path):
        self.app = app
        self.base = base
        self.now = 200.0
        self.events = []
        self.plc_instances = []
        self.host_leases = []
        self.gateway_leases = []
        self.tags = {tag: 0 for tag in gen.externally_writable(app)}
        self.mode = px.MODE_AUTO
        self.step = 0
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
        self.in_cycle = False
        self.current_level = 0
        self.required = [0] * 16
        self.config_view = RealPressConfigView(app, revision=23)
        self.expected_docs, self.config_rev = host_docs.expected_documents(self.config_view, app.name)
        self.denied_key = 9201
        self.not_ready_key = 9202
        self._declared_private = {
            f'{group}_{field}'
            for group, fields in app.fixture_observation
            for field in fields
        }

    def new_plc(self):
        plc = FakePLC(self, f'plc-{len(self.plc_instances) + 1}')
        self.plc_instances.append(plc)
        self.events.append(('open', plc.name))
        return plc

    def sleep(self, seconds):
        self.events.append(('sleep', seconds))
        self.now += seconds

    def bind_session(self, comm, app, expect_serial):
        if comm.comm.closed:
            raise AssertionError('bind_session on closed PLC')
        controller = self
        manifest_hash = views.manifest_hash(app)

        class FakeRowReader:
            def __init__(self):
                self._manifest = dict(controller.config_view._manifest)

            def manifest_identity(self):
                return dict(Valid=True, Truncated=False, ContentHash=manifest_hash)

            def command_keys(self, root):
                return {access.DENIED: controller.denied_key, gen.UNIT_NOT_READY_KEY: controller.not_ready_key}

            def host_status(self, root):
                return dict(Restoring=False)

            def read_row(self, paths, private=()):
                if comm.comm.closed:
                    raise AssertionError(f'read_row on closed {comm.comm.name}')
                controller.events.append(('read_row', comm.comm.name, tuple(paths)))
                vals = {}
                for p in paths:
                    if p in controller.config_view.values:
                        vals[p] = controller.config_view.values[p]
                    else:
                        vals[p] = controller.canonical_value(p)
                priv = {}
                if private:
                    for sym, members in private.items():
                        priv[sym] = {m: controller.private_value(m) for m in members}
                return {'values': vals, 'private': priv}

        session = views.FixtureReads(app, FakeRowReader(), expected_serial=expect_serial)
        views.connection_state(comm)._fraktal_fixture_reads = session
        return session

    def restore_configuration(self, comm, app):
        # Must read the isolated seed manifest commissioned by walk.seed_medium!
        seed_docs = host_docs.seed_documents('601FC87B', app.name)
        if set(seed_docs) != set(self.expected_docs):
            raise AssertionError('isolated seed manifest missing press documents')
        state = views.connection_state(comm)
        store = self.base / f'isolated-host-work-{len(self.host_leases) + 1}'
        medium = FileMedium(store / 'live')
        for key, doc in seed_docs.items():
            medium.write(key, doc)
        lease = FakeLease(f'host-{len(self.host_leases) + 1}', store=store)
        self.host_leases.append(lease)
        attach(comm, 'host', lease)
        state._fraktal_host_lease = lease
        return dict(wasRestoring=True, restoring=False, medium=str(store / 'live'),
                    confirmedKeys=sorted(seed_docs), health={'state': 'serving'})

    def on_stimulus(self, tag, value):
        if tag == px.TWO_HAND and value == 1 and self.running and self.mode == px.MODE_AUTO:
            self.in_cycle = True
            self.step = 100
            if self.tags[px.FAULT['PartSlide']]:
                first_out = next(iter(self.app.reasons.values()))
                self.running = 0
                self.in_cycle = False
                self.step = 0
                self.error = 1
                self.error_id = first_out
                return
            if self.tags[px.HOLD['PressRam']]:
                self.step = 200
                return
            if self.tags[px.FAULT['PressRam']]:
                self.step = 200
                self.decision_id = 1
                return
            self._finish_good_cycle()
        elif tag == px.HOLD['PressRam'] and value == 0 and self.running and self.in_cycle:
            self._finish_good_cycle()
        elif (tag == px.FAULT['PressRam'] and value == 0
              and self.running and self.in_cycle and self.decision_id == 0):
            self.in_cycle = False
            self.step = 0
            self.scrap_count += 1
            self.cycle_count += 1
            self.running = 0
            self.complete = 1

    def _finish_good_cycle(self):
        self.in_cycle = False
        self.step = 0
        self.good_count += 1
        self.cycle_count += 1
        self.running = 0
        self.complete = 1

    def handle_command(self, comm, kind, *, app, settle, **arguments):
        if comm.comm.closed:
            raise AssertionError('command on closed connection')
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
            return dict(sequence=1, accepted=False, diagnosticKey=self.not_ready_key)
        if kind == mb.STOP:
            was_running = self.running
            self.running = 0
            self.in_cycle = False
            self.step = 0
            self.aborted = 1 if was_running else 0
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.OPERATOR_RESET:
            self.error = 0
            self.error_id = 0
            self.aborted = 0
            self.complete = 0
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.SET_MODE:
            new_mode = int(arguments['IntValue'])
            self.mode = new_mode
            if new_mode == self.app.manual_mode:
                # Like the generated Unit: chain stands down to Step 0 while run level keeps Running unless stopped.
                self.step = 0
                self.in_cycle = False
            else:
                self.running = 0
                self.step = 0
                self.in_cycle = False
            self.complete = 0
            self.error = 0
            self.aborted = 0
            return dict(sequence=1, accepted=True, diagnosticKey=0)
        if kind == mb.START:
            if self.mode == px.MODE_HOME:
                self.running = 0
                self.step = 0
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
        prefix = self.app.name + '/'
        rel = path[len(prefix):] if path.startswith(prefix) else path
        if rel == 'ModeActivePublished':
            return self.mode
        if rel == 'CurrentStep/StepNo':
            return self.step
        if rel == 'Status/ConfigRev':
            return self.config_rev
        if rel == 'GoodCount':
            return self.good_count
        if rel == 'NokCount':
            return self.scrap_count
        if rel == 'ReworkCount':
            return self.rework_count
        if rel.startswith('PressRam/'):
            if rel.endswith('Status/State'):
                return 1 if self.running else 0
            return 0
        if rel.startswith('TwoHand/'):
            return 0
        return 0

    def private_value(self, member):
        if member not in self._declared_private:
            raise KeyError(member)
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
            'PressRam_OutImm_Held': int(self.tags[px.HOLD['PressRam']] != 0 and self.in_cycle),
            'PressRam_DoneCount': self.cycle_count,
            'PressRam_RunCount': self.cycle_count,
            'AccessState_CurrentLevel': self.current_level,
            'AccessState_LoginBusy': 0,
            'AccessState_Required': list(self.required),
            'AccessState_UserBytes': [0] * 32,
        }
        return mapping.get(member, 0)


class StandaloneAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.pin = 'AB' * 32
        self.valid = dict(
            CurrentOwnerApproved=True,
            MailboxOrTagWritesAuthorized=True,
            Serial='601FC87B',
            CanonicalSha256=self.pin,
            FaultClearAuthorized=False,
            ClockSetAuthorized=False,
        )

    def _write(self, payload):
        path = self.base / 'auth.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        return path

    def test_valid_exact_image_authorization_passes_without_s3k_module(self):
        path = self._write(self.valid)
        with patch.object(walk.typed, 'authorize', side_effect=AssertionError('must not call MO s3k authorize')):
            parsed = walk.authorize(path, self.pin)
        self.assertEqual(parsed['CanonicalSha256'], self.pin)

    def test_invalid_pin_or_approval_fields_are_refused(self):
        path = self._write(self.valid)
        for bad_pin in ('ab' * 32, 'A' * 63, 'G' * 64):
            with self.subTest(pin=bad_pin), self.assertRaisesRegex(part_execute.FixtureRefused, 'press authorization'):
                walk.authorize(path, bad_pin)
        mutations = (
            ('CurrentOwnerApproved', 1),
            ('CurrentOwnerApproved', False),
            ('MailboxOrTagWritesAuthorized', 1),
            ('MailboxOrTagWritesAuthorized', False),
            ('Serial', 'DEADBEEF'),
            ('CanonicalSha256', 'CD' * 32),
            ('FaultClearAuthorized', 0),
            ('FaultClearAuthorized', True),
            ('ClockSetAuthorized', 0),
            ('ClockSetAuthorized', True),
        )
        for key, bad_val in mutations:
            broken = dict(self.valid, **{key: bad_val})
            p = self._write(broken)
            with self.subTest(field=key, value=bad_val), \
                    self.assertRaisesRegex(part_execute.FixtureRefused, 'press authorization'):
                walk.authorize(p, self.pin)


class PressSeedEquivalenceAndGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def test_collapsed_seed_medium_matches_legacy_live_documents_byte_for_byte_on_both_profiles(self):
        legacy_app = legacy_press.application()
        for label, factory in (('collapse', collapse_press.application),
                               ('shelving', shelving_press.application)):
            with self.subTest(profile=label):
                app = factory()
                view = RealPressConfigView(app, revision=31)
                legacy_docs = legacy_live.documents(legacy_app, view.legacy_capture, 0)
                self.assertEqual(
                    set(legacy_docs),
                    {'Press.station', 'Press.line', 'Press.model1', 'Press.model2', 'Press.model3'},
                )
                seed_dir = self.base / f'{label}_press_medium'
                seed_dir.mkdir()
                (seed_dir / 'live').mkdir()
                session = NS(reader=view, root=app.name)
                run = NS(
                    app=app,
                    comm=object(),
                    evidence=dict(serial='601FC87B'),
                    check=part_execute.Run.check.__get__(object(), part_execute.Run),
                )
                env = {walk.ISOLATED_SEED_ENV: str(seed_dir)}
                for k in ('FRAKTAL_HARNESS_HOST_SEED', 'FRAKTAL_HARNESS_HOST_SEED_SHA256'):
                    os.environ.pop(k, None)
                with patch.dict(os.environ, env, clear=False), \
                        patch.object(views, '_session', return_value=session), \
                        patch.object(views, 'revision', return_value=31):
                    walk.seed_medium(run)
                    manifest_docs = host_docs.seed_documents('601FC87B', app.name)
                    # Second call on the same directory must refuse!
                    with self.assertRaisesRegex(part_execute.FixtureRefused, 'must start empty'):
                        walk.seed_medium(run)
                store = FileMedium(seed_dir / 'live')
                self.assertEqual(set(store.index()), set(legacy_docs))
                for key, wanted_doc in legacy_docs.items():
                    self.assertEqual(doc_content(store.read(key)), doc_content(wanted_doc))
                    self.assertEqual(doc_content(manifest_docs[key]), doc_content(wanted_doc))
                meta = run.evidence['pressMedium']
                self.assertEqual(meta['seeded'], sorted(legacy_docs))
                self.assertEqual(meta['files'], 6)
                self.assertEqual(meta['source'], 'published configuration view of the downloaded press image')
                manifest_path = Path(meta['seedManifest'])
                self.assertEqual(
                    hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper(),
                    meta['seedManifestSha256'],
                )

    def test_seed_medium_and_isolate_medium_refusal_guards(self):
        app = collapse_press.application()
        view = RealPressConfigView(app, revision=19)
        session = NS(reader=view, root=app.name)
        run = NS(
            app=app,
            comm=object(),
            evidence=dict(serial='601FC87B'),
            check=part_execute.Run.check.__get__(object(), part_execute.Run),
        )
        # 1. Missing ISOLATED_SEED_ENV
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(walk.ISOLATED_SEED_ENV, None)
            with self.assertRaisesRegex(part_execute.FixtureRefused, 'not selected'):
                walk.seed_medium(run)

        # 2. Pre-existing FRAKTAL_HARNESS_HOST_SEED in seed_medium and isolate_medium
        out = self.base / 'out.json'
        with patch.dict(os.environ, {walk.ISOLATED_SEED_ENV: str(self.base / 'm1'),
                                     'FRAKTAL_HARNESS_HOST_SEED': 'already.json'}, clear=False):
            with self.assertRaisesRegex(part_execute.FixtureRefused, 'must start empty'):
                walk.seed_medium(run)
            with self.assertRaisesRegex(part_execute.FixtureRefused, 'host seed environment already set'):
                walk.isolate_medium(out, canonical_collapse=True)

        # 3. Epoch change during seeding
        m2 = self.base / 'm2'
        m2.mkdir()
        (m2 / 'live').mkdir()
        with patch.dict(os.environ, {walk.ISOLATED_SEED_ENV: str(m2)}, clear=False), \
                patch.object(views, '_session', return_value=session), \
                patch.object(views, 'revision', return_value=20):
            os.environ.pop('FRAKTAL_HARNESS_HOST_SEED', None)
            os.environ.pop('FRAKTAL_HARNESS_HOST_SEED_SHA256', None)
            with self.assertRaisesRegex(part_execute.FixtureRefused, 'configuration changed'):
                walk.seed_medium(run)

        # 4. Pre-existing seed manifest beside output refuses isolate_medium
        out2 = self.base / 'run2.json'
        stale_manifest = self.base / 'run2_press_medium_seed.json'
        stale_manifest.write_text('{}', encoding='utf-8')
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('FRAKTAL_HARNESS_HOST_SEED', None)
            os.environ.pop('FRAKTAL_HARNESS_HOST_SEED_SHA256', None)
            with self.assertRaisesRegex(part_execute.FixtureRefused, 'already exists'):
                walk.isolate_medium(out2, canonical_collapse=True)


class CollapsedPressLauncherLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        app = collapse_press.application()
        self.creds = self.base / 'creds.json'
        user_name = app.access_users[0].name
        self.creds.write_text(
            json.dumps({'users': [{'user': user_name, 'pin': '1234', 'level': 4}]}),
            encoding='utf-8',
        )
        self.pin = 'CD' * 32
        self.auth = self.base / 'auth.json'
        self.auth.write_text(json.dumps(dict(
            CurrentOwnerApproved=True,
            MailboxOrTagWritesAuthorized=True,
            Serial='601FC87B',
            CanonicalSha256=self.pin,
            FaultClearAuthorized=False,
            ClockSetAuthorized=False,
        )), encoding='utf-8')

    def test_end_to_end_collapsed_launcher_runs_all_23_rows_without_mo_and_cleans_env(self):
        for decl_name, factory in (('fraktal_ab_press_s6_collapse_echo38', collapse_press.application),
                                   ('fraktal_ab_press_s6_shelving_echo38', shelving_press.application)):
            with self.subTest(declaration=decl_name):
                app = factory()
                sim = SimulatedCollapsedPressController(app, self.base / decl_name)
                (self.base / decl_name).mkdir()
                output = self.base / decl_name / 'press_collapse_evidence.json'
                orig_exec = tower_execute.execute_fixture

                def execute_with_sim(*args, **kwargs):
                    return orig_exec(*args, plc_factory=sim.new_plc, **kwargs)

                self.assertIs(px.module_surface.func, views.module_surface)
                with patch.dict(os.environ, {'FRAKTAL_AB_DECLARATION': decl_name}, clear=False), \
                        patch.object(px, 'APP', app), \
                        patch.object(px, 'module_surface', partial(views.module_surface, app=app)), \
                        patch.object(views, 'bind', side_effect=sim.bind_session), \
                        patch.object(views, 'command', side_effect=sim.handle_command), \
                        patch.object(host_docs, 'restore_configuration', side_effect=sim.restore_configuration), \
                        patch.object(host_docs, 'ready', return_value={'restoring': False}), \
                        patch.object(tower_execute, 'execute_fixture', side_effect=execute_with_sim), \
                        patch.object(walk.time, 'sleep', side_effect=sim.sleep), \
                        patch.object(part_execute.time, 'monotonic', side_effect=lambda: sim.now), \
                        patch.object(part_execute.time, 'sleep', side_effect=sim.sleep), \
                        patch.object(walk.typed, 'authorize', side_effect=AssertionError('MO authorize called')), \
                        patch.object(walk, 'paired_run', side_effect=AssertionError('MO paired_run called')), \
                        patch.object(walk.equivalence, 'run', side_effect=AssertionError('MO equivalence called')):
                    os.environ.pop(walk.ISOLATED_SEED_ENV, None)
                    os.environ.pop('FRAKTAL_HARNESS_HOST_SEED', None)
                    os.environ.pop('FRAKTAL_HARNESS_HOST_SEED_SHA256', None)
                    rc = walk.main([
                        '--authorization-file', str(self.auth),
                        '--expect-acd-sha256', self.pin,
                        '--output', str(output),
                        '--execute-fixture',
                        '--expect-serial', '601FC87B',
                        '--credential-file', str(self.creds),
                    ])
                    # Environment variables must be cleaned up on exit!
                    self.assertNotIn(walk.ISOLATED_SEED_ENV, os.environ)
                    self.assertNotIn('FRAKTAL_HARNESS_HOST_SEED', os.environ)
                    self.assertNotIn('FRAKTAL_HARNESS_HOST_SEED_SHA256', os.environ)

                self.assertEqual(rc, 0)
                evidence = json.loads(output.read_text(encoding='utf-8'))
                self.assertEqual(evidence['schema'], 'fraktal.ab.press-collapse-fixture')
                self.assertEqual(evidence['manifestHash'], views.manifest_hash(app))
                self.assertTrue(evidence['restored'])
                self.assertTrue(evidence['policyRestored'])
                self.assertIsNone(evidence['final']['tower'])
                self.assertTrue(evidence['final']['originalMediumUnchanged'])
                self.assertTrue(evidence['final']['liveDocumentsVerified'])
                self.assertEqual(
                    evidence['pressMedium']['seeded'],
                    ['Press.line', 'Press.model1', 'Press.model2', 'Press.model3', 'Press.station'],
                )
                # 2 leading rows (configuration_preserved, logged_out_manual_refusal) + 3 * 7 rendition rows = 23
                self.assertEqual(len(evidence['rows']), 23)
                self.assertTrue(all(r['passed'] for r in evidence['rows']))
                self.assertEqual(
                    [r['case'] for r in evidence['rows'][:2]],
                    ['configuration_preserved', 'logged_out_manual_refusal'],
                )
                for idx, language in enumerate(decl.RENDITIONS):
                    chunk = evidence['rows'][2 + idx * 7: 2 + (idx + 1) * 7]
                    self.assertTrue(all(r['language'] == language for r in chunk))
                    self.assertEqual(
                        [r['case'] for r in chunk],
                        ['OK', 'handled_NOK', 'HELD_resume', 'abort', 'mode_change',
                         'adopted_fault', 'single_reset_restart'],
                    )
                self.assertTrue(all(p.closed for p in sim.plc_instances))
                self.assertTrue(all(l._closed for l in sim.host_leases))

    def test_collapsed_launcher_cleans_env_even_when_inner_runner_rejects_args(self):
        output = self.base / 'rejected.json'
        with patch.dict(os.environ, {'FRAKTAL_AB_DECLARATION': 'fraktal_ab_press_s6_collapse_echo38'}, clear=False), \
                contextlib.redirect_stderr(io.StringIO()):
            os.environ.pop(walk.ISOLATED_SEED_ENV, None)
            os.environ.pop('FRAKTAL_HARNESS_HOST_SEED', None)
            os.environ.pop('FRAKTAL_HARNESS_HOST_SEED_SHA256', None)
            with self.assertRaises(SystemExit):
                # Missing --execute-fixture triggers parser.error inside live.main
                walk.main([
                    '--authorization-file', str(self.auth),
                    '--expect-acd-sha256', self.pin,
                    '--output', str(output),
                    '--expect-serial', '601FC87B',
                    '--credential-file', str(self.creds),
                ])
            self.assertNotIn(walk.ISOLATED_SEED_ENV, os.environ)
            self.assertNotIn('FRAKTAL_HARNESS_HOST_SEED', os.environ)
            self.assertNotIn('FRAKTAL_HARNESS_HOST_SEED_SHA256', os.environ)


if __name__ == '__main__':
    unittest.main()
