import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

import fraktal_ab_readback as readback


SOURCE = '''<RSLogix5000Content><Controller Name="Test">
<DataTypes/><AddOnInstructionDefinitions/>
<Tags><Tag Name="Identity" DataType="DINT" TagType="Base" ExternalAccess="Read Only" Constant="false">
<Data Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="42"/></Data></Tag></Tags>
<Programs><Program Name="Main" MainRoutineName="Logic"><Tags/><Routines>
<Routine Name="Logic" Type="ST"><STContent><Line Number="0"><![CDATA[X := 1;]]></Line></STContent></Routine>
<Routine Name="Ladder" Type="RLL"><RLLContent><Rung Number="0"><Text><![CDATA[MOVE(1,X);]]></Text></Rung></RLLContent></Routine>
</Routines></Program></Programs><Tasks/></Controller></RSLogix5000Content>'''


class NativeReadback(unittest.TestCase):
    def compare(self, exported):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder)/'source.L5X', Path(folder)/'export.L5X'
            a.write_text(SOURCE)
            b.write_text(exported)
            return readback.compare(a,b)

    def test_equal_artifact_passes(self):
        self.assertTrue(self.compare(SOURCE)['Equivalent'])

    def test_same_line_count_with_changed_st_is_rejected(self):
        result = self.compare(SOURCE.replace('X := 1;', 'X := 2;'))
        self.assertTrue(result['Inventory']['Equivalent'])
        self.assertEqual(result['ExecutableDifferences'], ['Main/Logic'])
        self.assertFalse(result['Equivalent'])

    def test_changed_rung_operand_is_rejected(self):
        self.assertFalse(self.compare(SOURCE.replace('MOVE(1,X)', 'MOVE(2,X)'))['Equivalent'])

    def test_identity_initial_value_loss_is_rejected(self):
        result = self.compare(SOURCE.replace('Value="42"', 'Value="0"'))
        self.assertTrue(result['Inventory']['Equivalent'])
        self.assertEqual(result['InitialValueDifferences'], ['Test/Identity'])
        self.assertFalse(result['Equivalent'])

    def test_presentation_is_ignored_and_quoted_whitespace_is_preserved(self):
        self.assertEqual(readback.normalized("(* note *) X := 'a b';\n"), "X:='a b';")
        self.assertNotEqual(readback.normalized("X := 'a b';"), readback.normalized("X := 'ab';"))
        self.assertEqual(readback.normalized('X:=1; // comment\n Y:=2;'), 'X:=1;Y:=2;')

    def test_sdk_empty_ascii_normalization_is_explicit_and_nonempty_text_is_kept(self):
        import xml.etree.ElementTree as ET
        def artifact(value):
            return ET.fromstring('<RSLogix5000Content><Controller Name="C"><Tags><Tag Name="S">'
                '<Data Format="Decorated"><DataValue Radix="ASCII">' + value +
                '</DataValue></Data></Tag></Tags></Controller></RSLogix5000Content>')
        self.assertEqual(readback.initials(artifact("''")), readback.initials(artifact('')))
        self.assertNotEqual(readback.initials(artifact("'asset'")), readback.initials(artifact('')))

    def test_native_ascii_escape_spellings_compare_by_actual_bytes(self):
        self.assertEqual(readback.ascii_payload("'a]]$3Eb'"), b'a]]>b')
        self.assertEqual(readback.ascii_payload("'$$$'tool'"), b"$'tool")
        with self.assertRaises(ValueError):
            readback.ascii_payload("'truncated$'")

    def alarm(self, **attributes):
        root = ET.fromstring(SOURCE)
        tag = root.find('Controller/Tags/Tag')
        alarm = ET.SubElement(ET.SubElement(tag,'AlarmConditions'),'AlarmCondition',
                              dict(Name='Fault',Input='.0',ConditionType='TRIP',
                                   Severity='700',AckRequired='false',Latched='false',
                                   Expression='Input = 1',AssocTag1='Reason',**attributes))
        config = ET.SubElement(alarm,'AlarmConfig')
        ET.SubElement(config,'AlarmClass').text = 'Fraktal'
        text = ET.SubElement(ET.SubElement(ET.SubElement(config,'Messages'),'Message',Type='CAM'),'Text',Lang='en-US')
        text.text = 'Actual fault message'
        return root, alarm

    def test_native_alarm_loss_can_no_longer_pass_with_identical_tags_and_code(self):
        first, alarm = self.alarm()
        second = ET.fromstring(ET.tostring(first))
        second.find('Controller/Tags/Tag').remove(second.find('.//AlarmConditions'))
        count,differences = readback.alarm_differences(first,second)
        self.assertEqual(count,1)
        self.assertTrue(differences)
        with tempfile.TemporaryDirectory() as folder:
            a,b = Path(folder)/'a.L5X',Path(folder)/'b.L5X'
            ET.ElementTree(first).write(a)
            ET.ElementTree(second).write(b)
            result = readback.compare(a,b)
        self.assertTrue(result['Inventory']['Equivalent'])
        self.assertFalse(result['Equivalent'])
        self.assertTrue(result['AlarmDifferences'])

    def test_all_authored_native_fields_messages_and_identity_are_checked(self):
        first, alarm = self.alarm()
        mutations = [lambda n:n.set('Input','.1'),lambda n:n.set('Severity','900'),
                     lambda n:n.set('AssocTag1','OtherReason'),lambda n:n.set('Latched','true'),
                     lambda n:n.set('AckRequired','true'),lambda n:n.set('Expression','Input = 0'),
                     lambda n:n.find('AlarmConfig/AlarmClass').__setattr__('text','Other'),
                     lambda n:n.find('.//Text').__setattr__('text','Wrong message')]
        for mutate in mutations:
            second = ET.fromstring(ET.tostring(first))
            mutate(second.find('.//AlarmCondition'))
            self.assertTrue(readback.alarm_differences(first,second)[1])

    def test_defaults_numeric_and_expression_presentation_do_not_hide_differences(self):
        first, alarm = self.alarm()
        second = ET.fromstring(ET.tostring(first))
        node = second.find('.//AlarmCondition')
        node.set('Severity','700.0')
        node.set('Expression','Input=1')
        node.set('DelayOn','0')
        self.assertEqual(readback.alarm_differences(first,second)[1],[])
        node.set('Severity','701')
        self.assertTrue(readback.alarm_differences(first,second)[1])

    def test_definition_scope_extra_and_duplicate_alarms_are_not_collapsed(self):
        first, alarm = self.alarm()
        import copy
        second = ET.fromstring(ET.tostring(first))
        tag = second.find('Controller/Tags/Tag/AlarmConditions')
        added = copy.deepcopy(alarm)
        added.set('Name','Additional')
        tag.append(added)
        self.assertTrue(readback.alarm_differences(first,second)[1])
        tag.append(copy.deepcopy(added))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            readback.alarm_metadata(second)
        second = ET.fromstring(ET.tostring(first))
        definitions = ET.SubElement(second.find('Controller'),'AlarmDefinitions')
        owner = ET.SubElement(definitions,'DataTypeAlarmDefinition',Name='Device')
        ET.SubElement(owner,'MemberAlarmDefinition',Name='Fault',Input='.Failed')
        self.assertEqual(len(readback.alarm_metadata(second)),2)

    def test_native_almd_parameter_and_message_loss_is_checked_but_implicit_defaults_allowed(self):
        first = ET.fromstring(SOURCE)
        second = ET.fromstring(SOURCE)
        for root in (first,second):
            root.find('Controller/Tags/Tag').set('DataType','ALARM_DIGITAL')
        data = ET.SubElement(second.find('Controller/Tags/Tag'),'Data',Format='Alarm')
        parameters = ET.SubElement(data,'AlarmDigitalParameters',Severity='500',Latched='false')
        self.assertEqual(readback.alarm_differences(first,second)[1],[])
        first = ET.fromstring(ET.tostring(second))
        parameters.set('Latched','true')
        self.assertTrue(readback.alarm_differences(first,second)[1])

    def test_unrequested_alarm_configuration_is_not_a_native_default_on_an_ordinary_tag(self):
        first = ET.fromstring(SOURCE)
        second = ET.fromstring(SOURCE)
        data = ET.SubElement(second.find('Controller/Tags/Tag'),'Data',Format='Alarm')
        ET.SubElement(data,'AlarmDigitalParameters',Severity='500')
        self.assertTrue(readback.alarm_differences(first,second)[1])


if __name__ == '__main__':
    unittest.main()
