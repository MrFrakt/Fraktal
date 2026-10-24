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
import fraktal_ab_host_events as host
import fraktal_ab_live as live
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as manifest
import fraktal_ab_manifest_read as reader
import fraktal_ab_part as part
import fraktal_ab_part_demo as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
import fraktal_ab_set_broker as broker
import fraktal_ab_sets as sets
import fraktal_ab_station as station


class FixtureRefused(RuntimeError):
    pass


class Guarded:
    def __init__(self, comm, serial, app):
        self.comm, self.serial, self.app = comm, serial, app
        self.allowed = frozenset(gen.externally_writable(app)) | frozenset(
            tag for tag, _ in mb.command_writes(app, mb.STOP, 1)) | frozenset(
            mb.request_tag_name(app) + '.ConfigSet.' + member.name for member in sets.request_members())

    def __getattr__(self, name):
        return getattr(self.comm, name)

    @property
    def ConnectionSize(self):
        return self.comm.ConnectionSize

    @ConnectionSize.setter
    def ConnectionSize(self, value):
        self.comm.ConnectionSize = value

    def guard(self):
        answer = self.comm.GetDeviceProperties()
        value = answer.Value
        if (answer.Status != 'Success' or value is None
                or int(str(value.SerialNumber), 0) != self.serial
                or value.ProductName != 'Emulate 5580 Controller'
                or value.Revision != '38.11' or self.comm.IPAddress != '127.0.0.1'
                or self.comm.ProcessorSlot != 0):
            raise FixtureRefused('exact local Echo identity guard failed')
        raw, status, _ = reader._read_raw(self.comm, manifest.header_tag(self.app))
        if raw is None:
            raise FixtureRefused('manifest header acquisition failed')
        projection.validate(reader.decode_header(raw))

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
        answer = px.command(self.comm, kind, settle=4, **arguments)
        if not answer['accepted']:
            raise FixtureRefused(f'mailbox refused command {kind}, diagnostic key {answer["diagnosticKey"]}')
        return answer

    def unit(self):
        value = px.read_unit(self.comm)
        if value is None:
            raise FixtureRefused('Unit read failed')
        return value

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
            state = projection.read_access(self.comm)
            return state is not None and not state['LoginBusy'] and state['CurrentLevel'] == self.account['level']
        self.wait(settled, 'login', timeout=15)

    def restore_configuration(self):
        """Commission through the existing keeper and controller set validator."""
        from fraktal_ab_gateway import MailboxWriter
        directory = live.live_directory(self.app, self.evidence['serial'])
        keeper = live.Keeper(self.app, live.FileMedium(directory))
        held = projection.read_document(self.comm)['liveConfig']
        writer = MailboxWriter('127.0.0.1', 0, self.evidence['serial'])
        def command(kind, document, *, name='', model=0, store_result=0):
            sequence = px.seed_sequence(self.comm) + 1
            root = self.app.name + '/HmiRequest/'
            writes = [(root+'Kind','int32',kind), (root+'TextValue','string',live.LIVE_NAME),
                      (root+'NameValue','string',name), (root+'BoolValue','boolean',kind == mb.CREATE_MODEL),
                      (root+'DurationMs','uint32',model), (root+'Sequence','uint32',sequence)]
            return broker.restore_command(self.comm,self.app,writes,writer._write_base,document,store_result)
        restoring = held.restoring
        if restoring:
            self.check(keeper.wants_restore(held), 'configuration restore is not authorized')
            outcome = keeper.run_restore(held, command)
            self.check(outcome is not None and outcome.complete, 'configuration restore failed: '+keeper.error)
            self.check(not outcome.losses, 'configuration medium has lost documents')
        after = projection.read_document(self.comm)['liveConfig']
        self.check(not after.restoring, 'configuration is still restoring')
        written = keeper.keep(after)
        self.check(not keeper.failed, 'configuration medium persistence failed')
        self.evidence['configuration'] = dict(wasRestoring=restoring, restoring=after.restoring,
            medium=str(directory), written=written, health=keeper.health())

    def set(self, tag, value):
        if not px.write(self.comm, tag, value):
            raise FixtureRefused('stimulus write failed')

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
        # The real helper owns two-hand arming and START ordering.
        answer = px.start_cycle(self.comm, 4)
        if not answer['accepted']:
            raise FixtureRefused('START refused')

    def batch(self):
        return host.read(self.comm, self.app, self.codes)

    def verify_sink(self, output):
        """Read-only PLC acquisition; a rejected event cannot advance its cursor."""
        cursor_path, sink_path = output.with_suffix('.cursor.json'), output.with_suffix('.sink.jsonl')
        self.check(not cursor_path.exists() and not sink_path.exists(), 'sink fixture files already exist')
        batch = self.batch()
        source = self.evidence['serial'] + ':' + manifest.content_hash(self.app)
        cursor = host.Cursor(self.app.name, cursor_path, source=source)
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
        restarted = host.Cursor(self.app.name, cursor_path, source=source)
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
                   events=rows, part=part.project(self.app, part.read(self.comm,self.app)), **extra)
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
        self.wait(lambda: (px.read_module(self.comm,'PressRam') or {}).get('OutImm_Held'), 'recoverable hold')
        present = part.read(self.comm,self.app)
        self.check(present['Present'] != 0,'part must be present during hold')
        identity = part.uid(present['Uid'])
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
            self.wait(lambda: not part.read(self.comm,self.app)['Present'], 'part abort')
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
        self.wait(lambda: not part.read(self.comm,self.app)['Present'],'fault abort')
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
                    manifestHash=manifest.content_hash(app),rows=[],restored=False)
    with PLC('127.0.0.1') as native:
        native.ProcessorSlot=0
        native.ConnectionSize=4000
        native.SocketTimeout=5
        comm=Guarded(native,int(args.expect_serial,16),app)
        comm.guard()
        # Validate all static rows and native type layouts before the first write.
        projection.read_document(comm)
        original={tag:px.read_scalar(comm,tag) for tag in gen.externally_writable(app)}
        if any(v is None for v in original.values()):
            raise FixtureRefused('fixture input snapshot incomplete')
        original_mode=px.read_unit(comm)['Mode']
        initial_access=projection.read_access(comm)
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
                    projection.read_access(comm)['CurrentLevel']==0)
            finally:
                args.output.write_text(json.dumps(evidence,indent=2)+'\n')
    return 0 if evidence['restored'] else 1


if __name__=='__main__':
    raise SystemExit(main())
