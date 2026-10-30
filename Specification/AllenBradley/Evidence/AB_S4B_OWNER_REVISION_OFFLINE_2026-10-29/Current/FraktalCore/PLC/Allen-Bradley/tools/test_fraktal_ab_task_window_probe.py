import struct
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_observer_fixture as fixture
import fraktal_ab_readback as readback
import fraktal_ab_resource_demo as resource
import fraktal_ab_st_model as st
import fraktal_ab_task_window_probe as probe
from test_fraktal_ab_generate import emit_seed, SEED_38


def record(**changes):
    result = dict.fromkeys(probe.FIELDS, 0)
    result.update(SchemaVersion=1, Signature=probe.SIGNATURE, Revision=804,
                  Samples=401, TaskRateUs=10000, Window=4, WindowScans=100,
                  Done=1, ResetCount=4)
    for index in range(4):
        result[f'ResetMin{index}'] = probe.SENTINEL if index % 2 else 0
        result[f'WindowMax{index}'] = 10001
        result[f'WindowMin{index}'] = 9999 if index % 2 else 0
    result.update(changes)
    return result


def packed(value):
    return struct.pack(probe.FORMAT, *(value[name] for name in probe.FIELDS))


class TaskWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.base, _ = emit_seed(resource.application(), SEED_38)

    def test_all_original_code_values_task_settings_and_alarm_metadata_preserved(self):
        changed = ET.fromstring(probe.augment(self.base, resource.application()))
        before, after = readback.executable(self.root), readback.executable(changed)
        program = self.root.find('Controller/Programs/Program')
        main = (program.get('Name'), program.get('MainRoutineName'))
        self.assertEqual(after.pop((main[0], probe.ROUTINE)),
                         readback.normalized('\n'.join(probe.logic(resource.application()))))
        self.assertEqual(after[main], before[main] + readback.normalized(f'JSR({probe.ROUTINE},0);'))
        after[main] = before[main]
        self.assertEqual(before, after)
        self.assertEqual(readback.initials(self.root), readback.initials(changed))
        self.assertEqual(readback.alarm_metadata(self.root), readback.alarm_metadata(changed))
        self.assertEqual(ET.tostring(self.root.find('Controller/Tasks')),
                         ET.tostring(changed.find('Controller/Tasks')))

    def test_only_two_task_statistic_attributes_are_writable(self):
        code = probe.logic(resource.application())
        writes = [line for line in code if line.startswith('SSV(')]
        task = resource.application().task_name
        self.assertEqual(writes, [f'SSV(TASK,{task},MaxInterval,{probe.TAG}.SeedMaxWords[0]);',
                                  f'SSV(TASK,{task},MinInterval,{probe.TAG}.SeedMinWords[0]);'])
        changed = ET.fromstring(probe.augment(self.base, resource.application()))
        data = changed.find(f"Controller/DataTypes/DataType[@Name='{probe.TYPE}']")
        self.assertTrue(all(m.get('ExternalAccess') == 'Read Only' for m in data.findall('Members/Member')))
        self.assertEqual(changed.find(f"Controller/Tags/Tag[@Name='{probe.TAG}']").get('ExternalAccess'), 'Read Only')

    def test_wrong_target_task_external_io_and_duplicate_refused(self):
        for old, new in (('ProcessorType="1756-L81E"', 'ProcessorType="5069-L310ER"'),
                         ('MajorRev="38"', 'MajorRev="33"'),
                         ('Rate="10"', 'Rate="20"'),
                         ('DisableUpdateOutputs="true"', 'DisableUpdateOutputs="false"'),
                         ('</Modules>', '<Module Name="External"/></Modules>')):
            with self.subTest(new=new), self.assertRaises(ValueError):
                probe.augment(self.base.replace(old, new), resource.application())
        with self.assertRaisesRegex(ValueError, 'already present'):
            probe.augment(probe.augment(self.base, resource.application()), resource.application())

    def test_width_alignment_and_sentinel_preserve_all_64_bits(self):
        self.assertEqual(len(probe.DINTS) * 4 % 8, 0)
        self.assertEqual(probe.BYTES, 224)
        result = probe.decode(packed(record()))
        self.assertEqual(result['ResetMin1'], probe.SENTINEL)
        self.assertEqual(result['ResetMin3'], probe.SENTINEL)

    def test_malformed_partial_wrong_task_and_progress_refused(self):
        for changes in ({'SchemaVersion': 0}, {'Signature': 0}, {'Revision': 3},
                        {'Revision': 0}, {'TaskRateUs': 20000}, {'Samples': 402},
                        {'Window': 5}, {'WindowScans': 101}, {'Done': 2},
                        {'ResetCount': 5}, {'Window': 3}, {'Samples': 400}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                probe.decode(packed(record(**changes)))
        for raw in ('bad', b'', bytes(probe.BYTES - 1), bytes(probe.BYTES + 1)):
            with self.assertRaises(ValueError):
                probe.decode(raw)

    def test_assessment_never_hides_zero_minimum_or_bad_reset(self):
        result = probe.assess(record())
        self.assertTrue(result['WindowResetObserved'])
        self.assertEqual([row['positiveOrderedInterval'] for row in result['windows']],
                         [False, True, False, True])
        self.assertFalse(probe.assess(record(ResetMin3=0))['WindowResetObserved'])
        self.assertFalse(probe.assess(record(WindowMin1=10002))['windows'][1]['positiveOrderedInterval'])
        self.assertTrue(probe.assess(record(FaultSeen=1))['faultsObserved'])
        self.assertTrue(probe.assess(record(OverlapCount=1))['overlapChanged'])
        self.assertTrue(result['TaskWideStatisticsOwnershipRequired'])
        for name in ('ProductionReplacementAccepted', 'ClockAdjustmentQualified',
                     'MissedScansQualified', 'EchoScalingChangesQualified'):
            self.assertIs(result[name], False)
        with self.assertRaisesRegex(ValueError, 'not complete'):
            probe.assess(record(Done=0))

    def test_shared_collector_retries_torn_publication_without_writes(self):
        replies = iter([800, packed(record()), 804, 804, packed(record()), 804])
        class Connection:
            def Read(self, _): return SimpleNamespace(Status='Success', Value=next(replies))
            def Write(self, *_): raise AssertionError('unexpected controller write')
        self.assertEqual(fixture.sample(Connection(), probe.TAG, probe.decode)['Samples'], 401)

    def test_generated_program_stops_exactly_after_four_hundred_intervals(self):
        # Native instructions are stubs here: this proves generated control flow,
        # indexing and the write bound, not the controller's SSV semantics.
        changed = ET.fromstring(probe.augment(self.base, resource.application()))
        members = changed.find(f"Controller/DataTypes/DataType[@Name='{probe.TYPE}']/Members")
        state = {m.get('Name'): [0] * int(m.get('Dimension')) if int(m.get('Dimension')) else 0 for m in members}
        counters = {'writes': 0, 'MaxInterval': 0, 'MinInterval': 0}
        def gsv(plc, args):
            attribute = plc.describe(args[2])
            if attribute in ('MaxInterval', 'MinInterval'):
                value = counters[attribute]
                for offset, word in enumerate((value & 0xffffffff, value >> 32)):
                    holder, index = plc.element(args[3], offset)
                    holder[index] = word if word < 2**31 else word - 2**32
            else:
                plc.write(args[3], 10000 if attribute == 'Rate' else 0)
        def ssv(plc, args):
            low, high = (plc.element(args[3], i) for i in (0, 1))
            counters[plc.describe(args[2])] = (high[0][high[1]] << 32) | (low[0][low[1]] & 0xffffffff)
            counters['writes'] += 1
        def cop(plc, args):
            low, high = (plc.element(args[0], i) for i in (0, 1))
            self.assertEqual(plc.eval(args[2]), 1)
            plc.write(args[1], (high[0][high[1]] << 32) | (low[0][low[1]] & 0xffffffff))
        plc = st.Controller({probe.TAG: state}, calls={'GSV': gsv, 'SSV': ssv, 'COP': cop})
        code = st.parse('\n'.join(probe.logic(resource.application())))
        for scan in range(401):
            counters['MaxInterval'] = max(counters['MaxInterval'], 10000)
            counters['MinInterval'] = min(counters['MinInterval'], 10000)
            plc.run(code)
            self.assertEqual(state['Done'], int(scan == 400))
        self.assertEqual((state['Window'], state['ResetCount'], counters['writes']), (4, 4, 8))
        before = dict(state)
        for _ in range(1000): plc.run(code)
        self.assertEqual(state, before)
        self.assertEqual(counters['writes'], 8)


if __name__ == '__main__':
    unittest.main()
