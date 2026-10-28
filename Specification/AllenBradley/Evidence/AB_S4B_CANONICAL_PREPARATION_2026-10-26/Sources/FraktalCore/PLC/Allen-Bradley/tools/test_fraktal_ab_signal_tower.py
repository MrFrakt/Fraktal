from dataclasses import replace
import itertools
import re
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import fraktal_ab_access as access
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_machine_state as machine
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as manifest
import fraktal_ab_projection as projection
import fraktal_ab_signal_tower as tower
import fraktal_ab_sets as sets
import fraktal_ab_st_model as st
import test_fraktal_ab_access as auth

APP = replace(auth.APP, signal_tower=tower.SignalTower())


class Tc3Controller(st.Controller):
    """Preserve the oracle's BOOL storage; the Logix model stores public DINTs."""
    def write(self, ref, value):
        holder,key = self._container(ref)
        if isinstance(holder[key],bool):
            holder[key] = bool(value)
        else:
            super().write(ref,value)


class Bench:
    def __init__(self, app=APP):
        self.app, self.now, self.started = app, 0, 0
        self.plc = st.Controller({f'FRK_{app.name}_Unit':st.structure(gen.unit_context_members(app)),
            gen.alarm_active_tag(app):st.structure(gen.alarm_active_members()),
            **{tower.tag(app,s):st.structure(r.members) for s,r in zip(('', 'Cfg', 'Book'),tower.records(app))},
            tower.tag(app,'Timer'):dict(PRE=0,Reset=0,TimerEnable=0,DN=0)}, calls={'TONR':self.timer})
        self.body = st.parse('\n'.join(tower.logic(app)))

    def timer(self, plc, args):
        timer = plc.read(args[0])
        if timer['Reset'] or not timer['TimerEnable']:
            self.started = self.now
            timer['DN'] = False
        else:
            timer['DN'] = self.now-self.started >= timer['PRE']

    @property
    def unit(self):
        return self.plc.tags[f'FRK_{self.app.name}_Unit']

    @property
    def status(self):
        return self.plc.tags[tower.tag(self.app)]

    def scan(self):
        self.plc.run(self.body)


def tc3_mapping():
    from test_fraktal_ab_core_ordinals import core_enum
    path = Path(__file__).resolve().parents[2]/'TwinCAT/Framework/Fraktal_Core/BaseClasses/FB_SignalTower.TcPOU'
    body = ET.parse(path).find('.//Method[@Name="Cyclic"]/Implementation/ST').text
    body = body[body.index('Status.Red := FALSE;'):body.index('Cyclic := TRUE;')]
    for enum in ('E_MachineState','E_Severity'):
        for name,value in core_enum(enum).items():
            body = body.replace(enum+'.'+name,str(value))
    body = re.sub(r'//[^\n]*','',body)
    body = re.sub(r'\bEND_(IF|CASE)\b(?!\s*;)',r'END_\1;',body)
    return st.parse(body)


