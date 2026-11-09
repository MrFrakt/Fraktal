"""Guarded local Echo acceptance for the exact Part fixture, never production.

Requires an explicit arm flag, expected serial, exact deployed manifest and
local Echo identity. Writes are confined to the existing simulation inputs,
controller-validated configuration staging and sequence-last command frame.
Provider/internal state is never written.
Fixture credentials are read from a local file and never included in evidence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
from fraktal_ab_host_cursor import Cursor
import fraktal_ab_live as live
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as manifest
import fraktal_ab_manifest_read as reader
import fraktal_ab_part_demo as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_set_broker as broker
import fraktal_ab_sets as sets
import fraktal_ab_station as station
import fraktal_ab_fixture_reads as views


class FixtureRefused(RuntimeError):
    pass


class Guarded:
    def __init__(self, comm, serial, app, *, writable=True, plc_factory=None):
        self.comm, self.serial, self.app = comm, serial, app
        self._writable, self._plc_factory = bool(writable), plc_factory
        self._retired_phases, self._phase_closed, self._had_host_lease = [], False, False
        if not writable:
            self.allowed = frozenset()
        elif app.canonical_collapse:
            self.allowed = frozenset(gen.externally_writable(app))
        else:
            raise FixtureRefused('canonical collapsed profile required')
        if app.canonical_collapse:
            self._canonical_hash = views.manifest_hash(app)

    def __getattr__(self, name):
        return getattr(self.comm, name)

    @property
    def ConnectionSize(self):
        return self.comm.ConnectionSize

    @ConnectionSize.setter
    def ConnectionSize(self, value):
        self.comm.ConnectionSize = value

    def _new_plc(self):
        if self._plc_factory is not None:
            fresh = self._plc_factory()
        else:
            from pylogix import PLC
            fresh = PLC('127.0.0.1')
        fresh.ProcessorSlot = 0
        fresh.ConnectionSize = 4000
        fresh.SocketTimeout = 5
        return fresh

    @staticmethod
    def _phase_state(plc):
        return getattr(plc, 'conn', plc)

    @classmethod
    def _phase_children(cls, plc):
        children = getattr(cls._phase_state(plc), '_fraktal_child_leases', None)
        return children if isinstance(children, dict) else {}

    def check_owned_leases(self):
        for retired in self._retired_phases:
            for name, lease in self._phase_children(retired).items():
                if getattr(lease, 'failure', ''):
                    raise FixtureRefused(f'retired {name} lease latched failure: {lease.failure}')
                if not lease._closed:
                    raise FixtureRefused(f'retired {name} lease was not closed')
                if hasattr(lease, 'originals_unchanged') and not lease.originals_unchanged():
                    raise FixtureRefused('original host seed files changed')
        if not self._phase_closed:
            for name, lease in self._phase_children(self.comm).items():
                if getattr(lease, 'failure', ''):
                    raise FixtureRefused(f'owned {name} lease latched failure: {lease.failure}')
                if lease._closed or not lease.alive():
                    raise FixtureRefused(f'owned {name} lease exited unexpectedly; no restart')
                if hasattr(lease, 'originals_unchanged') and not lease.originals_unchanged():
                    raise FixtureRefused('original host seed files changed')

    def originals_unchanged(self):
        phases = [*self._retired_phases, *([] if self._phase_closed else [self.comm])]
        for phase in phases:
            for lease in self._phase_children(phase).values():
                if hasattr(lease, 'originals_unchanged') and not lease.originals_unchanged():
                    return False
        return True

    def close_phase(self):
        if not self.app.canonical_collapse:
            return self.comm.Close()
        if self._phase_closed:
            return None
        self.check_owned_leases()
        had_host = 'host' in self._phase_children(self.comm)
        try:
            return self.comm.Close()
        finally:
            self._retired_phases.append(self.comm)
            self._had_host_lease = self._had_host_lease or had_host
            self._phase_closed = True
            self.check_owned_leases()

    def open_new_phase(self):
        if not self.app.canonical_collapse:
            return None
        if not self._phase_closed:
            raise FixtureRefused('cannot open a new connection phase while the active phase is open')
        self.check_owned_leases()
        previous_state = self._phase_state(self._retired_phases[-1]) if self._retired_phases else None
        fresh = self._new_plc()
        if previous_state is not None:
            fresh_state = self._phase_state(fresh)
            for attr in ('_fraktal_gateway_executable', '_fraktal_gateway_sha256', '_fraktal_gateway_directory'):
                val = getattr(previous_state, attr, None)
                if isinstance(val, (str, Path)):
                    setattr(fresh_state, attr, val)
        self.comm = fresh
        self._phase_closed = False
        try:
            self.guard()
            if self._had_host_lease:
                from fraktal_ab_harness_documents import restore_configuration
                restore_configuration(self, self.app)
        except BaseException:
            try:
                fresh.Close()
            finally:
                self._retired_phases.append(fresh)
                self._phase_closed = True
            raise

    def open_observer(self):
        if not self.app.canonical_collapse:
            return None
        self.check_owned_leases()
        obs_plc = self._new_plc()
        observer = Guarded(obs_plc, self.serial, self.app, writable=False, plc_factory=self._plc_factory)
        try:
            observer.guard()
        except BaseException:
            obs_plc.Close()
            raise
        return observer

    def Close(self):
        return self.comm.Close()

    def Read(self, *args, **kwargs):
        if self._phase_closed:
            raise FixtureRefused('fixture connection phase is closed')
        return self.comm.Read(*args, **kwargs)

    def guard(self):
        if self._phase_closed:
            raise FixtureRefused('fixture connection phase is closed')
        if self.app.canonical_collapse:
            self.check_owned_leases()
        answer = self.comm.GetDeviceProperties()
        value = answer.Value
        if (answer.Status != 'Success' or value is None
                or int(str(value.SerialNumber), 0) != self.serial
                or value.ProductName != 'Emulate 5580 Controller'
                or value.Revision != '38.11' or self.comm.IPAddress != '127.0.0.1'
                or self.comm.ProcessorSlot != 0):
            raise FixtureRefused('exact local Echo identity guard failed')
        if self.app.canonical_collapse:
            state = views.connection_state(self)
            if getattr(state, '_fraktal_fixture_reads', None) is None:
                views.bind(self, self.app, f'{self.serial:08X}')
            held = views._session(self, self.app).reader.manifest_identity()
            if held != dict(Valid=True, Truncated=False, ContentHash=self._canonical_hash):
                raise FixtureRefused('canonical manifest pin acquisition or identity failed')
            return
        raise FixtureRefused('canonical collapsed profile required')

    def Write(self, tag, value):
        if tag not in self.allowed:
            raise FixtureRefused('write outside the declared fixture surface')
        self.guard()
        answer = self.comm.Write(tag, value)
        if answer.Status != 'Success':
            raise FixtureRefused('fixture write refused: ' + tag)
        return answer


class Run:
    def __init__(self, comm, app, account, evidence):
        self.comm, self.app, self.account, self.evidence = comm, app, account, evidence
        self.sequence, self.rows = 0, evidence['rows']
        self.codes = tuple(m.code for m in app.models)

    def command(self, kind, **arguments):
        answer = (views.command(self.comm, kind, app=self.app, settle=4, **arguments)
                  if self.app.canonical_collapse else px.command(self.comm, kind, settle=4, **arguments))
        if not answer['accepted']:
            raise FixtureRefused(f'mailbox refused command {kind}, diagnostic key {answer["diagnosticKey"]}')
        return answer

    def unit(self):
        value = views.unit_surface(self.comm, app=self.app) if self.app.canonical_collapse else px.unit_surface(self.comm)
        if value is None:
            raise FixtureRefused('Unit read failed')
        return value

    def module(self, name):
        return (views.module_surface(self.comm, name, app=self.app)
                if self.app.canonical_collapse else px.module_surface(self.comm, name))

    def wait(self, test, label, timeout=8):
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            last = test()
            if last:
                return last
            time.sleep(.01)
        u = self.unit()
        raise FixtureRefused(f'{label} timed out: step={u["Step"]}, error={u["ErrorID"]}')

    def login(self):
        self.command(mb.LOGIN, User=self.account['user'], Secret=self.account['pin'])
        def settled():
            state = views.read_access(self.comm, app=self.app)
            return state is not None and not state['LoginBusy'] and state['CurrentLevel'] == self.account['level']
        self.wait(settled, 'login', timeout=15)

    def restore_configuration(self):
        """Commission through the existing keeper and controller set validator."""
        if self.app.canonical_collapse:
            from fraktal_ab_harness_documents import restore_configuration
            self.evidence['configuration'] = restore_configuration(self.comm, self.app)
            return
        raise FixtureRefused('canonical collapsed profile required')

    def set(self, tag, value):
        if self.app.canonical_collapse:
            if tag not in gen.externally_writable(self.app):
                raise AssertionError(f'tag outside the declared write surface: {tag}')
            if not px._success(self.comm.Write(tag, value)):
                raise FixtureRefused('stimulus write failed')
            return
        raise FixtureRefused('canonical collapsed profile required')

    def idle(self):
        for tag in (*px.FAULT.values(), *px.HOLD.values()):
            self.set(tag, 0)
        self.command(mb.STOP)
        self.command(mb.OPERATOR_RESET)
        self.command(mb.SET_RUN_STYLE, IntValue=decl.RUN_CONTINUOUS)
        self.set(px.TWO_HAND, 0)

    def home(self):
        self.idle()
        self.set(px.AIR_OK, 1)
        self.set(px.PART_PRESENT, 1)
        self.command(mb.SET_MODE, IntValue=px.MODE_HOME)
        self.wait_ready_mode(px.MODE_HOME)
        self.command(mb.START)
        self.wait(lambda: self.unit()['Complete'], 'HOME')
        self.command(mb.STOP)
        self.command(mb.OPERATOR_RESET)
        self.command(mb.SET_MODE, IntValue=px.MODE_AUTO)
        # Mode application is the boundary here. The next START consumes the
        # controller's release report; a retained HOME result is not its gate.
        self.wait(lambda: self.unit()['Mode'] == px.MODE_AUTO, 'AUTO mode applied')

    def wait_ready_mode(self, mode):
        # The mailbox acknowledges the request before the Unit consumes its
        # mode change. START must see that completed transition and its reset.
        def settled():
            unit = self.unit()
            return unit if unit['Mode'] == mode and not any(
                unit[k] for k in ('Running', 'Complete', 'Error', 'Aborted')) else None
        self.wait(settled, 'ready mode '+str(mode))

    def begin(self):
        if not self.app.canonical_collapse:
            # The real helper owns two-hand arming and START ordering.
            answer = px.start_cycle(self.comm, 4)
            if not answer['accepted']:
                raise FixtureRefused('START refused')
            return
        self.set(px.TWO_HAND, 0)
        answer = views.command(self.comm, mb.START, app=self.app, settle=1.0)
        if not answer['accepted']:
            raise FixtureRefused('START refused')
        self.set(px.TWO_HAND, 0)
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline:
            observed = views.module_surface(self.comm, 'TwoHand', app=self.app)
            if observed is None or observed.get('OutImm_Armed') != 0:
                break
            time.sleep(0.005)
        self.set(px.TWO_HAND, 1)

    def batch(self):
        return views.host_events(self.comm, app=self.app)

    def verify_sink(self, output):
        """Read-only PLC acquisition; a rejected event cannot advance its cursor."""
        cursor_path, sink_path = output.with_suffix('.cursor.json'), output.with_suffix('.sink.jsonl')
        self.check(not cursor_path.exists() and not sink_path.exists(), 'sink fixture files already exist')
        batch = self.batch()
        source = self.evidence['serial'] + ':' + views.manifest_hash(self.app)
        cursor = Cursor(self.app.name, cursor_path, source=source)
        rejected = []
        def refuse(record):
            rejected.append(record)
            return False
        self.check(not cursor.deliver(batch, refuse) and not cursor_path.exists(), 'rejected sink advanced cursor')
        delivered = []
        with sink_path.open('x', encoding='utf-8') as out:
            def accept(record):
                out.write(json.dumps(record, sort_keys=True)+'\n')
                out.flush()
                os.fsync(out.fileno())
                delivered.append(record)
                return True
            self.check(cursor.deliver(batch, accept), 'durable sink refused batch')
        restarted = Cursor(self.app.name, cursor_path, source=source)
        replay = []
        self.check(restarted.deliver(batch, lambda record: replay.append(record) or True)
                   and not replay, 'sink restart repeated acknowledged interval')
        self.evidence['sink'] = dict(rejectedWithoutAdvance=bool(rejected),
            events=sum(r['kind']=='event' for r in delivered),
            losses=[r for r in delivered if r['kind']=='dataLoss'],
            replayedAfterReopen=len(replay), cursor=restarted.state, file=str(sink_path))

    def boundary(self):
        return self.batch()['metadata']['NewestSequence'], self.unit()

    def record(self, language, case, before, counters, **extra):
        batch = self.batch()
        rows = [e for e in batch['events'] if e['Sequence'] > before]
        if batch['metadata']['NewestSequence'] - before > self.app.host_event_capacity:
            raise FixtureRefused('fixture event interval was overwritten')
        u = self.unit()
        delta = {n:u[n]-counters[n] for n in ('GoodCount','ScrapCount','ReworkCount','CycleCount')}
        row = dict(language=language, case=case, passed=False, counters=delta,
                   events=rows, part=views.part_values(self.comm, app=self.app), **extra)
        self.rows.append(row)
        return row

    def complete(self, baseline):
        self.wait(lambda: self.unit()['CycleCount'] > baseline['CycleCount'], 'cycle finish')

    def check(self, condition, message):
        if not condition:
            raise FixtureRefused(message)

    def happy(self, language, case='OK'):
        self.home()
        before, baseline = self.boundary()
        self.begin()
        self.complete(baseline)
        row = self.record(language, case, before, baseline)
        part_events = [e for e in row['events'] if 1 <= e['Kind'] <= 4]
        self.check([e['Kind'] for e in part_events] == [1,2,3], 'OK lifecycle order')
        self.check(len({e['PartUid'] for e in part_events}) == 1 and bool(part_events[0]['PartUid']), 'OK identity continuity')
        self.check(row['counters']['GoodCount'] == 1 and row['counters']['ScrapCount'] == 0, 'OK verdict count')
        self.check(row['part']['Part/Result/Verdict'] == 1 and not row['part']['Part/Present'], 'OK committed result')
        self.check(row['part']['Part/Result/Records[2]/Value'] == 100, 'PLC measurement value')
        return row

    def nok(self, language):
        self.home()
        before, baseline = self.boundary()
        self.set(px.FAULT['PressRam'], 1)
        self.begin()
        self.wait(lambda: self.unit()['DecisionId'] != 0, 'handled ram fault decision')
        self.command(mb.DECISION_ANSWER, IntValue=1)
        self.set(px.FAULT['PressRam'], 0)
        self.complete(baseline)
        row = self.record(language,'handled_NOK',before,baseline)
        kinds = [e['Kind'] for e in row['events'] if e['Kind'] in (1,2,3,4,10)]
        self.check(kinds == [1,2,3,10], 'NOK lifecycle/count event order')
        self.check(row['counters']['GoodCount'] == 0 and row['counters']['ScrapCount'] == 1, 'NOK must not count good')
        self.check(row['part']['Part/Result/Verdict'] == 2 and row['part']['Part/Result/ReasonCode'] != 0, 'NOK first-out')

    def held(self, language, ending='resume'):
        self.home()
        before, baseline = self.boundary()
        self.set(px.HOLD['PressRam'], 1)
        self.begin()
        self.wait(lambda: (self.module('PressRam') or {}).get('OutImm_Held'), 'recoverable hold')
        present = views.part_identity(self.comm, app=self.app)
        self.check(present['Present'] != 0,'part must be present during hold')
        identity = present['Uid']
        if ending == 'resume':
            time.sleep(.75)  # exceeds the cylinder command's 500 ms timeout
            self.check(self.unit()['Error'] == 0 and self.unit()['Running'] == 1,'held timeout must not accrue')
            self.set(px.HOLD['PressRam'],0)
            self.complete(baseline)
            row = self.record(language,'HELD_resume',before,baseline,heldUid=identity)
            self.check([e['Kind'] for e in row['events'] if 1 <= e['Kind'] <= 4] == [1,2,3], 'HELD event continuity')
            self.check(row['part']['Part/Uid'] == identity and row['counters']['GoodCount'] == 1,'HELD preserves identity and counts once')
        else:
            self.command(mb.STOP if ending == 'abort' else mb.SET_MODE,
                         **({} if ending == 'abort' else dict(IntValue=self.app.manual_mode)))
            self.wait(lambda: not views.part_identity(self.comm, app=self.app)['Present'], 'part abort')
            self.set(px.HOLD['PressRam'],0)
            row = self.record(language,'abort' if ending == 'abort' else 'mode_change',before,baseline)
            self.check([e['Kind'] for e in row['events'] if 1 <= e['Kind'] <= 4] == [1,4], 'abort must occur once without processed')
            self.check(row['counters']['GoodCount'] == row['counters']['ScrapCount'] == 0,'aborted part must not count')

    def adopted_fault(self, language):
        self.home()
        before, baseline = self.boundary()
        self.set(px.FAULT['PartSlide'],1)
        self.begin()
        failed = self.wait(lambda: self.unit() if self.unit()['Error'] else None, 'adopted slide fault')
        self.wait(lambda: not views.part_identity(self.comm, app=self.app)['Present'],'fault abort')
        row = self.record(language,'adopted_fault',before,baseline,firstOut=failed['ErrorID'])
        aborted = [e for e in row['events'] if e['Kind'] == 4]
        self.check(len(aborted) == 1 and aborted[0]['ReasonCode'] == failed['ErrorID'], 'fault abort preserves first-out')
        self.set(px.FAULT['PartSlide'],0)
        self.command(mb.OPERATOR_RESET)
        self.wait(lambda: self.unit()['Error'] == self.unit()['Aborted'] == self.unit()['Running'] == 0,'one-reset readiness')
        after, fresh = self.boundary()
        self.begin()
        self.complete(fresh)
        resumed = self.record(language,'single_reset_restart',after,fresh)
        self.check(resumed['counters']['GoodCount'] == 1,'single-reset restart must process normally')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-fixture',action='store_true')
    parser.add_argument('--expect-serial',required=True)
    parser.add_argument('--credential-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--language',choices=decl.RENDITIONS,action='append')
    args = parser.parse_args(argv)
    if not args.execute_fixture:
        parser.error('--execute-fixture is required before any write')
    if station.module_name() != 'fraktal_ab_part_demo':
        parser.error('select exactly FRAKTAL_AB_DECLARATION=fraktal_ab_part_demo')
    if args.output.exists():
        parser.error('refusing existing evidence output')
    if any(args.output.with_suffix(suffix).exists() for suffix in ('.cursor.json', '.sink.jsonl')):
        parser.error('refusing existing sink fixture output')
    app = fixture.application()
    account = next(a for a in json.loads(args.credential_file.read_text())['users'] if a['level'] == 4)
    if account['user'] not in {u.name for u in app.access_users}:
        parser.error('credential file does not identify a declared fixture account')
    from pylogix import PLC
    evidence = dict(schema='fraktal.ab.part-live-fixture',schemaVersion=1,serial=args.expect_serial,
                    manifestHash=views.manifest_hash(app),rows=[],restored=False)
    with PLC('127.0.0.1') as native:
        native.ProcessorSlot=0
        native.ConnectionSize=4000
        native.SocketTimeout=5
        comm=Guarded(native,int(args.expect_serial,16),app)
        comm.guard()
        original={tag:px.read_scalar(comm,tag) for tag in gen.externally_writable(app)}
        if any(v is None for v in original.values()):
            raise FixtureRefused('fixture input snapshot incomplete')
        original_mode=views.unit_surface(comm, app=app)['Mode']
        initial_access=views.read_access(comm, app=app)
        if initial_access['CurrentLevel'] != 0:
            raise FixtureRefused('another controller session is active')
        run=Run(comm,app,account,evidence)
        try:
            run.login()
            run.restore_configuration()
            for language in args.language or decl.RENDITIONS:
                run.idle()
                run.set(gen.rendition_tag(app),gen.rendition_ordinal(language))
                for operation in (run.happy,run.nok,run.held,
                                  lambda lang:run.held(lang,'abort'),
                                  lambda lang:run.held(lang,'mode'),run.adopted_fault):
                    first = len(run.rows)
                    operation(language)
                    for row in run.rows[first:]:
                        row['passed'] = True
                print(json.dumps(dict(language=language,passed=True,rows=len(run.rows))),flush=True)
            run.verify_sink(args.output)
        except Exception as error:
            evidence['error']=str(error)
            raise
        finally:
            try:
                run.idle()
                run.command(mb.SET_MODE,IntValue=original_mode)
                for tag,value in original.items():
                    run.set(tag,value)
                run.command(mb.LOGOUT)
                u=run.unit()
                evidence['restored']=(u['Running']==u['Error']==u['Aborted']==0 and
                    all(px.read_scalar(comm,k)==v for k,v in original.items()) and
                    views.read_access(comm, app=app)['CurrentLevel']==0)
            finally:
                try:
                    comm.Close()
                finally:
                    args.output.write_text(json.dumps(evidence,indent=2)+'\n')
    return 0 if evidence['restored'] else 1


if __name__=='__main__':
    raise SystemExit(main())
