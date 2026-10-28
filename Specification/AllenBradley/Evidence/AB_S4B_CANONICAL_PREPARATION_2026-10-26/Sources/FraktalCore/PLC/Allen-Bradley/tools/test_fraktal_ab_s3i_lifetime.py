"""The bounded fixture drives real emitted calendar and publication ST offline."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fraktal_ab_access as access
import fraktal_ab_generate as gen
import fraktal_ab_line as line
import fraktal_ab_mailbox as mb
import fraktal_ab_s3i_equivalence as equivalence
import fraktal_ab_s3i_lifetime_execute as lifetime
import fraktal_ab_canonical_equivalence as comparison
import test_fraktal_ab_capture as capture_model
import test_fraktal_ab_line as scheduling
import test_fraktal_ab_s3i_line as publishing


class Model:
    """No wire mock supplies expected calendar/publication values.

    The inherited ST interpreters execute the actual owner and publisher. Only
    the mailbox transport, real-time wait and unrelated full-root surfaces are
    replaced. The retained comparison itself is tested separately below.
    """
    def __init__(self,destination,*,bad_target=False,missing_clock=False):
        self.pub=publishing.LineBehaviorTests();self.pub.setUp();self.app=self.pub.app
        self.schedule=scheduling.Schedule();self.plc=self.schedule.bench(self.app)
        self.when=datetime(2026,10,24,10,20,30,123000,tzinfo=timezone.utc)
        self.state=self.plc.tags[line.tag(self.app,'State')];self.shift=self.plc.tags[line.tag(self.app,'Shift')]
        # The legacy access-test builder retains its six-word V1 prefix. Add
        # the actual opt-in owner's V2 extension, preserving identity keys.
        for m in line.state_members(self.app):self.state.setdefault(m.name,m.initial)
        self.state['SchemaVersion']=line.state_schema(self.app)
        self.cfg=self.plc.tags[line.cfg(self.app).name+'Tag']
        self.cfg['SchemaVersion']=line.CALENDAR_SCHEMA
        self.session=self.plc.tags[access.tag(self.app,'State')]
        self.session.update(CurrentLevel=0,UserLength=0,UserBytes=[0]*32)
        self.plc.tags[gen.health_probe_tag(self.app)]['TimeIsSynchronized']=0
        self.pub.tags[line.tag(self.app,'State')]=self.state;self.pub.tags[line.tag(self.app,'Shift')]=self.shift
        self.evidence=dict(rows=[],serial=lifetime.SERIAL)
        self.run=lifetime.CalendarRun(object(),self.app,dict(user='echo_admin',pin='test-only',level=4),self.evidence,destination)
        self.bad_target,self.missing_clock=bad_target,missing_clock
        self.commands=[];self.last=None;self.tick(self.when)

    def tick(self,when):
        self.when=when;self.schedule.tick(self.plc,when,self.app);self.pub.scan()

    def unit(self):return self.plc.tags[f'FRK_{self.app.name}_Unit']

    def command(self,run,kind,**arguments):
        self.commands.append((kind,{k:v for k,v in arguments.items() if k!='Secret'}))
        if kind==mb.LOGIN:
            user=run.account['user'].encode();self.session.update(CurrentLevel=4,UserLength=len(user),UserBytes=list(user)+[0]*(32-len(user)))
        elif kind==mb.LOGOUT:self.session.update(CurrentLevel=0,UserLength=0,UserBytes=[0]*32)
        elif kind==mb.WRITE_CONFIG:
            answer=capture_model.execute(self.plc,self.app,Kind=kind,**arguments)
            if answer['Accepted']!=1:raise lifetime.fixture.FixtureRefused('model mailbox refused Line write')
            self.tick(self.when)
            if self.bad_target and arguments['BoolValue']==lifetime.TEMPORARY_TARGET:
                self.shift['ProductionTarget']=lifetime.TEMPORARY_TARGET
        elif kind!=mb.QUERY_CONFIG:raise AssertionError('unexpected command')
        return dict(sequence=len(self.commands),accepted=True)

    def wait(self,run,test,label,timeout=8):
        if test():return True
        if label=='natural calendar closure':
            plan=self.evidence['interval'];end=lifetime.parse_stamp(plan['end'])
            self.unit().update(GoodCount=17,ScrapCount=3,ReworkCount=2)
            self.plc.tags[gen.oee_tag(self.app)].update(RunS=1234,RunMs=345,DownS=234,DownMs=567,IdleS=42,IdleMs=789)
            self.tick(end+timedelta(milliseconds=10))
        if not test():raise lifetime.fixture.FixtureRefused(label+' model timeout')
        return True

    def observe(self,run,phase):
        run.command(mb.QUERY_CONFIG,IntValue=0,DurationMs=0);self.pub.scan()
        values={self.app.name+'/'+p:v for p,v in self.pub.actual().items()}
        if phase=='fresh_published_clock' and self.missing_clock:values[self.app.name+'/Line/LastUpdate']=0
        paths=equivalence.line_paths(self.app,canonical=False,count=self.shift['Count'])
        aliases=comparison.path_correspondences()
        declared={aliases.get(p,p):t for p,t in equivalence.logical_types(self.app,paths).items()}
        types={p:declared.get(p,'Boolean' if type(v) is bool else 'String' if type(v) is str else 'Float' if type(v) is float else 'Int32') for p,v in values.items()}
        self.last=dict(passed=True,synthetic=True,pair=dict(canonical=dict(values=values,types=types),
            legacyInputs=dict(additional=dict(line_shift=dict(Count=self.shift['Count'])))))
        return self.last

    def execute(self):
        with patch.object(lifetime.fixture.Run,'command',lambda run,kind,**args:self.command(run,kind,**args)), \
             patch.object(lifetime.fixture.Run,'wait',lambda run,test,label,timeout=8:self.wait(run,test,label,timeout)), \
             patch.object(lifetime.fixture.Run,'unit',lambda run:self.unit()), \
             patch.object(lifetime.CalendarRun,'read_config',lambda run:deepcopy(self.cfg)), \
             patch.object(lifetime.CalendarRun,'scalar',lambda run,name:self.pub.root[name]), \
             patch.object(lifetime.CalendarRun,'observe',lambda run,phase:self.observe(run,phase)), \
             patch.object(lifetime.fixture.Run,'restore_configuration',lambda run:None), \
             patch.object(lifetime.projection,'read_access',lambda comm:self.session):
            return self.run.calendar()


class LifetimeTests(unittest.TestCase):
    def test_public_stamp_planner_crosses_midnight_sunday_and_year(self):
        for text in ('2026-10-25T00:00:01.123Z','2026-12-31T23:59:59.999Z','1998-01-01T05:56:49.024Z'):
            plan=lifetime.interval(text);row=plan.values()
            self.assertEqual(plan.end.second,0);self.assertEqual(plan.end.microsecond,0)
            self.assertEqual(plan.end-plan.start,timedelta(hours=12))
            self.assertLess(plan.start,plan.observed);self.assertGreater(plan.end,plan.observed)
            self.assertEqual(row['ActiveDays1'],1<<plan.start.weekday())
            line.validate_calendar(0,((row['StartMin1'],row['DurationMin1'],row['ActiveDays1']),)+((-1,480,0),)*4)

    def test_missing_non_utc_and_unsupported_clock_ranges_refuse(self):
        for text in (0,'','2026-10-24T10:00:00+01:00','2026-02-30T10:00:00.000Z',
                     '1970-01-01T00:00:00.000Z','2099-12-31T23:59:59.000Z'):
            with self.subTest(text=text),self.assertRaises((ValueError,lifetime.fixture.FixtureRefused)):lifetime.interval(text)

    def test_complete_real_owner_and_publisher_lifetime(self):
        with tempfile.TemporaryDirectory() as folder:
            model=Model(Path(folder)/'calendar.json');original=deepcopy(model.cfg)
            self.assertTrue(model.execute(),model.evidence)
            self.assertEqual(model.cfg,original);self.assertEqual(model.session['CurrentLevel'],0)
            self.assertEqual(model.run.config_writes,38)
            self.assertEqual(len(model.evidence['rows']),7)
            self.assertEqual(model.shift['Count'],2)
            self.assertEqual(model.shift['HistoryIndex'][:2],[1,0])
            self.assertEqual(model.shift['HistoryProductionTarget'][0],40)
            self.assertEqual(model.shift['HistoryGood'][0],17)
            self.assertEqual(model.shift['HistoryNok'][0],3)
            self.assertEqual(model.shift['HistoryRework'][0],2)
            retained=model.evidence['retentionExpected']
            self.assertEqual(len(retained['values']),18+21*2)
            self.assertEqual(retained['types']['Press/ShiftHistory[1]/SchemaVersion'],'UInt16')
            self.assertEqual(retained['types']['Press/ShiftHistory[1]/Oee'],'Float')
            self.assertGreater(retained['values']['Press/ShiftHistory[1]/Oee'],0)

    def test_wrong_latched_target_fails_and_still_restores_configuration_and_session(self):
        with tempfile.TemporaryDirectory() as folder:
            model=Model(Path(folder)/'calendar.json',bad_target=True);original=deepcopy(model.cfg)
            self.assertFalse(model.execute())
            self.assertIn('running snapshot',model.evidence['error'])
            self.assertTrue(model.evidence['configurationRestored']);self.assertEqual(model.cfg,original)
            self.assertEqual(model.session['CurrentLevel'],0)
            self.assertLessEqual(model.run.config_writes,lifetime.MAX_CONFIG_WRITES)

    def test_missing_public_clock_never_falls_back_to_private_tags(self):
        with tempfile.TemporaryDirectory() as folder:
            model=Model(Path(folder)/'calendar.json',missing_clock=True);original=deepcopy(model.cfg)
            self.assertFalse(model.execute());self.assertIn('published',model.evidence['error'])
            self.assertEqual(model.cfg,original);self.assertEqual(model.session['CurrentLevel'],0)
            self.assertEqual(model.run.config_writes,1)

    def test_active_session_preflight_never_logs_it_out(self):
        with tempfile.TemporaryDirectory() as folder:
            model=Model(Path(folder)/'calendar.json');model.session['CurrentLevel']=4
            with self.assertRaisesRegex(lifetime.fixture.FixtureRefused,'another operator'):model.execute()
            self.assertEqual(model.commands,[]);self.assertEqual(model.session['CurrentLevel'],4)

    def test_partial_or_active_original_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            model=Model(Path(folder)/'calendar.json');original=deepcopy(model.cfg)
            missing=deepcopy(original);missing.pop('ProductionTarget5')
            active=deepcopy(original);active.update(StartMin1=0,ActiveDays1=127)
            for values in (missing,active,dict(original,SchemaVersion=2),dict(original,ProductionTarget1=-1)):
                with self.assertRaises((ValueError,lifetime.fixture.FixtureRefused)):lifetime.original_values(model.app,values)

    def test_write_guard_refuses_non_line_non_integer_and_excess_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            model=Model(Path(folder)/'calendar.json');actor=model.run
            actor.login_committed=True
            user=actor.account['user'].encode();model.session.update(CurrentLevel=4,UserLength=len(user),UserBytes=list(user)+[0]*(32-len(user)))
            with patch.object(actor,'check_idle'),patch.object(actor,'access',lambda:model.session),patch.object(lifetime.fixture.Run,'command') as write:
                ordinal=actor.caps['ProductionTarget1'][0]
                for kind,args in ((mb.START,{}),(mb.WRITE_CONFIG,dict(IntValue=-1,BoolValue=1)),
                    (mb.WRITE_CONFIG,dict(IntValue=ordinal,BoolValue=True)),(mb.WRITE_CONFIG,dict(IntValue=ordinal,BoolValue=-1)),
                    (mb.QUERY_CONFIG,dict(IntValue=1,DurationMs=0))):
                    with self.assertRaises(lifetime.fixture.FixtureRefused):actor.command(kind,**args)
                actor.config_writes=lifetime.MAX_CONFIG_WRITES
                with self.assertRaisesRegex(lifetime.fixture.FixtureRefused,'budget'):actor.write_value('ProductionTarget1',40)
                write.assert_not_called()

    def test_logout_refuses_an_unrelated_principal(self):
        with tempfile.TemporaryDirectory() as folder:
            model=Model(Path(folder)/'calendar.json');actor=model.run;actor.login_committed=True
            model.session.update(CurrentLevel=4,UserLength=5,UserBytes=list(b'other')+[0]*27)
            with patch.object(actor,'check_idle'),patch.object(actor,'access',lambda:model.session),patch.object(lifetime.fixture.Run,'command') as write:
                with self.assertRaisesRegex(lifetime.fixture.FixtureRefused,'unrelated'):actor.command(mb.LOGOUT)
                write.assert_not_called()

    def test_current_exact_image_authorization_is_required(self):
        good=dict(CurrentOwnerApproved=True,Serial=lifetime.SERIAL,CanonicalSha256=lifetime.ACD,
            CalendarLifetimeVectorsAuthorized=True,RetainedCycleAuthorized=True,FaultClearAuthorized=False,ClockSetAuthorized=False)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'approval.json'
            for field,value in (('CurrentOwnerApproved',False),('Serial','00000000'),('CanonicalSha256','wrong'),
                ('CalendarLifetimeVectorsAuthorized',False),('RetainedCycleAuthorized',False),('ClockSetAuthorized',True),('FaultClearAuthorized',True)):
                path.write_text(json.dumps(dict(good,**{field:value})))
                with self.assertRaises(lifetime.fixture.FixtureRefused):lifetime.authorize(path)
            path.write_text(json.dumps(good));self.assertEqual(lifetime.authorize(path),good)

    def test_pairs_are_read_on_an_independent_observer_not_the_mailbox_writer(self):
        # Every mailbox command leaves the writer at its 500-byte framing; the
        # first native lifetime capture failed by reading the frame through it.
        with tempfile.TemporaryDirectory() as folder:
            model=Model(Path(folder)/'calendar.json');actor=model.run
            writer=SimpleNamespace(IPAddress='127.0.0.1',ProcessorSlot=0,ConnectionSize=500);actor.comm=writer
            used=[]
            class Observer:
                def __init__(self,address):used.append(address)
                def __enter__(self):return self
                def __exit__(self,*unused):return False
            def gate(comm):
                used.append((comm is writer,comm.ConnectionSize));return dict(passed=True)
            with patch.object(actor,'command') as command,patch('pylogix.PLC',Observer),patch.object(lifetime.equivalence,'run',gate):
                report=actor.observe('original_empty_profile')
            command.assert_called_once_with(mb.QUERY_CONFIG,IntValue=0,DurationMs=0)
            self.assertEqual(used,['127.0.0.1',(False,4000)])
            self.assertEqual(report['fixtureObserver'],dict(independent=True,writerConnectionBytes=500,readConnectionBytes=4000))
            self.assertEqual(model.evidence['s3iLifetimePairs'][0]['phase'],'original_empty_profile')

    def test_retention_compares_all_line_values_and_types_without_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            model=Model(Path(folder)/'calendar.json');self.assertTrue(model.execute())
            expected=model.evidence;report=deepcopy(model.last);app=model.app
            with patch.object(lifetime.station,'application',lambda:app),patch.object(lifetime.px,'read_unit',lambda comm:model.unit()), \
                patch.object(lifetime.projection,'read_access',lambda comm:model.session), \
                patch.object(lifetime,'image_guard',lambda comm:dict(passed=True,cases=8)), \
                patch.object(lifetime.equivalence,'run',lambda comm:report):
                result=lifetime.verify_retention(object(),expected,Path(folder)/'retained.json')
                self.assertTrue(result['passed']);self.assertEqual(result['controllerWrites'],0)
                for index,section in enumerate(('values','types')):
                    changed=deepcopy(report)
                    changed['pair']['canonical'][section]['Press/ShiftHistory[1]/ProductionTarget']=99 if section=='values' else 'Int32'
                    with patch.object(lifetime.equivalence,'run',lambda comm:changed):
                        with self.assertRaisesRegex(lifetime.fixture.FixtureRefused,'retained Line'):
                            lifetime.verify_retention(object(),expected,Path(folder)/f'bad_{index}.json')


if __name__=='__main__':unittest.main()
