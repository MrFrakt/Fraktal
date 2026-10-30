import struct
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import fraktal_ab_native_observer as probe
import fraktal_ab_native_observe as collector
import fraktal_ab_readback as readback
import fraktal_ab_tower_demo as tower
from test_fraktal_ab_generate import emit_seed, SEED_38


def record(**changes):
    values = dict.fromkeys(probe.FIELDS, 0)
    values.update(SchemaVersion=1, Signature=probe.SIGNATURE, Revision=4,
                  Samples=2, TaskRateUs=10000,
                  Cst=2**50, Wall=2**55, Start=2**55-100,
                  MaxIntervalLow=-1, MaxIntervalHigh=1,
                  MinIntervalLow=10000)
    values.update(changes)
    return values


def packed(value):
    return struct.pack(probe.FORMAT, *(value[name] for name in probe.FIELDS))


class Connection:
    def __init__(self, replies):
        self.replies = iter(replies)

    def Read(self, tag):
        value = next(self.replies)
        return SimpleNamespace(Status='Success', Value=value)

    def Write(self, *args):
        raise AssertionError('the observer must never write')


class NativeObserverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.base, _ = emit_seed(tower.application(), SEED_38)

    def test_instrumentation_preserves_every_original_body_initializer_and_task(self):
        changed = ET.fromstring(probe.augment(self.base, tower.application()))
        before, after = readback.executable(self.root), readback.executable(changed)
        main = self.root.find('Controller/Programs/Program')
        key = (main.get('Name'),main.get('MainRoutineName'))
        self.assertEqual(after.pop((key[0],probe.ROUTINE)),
                         readback.normalized('\n'.join(probe.logic(tower.application()))))
        self.assertEqual(after[key],before[key]+readback.normalized(f'JSR({probe.ROUTINE},0);'))
        after[key] = before[key]
        self.assertEqual(before,after)
        self.assertEqual(readback.initials(self.root),readback.initials(changed))
        self.assertEqual(ET.tostring(self.root.find('Controller/Tasks')),
                         ET.tostring(changed.find('Controller/Tasks')))
        record_type = changed.find(f"Controller/DataTypes/DataType[@Name='{probe.TYPE}']")
        for member in record_type.findall('Members/Member'):
            self.assertEqual(member.get('ExternalAccess'),'Read Only')
        self.assertEqual(changed.find(f"Controller/Tags/Tag[@Name='{probe.TAG}']").get('ExternalAccess'),'Read Only')
        self.assertNotIn('SSV(', '\n'.join(probe.logic(tower.application())))

    def test_family_physical_modules_changed_task_and_duplicate_are_refused(self):
        for old,new in (('ProcessorType="1756-L81E"','ProcessorType="5069-L310ER"'),
                        ('MajorRev="38"','MajorRev="33"'),
                        ('DisableUpdateOutputs="true"','DisableUpdateOutputs="false"'),
                        ('InhibitTask="false"','InhibitTask="true"'),
                        ('Rate="10"','Rate="20"'),
                        ('</Modules>','<Module Name="External"/></Modules>')):
            with self.subTest(new=new), self.assertRaises(ValueError):
                probe.augment(self.base.replace(old,new),tower.application())
        with self.assertRaisesRegex(ValueError,'already present'):
            probe.augment(probe.augment(self.base,tower.application()),tower.application())

    def test_exact_width_and_full_native_integer_values(self):
        self.assertEqual(probe.BYTES, 216)
        value = probe.decode(packed(record()))
        self.assertEqual(value['Cst'], 2**50)
        self.assertEqual(value['Wall'], 2**55)
        self.assertEqual(value['MaxIntervalUs'], 2**33-1)
        self.assertEqual(value['MinIntervalUs'], 10000)

    def test_schema_short_odd_uninitialized_and_wrong_task_refused(self):
        for changes in ({'Signature':0}, {'SchemaVersion':2}, {'Revision':3},
                        {'Revision':0}, {'Samples':1}, {'TaskRateUs':20000}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                probe.decode(packed(record(**changes)))
        for raw in (b'', bytes(probe.BYTES-1), bytes(probe.BYTES+1), 'bad'):
            with self.assertRaises(ValueError):
                probe.decode(raw)

    def test_torn_publication_is_retried(self):
        comm = Connection([2, packed(record()), 4, 4, packed(record()), 4])
        self.assertEqual(probe.sample(comm)['Revision'], 4)

    def test_odd_and_continuously_changing_publication_never_escape(self):
        for raw in (packed(record(Revision=3)), packed(record())):
            with self.assertRaisesRegex(ValueError, 'coherent'):
                probe.sample(Connection([2, raw, 6] * 2), attempts=2)

    def test_failed_transport_cannot_be_read_as_healthy(self):
        comm = Connection([])
        comm.Read = lambda _: SimpleNamespace(Status='timeout', Value=None)
        with self.assertRaisesRegex(ValueError, 'acquisition'):
            probe.sample(comm)

    def test_negative_clock_jump_preserved_without_minute_repair(self):
        first, last = record(), record(Samples=102, Revision=204)
        last.update(Cst=first['Cst']+1_000_000, Wall=first['Wall']-5_000_000,
                    Start=first['Start']-5_000_000, NegativeWall=1, NegativeStart=1)
        report = probe.assess(first, last, 2)
        self.assertEqual(report['MicrosecondsPerScan']['Cst'], 10000)
        self.assertEqual(report['ClockDeltaUs']['Wall'], -5_000_000)
        self.assertEqual(report['NegativeDeltas']['Start'], 1)
        self.assertEqual(report['SimulatedToHostRatio']['Cst'], .5)
        for key in ('ProductionReplacementAccepted', 'ClockAdjustmentQualified',
                    'EchoScalingChangesQualified', 'ExternalIoQualified'):
            self.assertIs(report[key], False)

    def test_restarts_saturation_and_faults_do_not_produce_clean_acceptance(self):
        first = record()
        for last in (record(), record(Samples=10,Revision=2), record(Samples=2_000_000_000),
                     record(Samples=10, FirstCst=1)):
            with self.assertRaises(ValueError):
                probe.assess(first, last, 1)
        last = record(Samples=3,Revision=6, MajorFaultBits=4)
        self.assertIs(probe.assess(first, last, 1)['FaultFree'], False)

    def test_collector_reads_only_and_checks_identity_every_sample(self):
        class Clock:
            now = 0
            def read(self): return self.now
            def sleep(self, amount): self.now += amount
        class Comm:
            checks = 0
            reads = 0
            fault_reads = ()
            def guard(self): self.checks += 1
            def Read(self, tag):
                if tag == probe.TAG:
                    self.reads += 1
                    return SimpleNamespace(Status='Success', Value=packed(record(
                        Samples=self.reads+1, Revision=self.checks*2,
                        MajorFaultBits=int(self.reads in self.fault_reads),
                        Cst=2**50+self.reads*500000)))
                return SimpleNamespace(Status='Success', Value=self.checks*2)
            def Write(self, *args): raise AssertionError('unexpected write')
        clock, comm = Clock(), Comm()
        report = collector.collect(comm, 5, monotonic=clock.read, sleep=clock.sleep)
        self.assertEqual(report['ControllerWrites'],0)
        self.assertEqual(comm.reads,comm.checks)
        self.assertEqual(report['observations']['ClockDeltaUs']['Cst'],5_000_000)
        self.assertEqual(report['observations']['HostSeconds'],5)
        clock, comm = Clock(), Comm()
        comm.fault_reads = (4,)
        report = collector.collect(comm,5,monotonic=clock.read,sleep=clock.sleep)
        self.assertEqual(report['rows'][-1]['values']['MajorFaultBits'],0)
        self.assertIs(report['observations']['FaultFree'],False)

    def test_collector_refuses_wrong_declaration_target_and_preexisting_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'evidence.json'
            arguments = ['--expect-serial','601FC87B','--output',str(output)]
            with patch.dict(os.environ, {'FRAKTAL_AB_DECLARATION':'fraktal_ab_press_demo'}):
                with self.assertRaises(SystemExit) as refusal:
                    collector.main(arguments)
                self.assertEqual(refusal.exception.code,2)
            with patch.dict(os.environ, {'FRAKTAL_AB_DECLARATION':'fraktal_ab_tower_demo'}):
                with self.assertRaises(SystemExit):
                    collector.main(['--expect-serial','1234','--output',str(output)])
                self.assertFalse(output.exists())
                output.write_text('preserve',encoding='utf-8')
                with self.assertRaises(SystemExit):
                    collector.main(arguments)
                self.assertEqual(output.read_text(encoding='utf-8'),'preserve')


if __name__ == '__main__':
    unittest.main()
