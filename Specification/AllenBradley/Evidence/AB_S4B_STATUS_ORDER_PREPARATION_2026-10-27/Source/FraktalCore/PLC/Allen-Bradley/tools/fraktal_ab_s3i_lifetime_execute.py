"""Fixed S3i calendar/lifetime acceptance on local Echo, never production.

Only public Line WRITE_CONFIG capabilities are changed. A fresh published
Line.LastUpdate positions one twelve-hour interval to end three minutes later.
The original empty calendar is restored while the interval runs; the producer
must close it naturally before applying that queued restoration. A separate
guarded SDK helper owns the subsequently authorized Program/Run cycle.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
import argparse
import gzip
import json
from pathlib import Path
import re
import time

import fraktal_ab_canonical_publication as publication
import fraktal_ab_genealogy_s3i_demo as candidate
import fraktal_ab_generate as gen
import fraktal_ab_line as line
import fraktal_ab_mailbox as mb
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
import fraktal_ab_s3a_fixture_execute as capture
import fraktal_ab_s3b_fixture_execute as observer
import fraktal_ab_s3f_fixture_execute as manifest_fixture
import fraktal_ab_s3i_equivalence as equivalence
import fraktal_ab_s3i_native_checks as native_checks
import fraktal_ab_station as station

SERIAL='601FC87B'
ACD='A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
MAX_CONFIG_WRITES=64
TARGET,TEMPORARY_TARGET=40,99
DURATION_MINUTES=720
BOUNDARY_WAIT_SECONDS=220


def authorize(path):
    value=json.loads(path.read_text(encoding='utf-8'))
    if (value.get('CurrentOwnerApproved') is not True or value.get('Serial')!=SERIAL
            or value.get('CanonicalSha256')!=ACD or value.get('CalendarLifetimeVectorsAuthorized') is not True
            or value.get('RetainedCycleAuthorized') is not True
            or value.get('FaultClearAuthorized') is not False or value.get('ClockSetAuthorized') is not False):
        raise fixture.FixtureRefused('current exact-image calendar/lifetime authorization required')
    return value


def parse_stamp(text):
    if not isinstance(text,str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3,9}Z',text):
        raise fixture.FixtureRefused('fresh published Line UTC timestamp required')
    return datetime.fromisoformat(text[:-1]+'+00:00')


@dataclass(frozen=True)
class Interval:
    observed:datetime
    end:datetime

    @property
    def start(self):return self.end-timedelta(minutes=DURATION_MINUTES)

    def values(self):
        return dict(StartMin1=self.start.hour*60+self.start.minute,DurationMin1=DURATION_MINUTES,
            ProductionTarget1=TARGET,ActiveDays1=1<<self.start.weekday())

    def document(self):
        stamp=lambda v:v.isoformat(timespec='milliseconds').replace('+00:00','Z')
        return dict(observed=stamp(self.observed),start=stamp(self.start),end=stamp(self.end),
            utcOffsetMin=0,**self.values())


def interval(text):
    observed=parse_stamp(text);end=observed.replace(second=0,microsecond=0)+timedelta(minutes=3)
    result=Interval(observed,end)
    if not 1970<=result.start.year<=result.end.year<=2099:
        raise fixture.FixtureRefused('interval exceeds the declared Line clock range')
    return result


def capabilities(app):
    result={m.name:(ordinal,m) for ordinal,record,m in gen.editable_values(app) if record.line_cfg}
    if line.MAX_SHIFTS!=5 or line.HISTORY!=8 or len(result)!=21:
        raise fixture.FixtureRefused('fixed five-slot/eight-history Line profile required')
    return result


def original_values(app,values):
    caps=capabilities(app)
    if values is None or set(values)!={'SchemaVersion',*caps} or values['SchemaVersion']!=3:
        raise fixture.FixtureRefused('complete Line V3 original unavailable')
    for name,(_,member) in caps.items():
        value=values[name]
        if type(value) is not int or not member.minimum<=value<=member.maximum:
            raise fixture.FixtureRefused('original Line capability outside its domain')
    rows=tuple((values[f'StartMin{i}'],values[f'DurationMin{i}'],values[f'ActiveDays{i}']) for i in range(1,6))
    line.validate_calendar(values['UtcOffsetMin'],rows)
    if any(start>=0 and days for start,duration,days in rows):
        raise fixture.FixtureRefused('lifetime fixture requires the original empty calendar')
    return dict(values)


def restoration(values):
    # Every intermediate proposal remains a valid whole calendar. Original day
    # masks are installed last, after their starts, durations, targets and offset.
    days=[f'ActiveDays{i}' for i in range(1,6)]
    return [(name,0) for name in days]+[(name,value) for name,value in values.items()
        if name not in ('SchemaVersion',*days)]+[(name,values[name]) for name in days]


def line_snapshot(report):
    pair=report['pair'];count=pair['legacyInputs']['additional']['line_shift']['Count']
    wanted=equivalence.line_paths(candidate.application(),canonical=True,count=count)
    values=pair['canonical']['values'];types=pair['canonical']['types']
    if not wanted<=values.keys():raise fixture.FixtureRefused('incomplete Line lifetime snapshot')
    return dict(values={p:values[p] for p in sorted(wanted)},types={p:types[p] for p in sorted(wanted)})


class CalendarRun(fixture.Run):
    def __init__(self,comm,app,account,evidence,destination):
        super().__init__(comm,app,account,evidence)
        self.destination=destination;self.caps=capabilities(app);self.by_ordinal={o:(n,m) for n,(o,m) in self.caps.items()}
        self.config_writes=0;self.login_committed=False

    def access(self):
        state=projection.read_access(self.comm)
        if state is None:raise fixture.FixtureRefused('controller session unavailable')
        return state

    def owns_session(self,state):
        length=state['UserLength']
        return state['CurrentLevel']==4 and type(length) is int and 0<=length<=len(state['UserBytes']) and (
            bytes(v&255 for v in state['UserBytes'][:length])==self.account['user'].encode('ascii'))

    def check_idle(self):
        u=self.unit()
        self.check(u['Mode']==self.app.manual_mode and not any(u[n] for n in
            ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')),'MANUAL/idle Unit required')

    def command(self,kind,**arguments):
        if kind not in (mb.LOGIN,mb.LOGOUT,mb.WRITE_CONFIG,mb.QUERY_CONFIG):
            raise fixture.FixtureRefused('command outside the fixed lifetime surface')
        self.check_idle()
        if kind==mb.WRITE_CONFIG:
            if set(arguments)!={mb.CONFIG_ORDINAL_MEMBER,mb.CONFIG_VALUE_MEMBER}:
                raise fixture.FixtureRefused('only one public Line capability frame is allowed')
            ordinal,value=arguments[mb.CONFIG_ORDINAL_MEMBER],arguments[mb.CONFIG_VALUE_MEMBER]
            if type(ordinal) is not int or ordinal not in self.by_ordinal:
                raise fixture.FixtureRefused('write outside the public Line capabilities')
            name,member=self.by_ordinal[ordinal]
            if type(value) is not int or not member.minimum<=value<=member.maximum:
                raise fixture.FixtureRefused('calendar value outside its declared domain')
            if self.config_writes>=MAX_CONFIG_WRITES:raise fixture.FixtureRefused('calendar write budget exhausted')
            self.check(self.login_committed and self.owns_session(self.access()),'fixture administrator session required')
            self.config_writes+=1
        elif kind==mb.QUERY_CONFIG:
            if arguments!=dict(IntValue=0,DurationMs=0):raise fixture.FixtureRefused('only page-zero/current-model query allowed')
        elif kind==mb.LOGIN:
            if arguments!=dict(User=self.account['user'],Secret=self.account['pin']):
                raise fixture.FixtureRefused('only the declared fixture account may log in')
            self.check(self.access()['CurrentLevel']==0,'another operator session is active')
        elif arguments:raise fixture.FixtureRefused('logout has no arguments')
        if kind==mb.LOGOUT:
            state=self.access()
            self.check(self.login_committed and (state['CurrentLevel']==0 or self.owns_session(state)),
                'refusing to log out an unrelated session')
        answer=super().command(kind,**arguments)
        if kind==mb.LOGIN:self.login_committed=True
        # No LOGIN argument, secret or account contents enter the evidence.
        if kind==mb.WRITE_CONFIG:self.evidence.setdefault('calendarWrites',[]).append(
            dict(name=name,ordinal=ordinal,value=value,sequence=answer['sequence'],accepted=True))
        return answer

    def write_value(self,name,value):
        ordinal=self.caps[name][0]
        return self.command(mb.WRITE_CONFIG,**{mb.CONFIG_ORDINAL_MEMBER:ordinal,mb.CONFIG_VALUE_MEMBER:value})

    def read_config(self):
        record=line.cfg(self.app)
        return px.read_flat(self.comm,record.name+'Tag',tuple(m.name for m in record.members))

    def restore_line(self,original):
        for name,value in restoration(original):self.write_value(name,value)
        self.check(self.read_config()==original,'original public Line configuration not restored')

    def observe(self,phase):
        self.command(mb.QUERY_CONFIG,IntValue=0,DurationMs=0)
        # The mailbox leaves this writer at its 500-byte frame size. Pairs use
        # the fixture's independent 4,000-byte observer, as every capture does.
        return capture.capture_pair(self,self.destination,lambda comm:observer.capture_gate(comm,equivalence.run),
                                    key='s3iLifetimePairs',kind='lifetime',metadata=dict(phase=phase))

    def value(self,report,path):return report['pair']['canonical']['values'][self.app.name+'/'+path]

    def scalar(self,name):
        result=px.read_scalar(self.comm,self.app.name+'.'+name)
        if type(result) is not int:raise fixture.FixtureRefused('required public lifetime scalar unavailable')
        return result

    def row(self,case,**detail):self.rows.append(dict(case=case,passed=True,**detail))

    def calendar(self):
        original=None;error=None
        # A refused preflight must never reach a finally-block LOGOUT.
        self.check(self.access()['CurrentLevel']==0,'another operator session is active')
        self.check_idle()
        try:
            self.login();self.restore_configuration()
            original=original_values(self.app,self.read_config());self.evidence['originalLine']=original
            first=self.observe('original_empty_profile')
            self.check(self.value(first,'CurrentShift')==0 and self.value(first,'ShiftHistoryCount')==0
                and not self.value(first,'ShiftCalendarPending'),'fresh empty native owner required')
            self.row('original_empty_profile')
            # A no-op public commit obtains the PLC clock through its owning
            # published timestamp. No private clock read or clock set exists.
            self.write_value('UtcOffsetMin',original['UtcOffsetMin'])
            fresh=self.observe('fresh_published_clock');plan=interval(self.value(fresh,'Line/LastUpdate'))
            self.evidence['interval']=plan.document()
            for i in range(1,6):self.write_value(f'ActiveDays{i}',0)
            self.write_value('UtcOffsetMin',0)
            for name,value in plan.values().items():self.write_value(name,value)
            self.wait(lambda:self.scalar('CurrentShift')==1,'temporary interval selection')
            active=self.observe('interval_selected')
            self.check(self.value(active,'ShiftProductionTarget')==TARGET and self.value(active,'ShiftHistoryCount')==1,
                'entry must close unscheduled accounting and latch the selected target')
            self.check(parse_stamp(self.value(active,'ShiftEndsAt'))==plan.end,'published natural boundary differs')
            self.check(self.value(active,'ShiftHistory[1]/ShiftIndex')==0,'first closure must be unscheduled')
            started=self.value(active,'ShiftStartedAt');self.row('natural_interval_selected',target=TARGET)
            self.write_value('ProductionTarget1',TEMPORARY_TARGET)
            pending=self.observe('target_edit_deferred')
            self.check(self.value(pending,'ShiftCalendarPending') and self.value(pending,'ShiftProductionTarget')==TARGET,
                'target edit must not replace the running snapshot')
            self.row('target_edit_deferred',requested=TEMPORARY_TARGET,latched=TARGET)
            self.restore_line(original)
            queued=self.observe('original_calendar_restore_deferred')
            self.check(self.value(queued,'ShiftCalendarPending') and self.value(queued,'CurrentShift')==1
                and self.value(queued,'ShiftProductionTarget')==TARGET,'original calendar must remain queued to the real boundary')
            self.row('original_calendar_restore_deferred')
            self.wait(lambda:self.scalar('CurrentShift')==0 and self.scalar('ShiftHistoryCount')==2,
                'natural calendar closure',timeout=BOUNDARY_WAIT_SECONDS)
            closed=self.observe('natural_closure_history')
            self.check(not self.value(closed,'ShiftCalendarPending') and self.value(closed,'ShiftEndsAt')==0
                and self.value(closed,'ShiftProductionTarget')==0,'empty original must apply after closure')
            self.check(self.value(closed,'ShiftHistory[1]/ShiftIndex')==1
                and self.value(closed,'ShiftHistory[1]/ProductionTarget')==TARGET
                and self.value(closed,'ShiftHistory[1]/StartAt')==started
                and not self.value(closed,'ShiftHistory[1]/ManualReset'),'closed scheduled row differs')
            ended=parse_stamp(self.value(closed,'ShiftHistory[1]/EndAt'))
            self.check(plan.end<=ended<plan.end+timedelta(minutes=1),'closure was early or skipped its real minute')
            self.check(self.value(closed,'ShiftHistory[2]/ShiftIndex')==0,'history is not newest first')
            self.row('natural_closure_history',occupiedRows=2,fieldsPerRow=21)
            self.check(self.read_config()==original,'closure changed the original configuration')
            self.row('closed_target_immutable',target=TARGET,originalTarget=original['ProductionTarget1'])
        except Exception as caught:
            error=f'{type(caught).__name__}: {caught}';self.evidence['error']=error
        finally:
            try:
                if original is not None and self.read_config()!=original:
                    if not self.owns_session(self.access()):self.login()
                    self.restore_line(original)
                if self.login_committed:self.command(mb.LOGOUT)
                self.check(projection.read_access(self.comm)['CurrentLevel']==0,'logout failed')
                self.check_idle()
                self.evidence['configurationRestored']=original is not None and self.read_config()==original
                if error is None:
                    final=self.observe('retention_before')
                    self.evidence['retentionExpected']=line_snapshot(final)
                    self.row('public_configuration_restored_and_logged_out')
            except Exception as caught:
                self.evidence['cleanupError']=f'{type(caught).__name__}: {caught}'
            self.evidence['calendarWriteCount']=self.config_writes
        self.evidence['passed']=error is None and 'cleanupError' not in self.evidence
        return self.evidence['passed']


def image_guard(comm):
    from fraktal_ab_canonical_reader import read_document
    app=candidate.application();unused,capture_data=read_document(comm,expect_serial=SERIAL)
    if capture_data['manifest']['contentHash']!=manifest_fixture.expected_manifest(app):
        raise fixture.FixtureRefused('exact S3i publication required')
    return native_checks.read_results(comm)


def verify_retention(comm,before,destination):
    app=station.application();unit=px.read_unit(comm);access=projection.read_access(comm)
    if unit is None or unit['Mode']!=app.manual_mode or any(unit[n] for n in
            ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')) or access['CurrentLevel']!=0:
        raise fixture.FixtureRefused('retention comparison requires MANUAL/idle and logged out')
    if before.get('passed') is not True or 'retentionExpected' not in before:
        raise fixture.FixtureRefused('successful natural calendar evidence required')
    report=equivalence.run(comm)
    path=destination.with_name(destination.stem+'_pair.json.gz')
    with gzip.open(path,'xt',encoding='utf-8') as f:json.dump(report,f,indent=2,allow_nan=False)
    if not report['passed']:raise fixture.FixtureRefused('retained equivalence failed')
    actual=line_snapshot(report)
    if actual!=before['retentionExpected']:raise fixture.FixtureRefused('retained Line metadata/history values or types differ')
    return dict(passed=True,readOnly=True,pair=str(path),line=actual,nativeFirstScanChecks=image_guard(comm),
        rows=[dict(case='retained_line_metadata_history_and_types',passed=True)],controllerWrites=0)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('calendar','retention'),required=True)
    parser.add_argument('--execute-fixture',action='store_true');parser.add_argument('--expect-serial',required=True)
    parser.add_argument('--authorization-file',required=True,type=Path);parser.add_argument('--credential-file',type=Path)
    parser.add_argument('--before',type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    if not args.execute_fixture or args.expect_serial!=SERIAL or station.module_name()!='fraktal_ab_genealogy_demo':
        parser.error('explicit arm, exact genealogy declaration and local serial required')
    if args.output.exists() or (args.phase=='calendar' and args.credential_file is None) or (args.phase=='retention' and args.before is None):
        parser.error('new output and phase-specific inputs required')
    authorize(args.authorization_file)
    from pylogix import PLC
    evidence=dict(schema='fraktal.ab.s3i-calendar-lifetime',schemaVersion=1,serial=SERIAL,rows=[],passed=False)
    try:
        with PLC('127.0.0.1') as native:
            native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,10
            app=station.application();comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
            evidence['initialNativeChecks']=image_guard(comm)
            if args.phase=='calendar':
                account=next(a for a in json.loads(args.credential_file.read_text())['users'] if a['level']==4)
                if account['user'] not in {u.name for u in app.access_users}:raise fixture.FixtureRefused('fixture account differs')
                run=CalendarRun(comm,app,account,evidence,args.output);run.calendar()
            else:evidence.update(verify_retention(comm,json.loads(args.before.read_text(encoding='utf-8')),args.output))
    except Exception as error:evidence.update(passed=False,error=f'{type(error).__name__}: {error}')
    with args.output.open('x',encoding='utf-8') as f:json.dump(evidence,f,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=evidence['passed'],rows=len(evidence['rows']),error=evidence.get('error'))))
    return 0 if evidence['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