class SignalTowerPolicy(unittest.TestCase):
    def test_semantics_match_the_actual_tc3_mapper(self):
        oracle = tc3_mapping()
        units = (dict(),dict(Running=1),dict(Error=1),dict(Aborted=1),dict(Mode=3),
                 dict(Running=1,Error=1),dict(Running=1,Aborted=1))
        for unit, severity, shelved, decision, white, horn in itertools.product(
                units,(-1,0,1,2,9),(0,1),(0,1),(False,True),(False,True)):
            bench = Bench(replace(APP,signal_tower=tower.SignalTower(operator_uses_white=white,horn_on_high=horn)))
            bench.unit.update(unit,DecisionId=decision)
            alarm = bench.plc.tags[gen.alarm_active_tag(APP)]
            alarm['ActState'][0],alarm['ActSeverity'][0],alarm['ActShelved'][0] = 1,severity,shelved
            bench.scan()
            model = Tc3Controller(dict(Status={n:False for n in tower.OUTPUTS},_testActive=False,
                TRUE=True,FALSE=False,
                MachineState=bench.status['MachineState'],AlarmActive=not shelved,
                HighestSeverity=max(0,severity),OperatorActionRequired=bool(decision),
                ParCfg=dict(OperatorUsesWhite=white,HornOnHigh=horn),
                E_MachineState=machine.STATES,E_Severity=dict(HIGH=2,MED=1,LOW=0)))
            model.run(oracle)
            self.assertEqual({n:bench.status[n] for n in tower.OUTPUTS},model.tags['Status'])

    def test_classifier_has_the_same_priority_in_gateway_and_controller(self):
        from test_fraktal_ab_core_ordinals import core_enum
        self.assertEqual(machine.STATES,core_enum('E_MachineState'))
        for kind in ('WAIT_UPSTREAM','WAIT_DOWNSTREAM'):
            first = APP.chains[0]
            step = replace(first.steps[0],time_class=kind)
            app = replace(APP,chains=(replace(first,steps=(step,*first.steps[1:])),*APP.chains[1:]))
            bench = Bench(app)
            for error,blocking,running,aborted in itertools.product((0,1),repeat=4):
                bench.unit.update(Mode=first.mode_ordinal,Step=step.number,Error=error,Running=running,Aborted=aborted)
                alarm = bench.plc.tags[gen.alarm_active_tag(app)]
                alarm['Blocking'] = blocking
                bench.scan()
                self.assertEqual(bench.status['MachineState'],projection.machine_state(app,bench.unit,alarm)['MachineState'])

    def test_native_timer_boundary_and_clamp_without_client_or_scan_counter(self):
        for requested,duration in ((3000,3000),(0,3000),(-1,3000),(30001,30000),(1,1)):
            bench = Bench(replace(APP,signal_tower=tower.SignalTower(requested)))
            bench.plc.tags[tower.tag(APP,'Book')]['Request'] = 1
            bench.scan()
            self.assertTrue(all(bench.status[n] for n in tower.OUTPUTS))
            bench.now = duration-1
            bench.scan()
            self.assertTrue(bench.status['TestActive'])
            bench.now = duration
            bench.scan()
            self.assertFalse(any(bench.status[n] for n in tower.OUTPUTS))
            self.assertEqual(bench.plc.tags[tower.tag(APP,'Book')]['Request'],0)

    def test_shelving_does_not_suppress_machine_down(self):
        bench = Bench()
        alarm = bench.plc.tags[gen.alarm_active_tag(APP)]
        alarm['Blocking'],alarm['ActState'][0],alarm['ActSeverity'][0],alarm['ActShelved'][0] = 1,1,2,1
        bench.scan()
        self.assertEqual((bench.status['Red'],bench.status['Horn'],bench.status['MachineState']),(1,0,4))


