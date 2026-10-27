"""Mutation tests for the TIA candidate ABI and native-interface gate."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools import check_tia_contracts as gate
from fraktal_tia_binding import Catalog, type_source


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = gate.BASELINE.read_bytes()
        cls.baseline = json.loads(cls.raw)
        cls.current = gate.collect()
        cls.part = gate.PART.read_text(encoding='utf-8')
        cls.digest = hashlib.sha256(cls.raw).hexdigest()

    def audit(self, current=None, part=None):
        return gate.audit(self.baseline, self.current if current is None else current,
                          self.part if part is None else part, self.digest)

    def test_current_authorities_match_and_prose_binds_exact_bytes(self):
        self.assertEqual(self.audit(), [])
        self.assertTrue(self.audit(part=self.part.replace(self.digest, '0' * 64)))
        self.assertTrue(self.audit(part=self.part + '\n<!-- TIA-CONTRACTS-V2 sha256:' + self.digest + ' -->'))

    def test_logical_narrowing_and_native_width_changes_are_rejected(self):
        catalog = Catalog.read()
        catalog.records['ST_Diagnostic'][0]['type'] = 'INT'
        self.assertTrue(self.audit(current=gate.collect(catalog)))
        for key, value in [('STRING(255)', 'String[254]'), ('DT', 'DTL'), ('LREAL', 'Real')]:
            current = copy.deepcopy(self.current)
            current['typeMap'][key] = value
            self.assertTrue(self.audit(current))

    def test_removed_reordered_exposed_and_appended_fields_are_rejected(self):
        original = self.current['records']['ST_HmiRequest']
        variants = [original[1:], list(reversed(original)), original + [original[0]]]
        for fields in variants:
            current = copy.deepcopy(self.current)
            current['records']['ST_HmiRequest'] = fields
            self.assertTrue(self.audit(current))
        current = copy.deepcopy(self.current)
        current['records']['ST_ConfigEntry'][0]['accessible'] = False
        self.assertTrue(self.audit(current))

    def test_enum_reassignment_removal_and_additions_need_review(self):
        for change in ('reassign', 'remove', 'add'):
            current = copy.deepcopy(self.current)
            enum = current['enums']['E_HmiRequestKind']
            if change == 'reassign':
                enum['START'] = -1
            elif change == 'remove':
                enum.pop('START')
            else:
                enum['EXAMPLE_NEW_REQUEST'] = 999
            self.assertTrue(self.audit(current))

    def test_capacity_and_consumed_table_shape_changes_are_rejected(self):
        current = copy.deepcopy(self.current)
        current['capacities']['MAX_CONFIG_PAGE'] -= 1
        self.assertTrue(self.audit(current))
        current = copy.deepcopy(self.current)
        current['sequencePublication']['ActiveSteps'] = 'Array[1..$branches] of "ST_SequenceCursor"'
        self.assertTrue(self.audit(current))

    def test_projection_is_read_from_adapter_and_unfamiliar_code_fails_closed(self):
        text = gate.ADAPTER.read_text(encoding='utf-8')
        self.assertTrue(self.audit(gate.collect(adapter=text.replace("'lreal' => 'Double'", "'lreal' => 'Float'"))))
        for broken in ('', text.replace("'lreal' => 'Double'", "'lreal' => dynamicType()"),
                       text.replace("'lreal' => 'Double'", "'lreal' => 'Double', 'lreal' => 'Float'")):
            with self.assertRaises(ValueError):
                gate.adapter_types(broken)

    def test_generated_layout_and_private_visibility_are_checked(self):
        records = {**self.current['records'], 'PrivateExample': [
            {'member': 'Hidden', 'native_type': 'Int', 'accessible': False, 'initial': ''}]}
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name, fields in records.items():
                (directory / (name + '.udt')).write_bytes(type_source(name, fields).encode('ascii'))
            actual = gate.generated_records(directory, records)
            self.assertEqual(gate.audit_layouts(records, actual, 'generated'), [])
            row = actual['PrivateExample'][0]
            row['ExternalVisible'] = True
            self.assertTrue(gate.audit_layouts(records, actual, 'generated'))
            self.assertTrue(gate.audit_layouts(records, {}, 'generated'))
            (directory / 'duplicate.udt').write_bytes((directory / 'ST_HmiRequest.udt').read_bytes())
            with self.assertRaises(ValueError):
                gate.generated_records(directory, records)

    def test_native_xml_order_bounds_visibility_and_missing_types(self):
        records = {'Example': [{'member': 'Hidden', 'native_type': 'Array[0..2] of Int', 'accessible': False}]}
        xml = '''<Document><SW.Types.PlcStruct><AttributeList><Name>Example</Name>
        <Interface><Sections xmlns="urn:siemens:interface"><Section Name="None">
        <Member Name="Hidden" Datatype="Array[0..2] of Int"><AttributeList>
        <BooleanAttribute Name="ExternalAccessible">false</BooleanAttribute>
        <BooleanAttribute Name="ExternalVisible">false</BooleanAttribute>
        <BooleanAttribute Name="ExternalWritable">false</BooleanAttribute>
        </AttributeList></Member></Section></Sections></Interface>
        </AttributeList></SW.Types.PlcStruct></Document>'''
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / 'Example.type.xml'
            path.write_bytes(xml.encode('ascii'))
            self.assertEqual(gate.audit_layouts(records, gate.native_records(directory, records), 'native'), [])
            for changed in (xml.replace('[0..2]', '[1..2]'), xml.replace('>false<', '>true<', 1)):
                path.write_bytes(changed.encode('ascii'))
                self.assertTrue(gate.audit_layouts(records, gate.native_records(directory, records), 'native'))
            self.assertTrue(gate.audit_layouts({**records, 'Missing': []}, gate.native_records(directory, records), 'native'))
            (directory / 'duplicate.type.xml').write_bytes(xml.encode('ascii'))
            with self.assertRaises(ValueError):
                gate.native_records(directory, records)

    def test_a_successor_preserves_and_keeps_binding_every_earlier_baseline(self):
        raw = gate.BASELINES[0].read_bytes()
        v1 = (json.loads(raw), hashlib.sha256(raw).hexdigest())
        audit = lambda baseline, previous, part=None: gate.audit(
            baseline, self.current, self.part if part is None else part, self.digest, previous)
        self.assertEqual(audit(self.baseline, [v1]), [])
        changed = copy.deepcopy(self.baseline)
        changed['contracts']['enums']['E_Reason']['TASK_OVERRUN'] = 99
        self.assertTrue(any('does not preserve V1' in f for f in audit(changed, [v1])))
        dropped = copy.deepcopy(self.baseline)
        dropped['contracts']['enums']['E_Reason'].pop('NONE')
        self.assertTrue(any('does not preserve V1' in f for f in audit(dropped, [v1])))
        self.assertTrue(audit(self.baseline, [v1], part=self.part.replace(v1[1], '0' * 64)))
        self.assertTrue(audit(self.baseline, [(self.baseline, self.digest)]))

    def test_invalid_or_empty_baseline_cannot_pass(self):
        baseline = copy.deepcopy(self.baseline)
        baseline['schemaVersion'] = 2
        self.assertTrue(gate.audit(baseline, self.current, self.part, self.digest))
        baseline = copy.deepcopy(self.baseline)
        baseline['contracts'] = {}
        self.assertTrue(gate.audit(baseline, self.current, self.part, self.digest))


if __name__ == '__main__':
    unittest.main()
