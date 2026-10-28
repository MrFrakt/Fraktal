import os
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import fraktal_ab_alarm_observer as probe
import fraktal_ab_alarm_observe as collector
import fraktal_ab_native_observer as timing
import fraktal_ab_observer_fixture as fixture
import fraktal_ab_readback as readback
import fraktal_ab_tower_demo as tower
from test_fraktal_ab_generate import emit_seed, SEED_38


def record():
    value = dict.fromkeys(probe.HEADER,0)
    value.update(SchemaVersion=1,Signature=probe.SIGNATURE,Revision=4,Scans=12000,
                 Phase=len(probe.PHASES)-1,Done=1,Started=1,RunStartCst=123456789,PhaseStartCst=223456789)
    value['Rows'] = []
    for name,seconds in probe.PHASES:
        row = dict.fromkeys(probe.ROW,0)
        row.update(Name=name,Samples=seconds*100,ElapsedUs=seconds*1000000,Complete=1)
        for prefix in ('Tba','Almd'):
            flags = {'sustained':3,'latched_active':33,'ack_live':3,'reset_live':3,
                     'latched_gone':3,'suppressed':7,'unsuppressed':3,
                     'operator_shelve':11,'shelf_expiry':3}.get(name,2)
            row[prefix+'Flags'] = flags
            row[prefix+'SeenFlags'] = flags | (8 if name=='shelf_expiry' else 0)
            row[prefix+'Count'] = int(name!='baseline')
        value['Rows'].append(row)
    return value


def packed(value):
    return struct.pack(probe.FORMAT,*(value[name] for name in probe.HEADER),
        *(row[name] for row in value['Rows'] for name in probe.ROW),
        *(value[name] for name in probe.LINTS))


class AlarmObserverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, base, _ = emit_seed(tower.application(),SEED_38)
        cls.base = timing.augment(base,tower.application())

    def test_original_code_initializers_tasks_and_manifest_are_preserved(self):
        first = ET.fromstring(self.base)
        changed = ET.fromstring(probe.augment(self.base,tower.application()))
        a,b = readback.executable(first),readback.executable(changed)
        program = first.find('Controller/Programs/Program')
        main = program.get('Name'),program.get('MainRoutineName')
        self.assertEqual(b.pop((main[0],probe.ROUTINE)),readback.normalized('\n'.join(probe.logic())))
        self.assertEqual(b[main],a[main]+readback.normalized(f'JSR({probe.ROUTINE},0);'))
        b[main] = a[main]
        self.assertEqual(a,b)
        old,new = readback.initials(first),readback.initials(changed)
        self.assertTrue(all(new.get(k)==v for k,v in old.items()))
        self.assertEqual(ET.tostring(first.find('Controller/Tasks')),ET.tostring(changed.find('Controller/Tasks')))
        self.assertNotIn('SSV(', '\n'.join(probe.logic()))
        added = {t.get('Name'):t.get('ExternalAccess') for t in changed.findall('Controller/Tags/Tag')
                 if t.get('Name') not in {n.get('Name') for n in first.findall('Controller/Tags/Tag')}}
        self.assertEqual({k:v for k,v in added.items() if v!='Read Only'}, {probe.alarms.ALMD:'Read/Write'})

    def test_duplicate_missing_timing_physical_io_and_multi_program_are_refused(self):
        app = tower.application()
        with self.assertRaisesRegex(ValueError,'already present'):
            probe.augment(probe.augment(self.base,app),app)
        for old,new in ((f'Name="{timing.TAG}"','Name="Missing"'),
                        ('</Modules>','<Module Name="External"/></Modules>'),
                        ('</Programs>','<Program Name="Other"/></Programs>')):
            with self.subTest(old=old),self.assertRaises(ValueError):
                probe.augment(self.base.replace(old,new),app)

    def test_binary_layout_and_schema_incomplete_publications_are_checked(self):
        self.assertEqual(probe.BYTES,880)
        value = record()
        decoded = probe.decode(packed(value))
        self.assertEqual(decoded['Rows'],value['Rows'])
        self.assertEqual(decoded['RunStartCst'],value['RunStartCst'])
        for changes in ({'Revision':3},{'Revision':0},{'Signature':0},{'SchemaVersion':2},
                        {'Phase':-1},{'Phase':len(probe.PHASES)},{'Done':2}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                probe.decode(packed(dict(value,**changes)))
        for raw in (b'',b'\0'*(probe.BYTES-1),'not bytes'):
            with self.assertRaises(ValueError): probe.decode(raw)

    def test_completed_record_still_cannot_claim_runtime_projection_or_security(self):
        result = probe.assess(record())
        self.assertTrue(result['Completed'])
        self.assertTrue(all(result['Checks'].values()))
        self.assertFalse(result['RuntimeProjectionAccepted'])
        self.assertFalse(result['OperatorIsolationQualified'])
        self.assertTrue(result['CoreRegressionsRequired'])

    def test_partial_and_short_observations_are_never_completed(self):
        for mutate in (lambda n:n.update(Done=0),lambda n:n.update(ProbeFault=1),
                       lambda n:n['Rows'][0].update(Complete=0),
                       lambda n:n['Rows'][-2].update(ElapsedUs=1)):
            value=record()
            mutate(value)
            self.assertFalse(probe.assess(value)['Completed'])
        with self.assertRaises(ValueError): probe.assess(dict(record(),Rows=[]))

    def test_ack_does_not_clear_latch_and_transient_status_faults_survive(self):
        value = record()
        value['Rows'][probe.INDEX['ack_live']]['TbaFlags'] = 2
        self.assertFalse(probe.assess(value)['Checks']['TbaAckKeepsLatch'])
        value = record()
        value['Rows'][1]['AlmdSeenStatus'] = 1
        self.assertFalse(probe.assess(value)['Checks']['AlmdNoNativeStatusFault'])
        value = record()
        value['Rows'][probe.INDEX['latched_gone']]['TbaFlags'] = 2
        self.assertFalse(probe.assess(value)['Checks']['TbaLatchSurvivesGone'])

    def test_shelving_and_short_pulse_are_discriminators_and_not_assumed_successful(self):
        value = record()
        for row in value['Rows']:
            row['TbaCount'] = 0
            row['TbaSeenFlags'] &= ~8
        result = probe.assess(value)
        self.assertEqual(result['ShortPulseCountDelta']['Tba'],0)
        self.assertFalse(result['OperatorShelveObserved']['Tba'])
        self.assertFalse(result['ShelfExpiryObserved']['Tba'])
        self.assertFalse(result['RuntimeProjectionAccepted'])

    def test_read_only_collector_keeps_controller_faults_and_refuses_restarts(self):
        class Comm:
            guards=0
            def guard(self): self.guards += 1
            def Write(self,*args): raise AssertionError('observer cannot write')
        class Clock:
            now=0
            def read(self): return self.now
            def sleep(self,amount): self.now += amount
        value = record()
        partial = dict(value,Done=0)
        with patch.object(timing,'sample',side_effect=[dict(MajorFaultBits=1,MinorFaultBits=0),dict(MajorFaultBits=0,MinorFaultBits=0)]),patch.object(probe,'sample',side_effect=[partial,value]):
            comm,clock = Comm(),Clock()
            result=collector.collect(comm,5,monotonic=clock.read,sleep=clock.sleep)
            self.assertFalse(result['FaultFree'])
            self.assertFalse(result['BaseComparisonPassed'])
            self.assertEqual(comm.guards,2)
            self.assertEqual(result['ControllerWrites'],0)
        with patch.object(timing,'sample',return_value=dict(MajorFaultBits=0,MinorFaultBits=0)),patch.object(probe,'sample',side_effect=[partial,dict(value,RunStartCst=1)]):
            clock=Clock()
            with self.assertRaisesRegex(ValueError,'restarted'):
                collector.collect(Comm(),5,monotonic=clock.read,sleep=clock.sleep)

    def test_wrong_declaration_serial_and_existing_evidence_fail_before_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'evidence.json'
            args=['--expect-serial','601FC87B','--output',str(output)]
            with patch.dict(os.environ,{'FRAKTAL_AB_DECLARATION':'wrong'}),self.assertRaises(SystemExit):
                collector.main(args)
            with patch.dict(os.environ,{'FRAKTAL_AB_DECLARATION':'fraktal_ab_tower_demo'}):
                with self.assertRaises(SystemExit): collector.main(['--expect-serial','1','--output',str(output)])
                output.write_text('keep')
                with self.assertRaises(SystemExit): collector.main(args)
                self.assertEqual(output.read_text(),'keep')


if __name__ == '__main__':
    unittest.main()