class SignalTowerContract(unittest.TestCase):
    def test_adding_runtime_tower_preserves_exact_prior_document_revision_only(self):
        import fraktal_ab_tower_demo as fixture
        app = fixture.application()
        prior = replace(app,signal_tower=None)
        plc = st.Controller(dict(Revision=manifest.config_revision(prior),Rejected=0))
        check = 'Rejected := '+sets.revision_rejected(app,'Revision')+';'
        plc.run(check)
        self.assertEqual(plc.tags['Rejected'],0)
        plc.tags['Revision'] = manifest.config_revision(app)
        plc.run(check)
        self.assertEqual(plc.tags['Rejected'],0)
        plc.tags['Revision'] = 0
        plc.run(check)
        self.assertEqual(plc.tags['Rejected'],1)

    def test_manual_gate_and_busy_or_duplicate_refusal_use_normal_acknowledged_mailbox(self):
        c = auth.controller(APP)
        bench = Bench()
        c.tags.update({k:v for k,v in bench.plc.tags.items() if 'SignalTower' in k})
        state = c.tags[access.tag(APP,'State')]
        state['Required'][2],state['Required'][10] = 1,4
        state['CurrentLevel'] = 0
        answer = auth.request(c,mb.LAMP_TEST,APP)
        self.assertEqual((answer['Accepted'],answer['DiagnosticKey']),(0,manifest.numeric_key(APP,access.DENIED)))
        state['CurrentLevel'] = 1
        answer = auth.request(c,mb.LAMP_TEST,APP)
        self.assertEqual((answer['Accepted'],answer['AckSequence']),(1,c.tags[mb.request_tag_name(APP)]['Sequence']))
        self.assertEqual(c.tags[tower.tag(APP,'Book')]['Request'],1)
        c.tags[tower.tag(APP,'Book')]['Request'] = 0
        for busy,test in ((1,0),(0,1)):
            c.tags['FRK_Press_Unit']['Running'] = busy
            c.tags[tower.tag(APP)]['TestActive'] = test
            answer = auth.request(c,mb.LAMP_TEST,APP)
            self.assertEqual(answer['Accepted'],0)
            self.assertEqual(c.tags[tower.tag(APP,'Book')]['Request'],0)

    def test_only_declared_read_only_semantics_are_published(self):
        self.assertEqual(decl.validate(APP),[])
        self.assertNotIn(mb.LAMP_TEST,mb.refused_for(APP))
        absent = replace(APP,signal_tower=None)
        self.assertIn(mb.LAMP_TEST,mb.refused_for(absent))
        self.assertNotIn('TONR(', '\n'.join(gen.routine_logic(absent)))
        tags = ET.fromstring(gen.controller_tags(APP))
        for suffix in ('','Cfg','Book','Timer'):
            self.assertEqual(tags.find(f"Tag[@Name='{tower.tag(APP,suffix)}']").get('ExternalAccess'),
                             'Read Only' if suffix=='' else 'None')
        self.assertIn(tower.tag(APP),gen.publishable_tags(APP))
        self.assertNotIn(tower.tag(APP),gen.externally_writable(APP))
        config = replace(APP,signal_tower=tower.SignalTower(5000))
        self.assertNotEqual(manifest.content_hash(APP),manifest.content_hash(config))
        fields = [f for f in manifest.content(APP)['Fields'] if f['PathKey'] in {
            manifest.numeric_key(APP,'SignalTower.'+n) for n in tower.OUTPUTS}]
        self.assertEqual(len(fields),7)
        self.assertTrue(all(f['AccessClass']==manifest.ACCESS_READ and f['ReadTier']==manifest.TIER_LIVE for f in fields))
        sections = [n for n,_ in gen.scan_sections(APP)]
        self.assertGreater(sections.index('FRK_Press_ScanSignalTower'),sections.index('FRK_Press_ScanDiagnostics'))

    def test_malformed_convention_or_snapshot_refuses(self):
        for cfg in (object(),tower.SignalTower(True),tower.SignalTower(operator_uses_white=1)):
            self.assertTrue(decl.validate(replace(APP,signal_tower=cfg)))
        self.assertTrue(decl.validate(replace(APP,access_users=None)))
        for raw in (None,{},dict(SchemaVersion=99),{**st.structure(tower.members()),'Red':9}):
            with self.assertRaises(ValueError):
                tower.project(raw)

    def test_generic_projection_uses_the_native_machine_state_and_requires_the_facet(self):
        import test_fraktal_ab_projection as helpers
        with patch.object(projection,'APP',APP),patch.object(helpers,'APP',APP):
            args = (helpers.good_header(),manifest.content(APP),helpers.unit_values(),helpers.contexts())
            raw = st.structure(tower.members())
            raw.update(MachineState=4,Red=1)
            doc = projection.project(*args,tower_state=raw)
            self.assertTrue(doc['values']['Press/SignalTower/Red'])
            self.assertEqual(doc['values']['Press/MachineState'],4)
            with self.assertRaises(projection.ReadFailed):
                projection.project(*args)


if __name__ == '__main__':
    unittest.main()
