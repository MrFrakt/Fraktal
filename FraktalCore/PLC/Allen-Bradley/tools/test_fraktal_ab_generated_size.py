"""Growth accounting includes allocated array capacity and every routine scope."""
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_generated_size as size


class GeneratedSize(unittest.TestCase):
    def test_comments_do_not_inflate_statement_count(self):
        self.assertEqual(size.st_size('(* a; *)\nX := 0; // b;\n')['StStatementTerminators'], 1)

    def test_string_padding_arrays_and_aoi_exclusions_are_explicit(self):
        root = ET.fromstring('''<Project><Controller><DataTypes>
          <DataType Name="Key"><Members><Member Name="LEN" DataType="DINT"/>
          <Member Name="DATA" DataType="SINT" Dimension="5"/></Members></DataType>
          <DataType Name="Row"><Members><Member Name="Id" DataType="DINT"/>
          <Member Name="Key" DataType="Key"/></Members></DataType></DataTypes>
          <Tags><Tag Name="Rows" DataType="Row" Dimensions="8"/>
          <Tag Name="Atomic" DataType="DINT"/>
          <Tag Name="Instance" DataType="Worker"/>
          <Tag Name="Alias" TagType="Alias" DataType="DINT"/>
          <Tag Name="Unknown" DataType="TIMER"/></Tags>
          <AddOnInstructionDefinitions><AddOnInstructionDefinition Name="Worker"><Routines>
          <Routine Name="Logic"><STContent><Line>X := 1;</Line></STContent></Routine>
          </Routines></AddOnInstructionDefinition></AddOnInstructionDefinitions>
          <Programs><Program Name="P"><Tags><Tag Name="Local" DataType="DINT" Dimensions="2,3"/></Tags>
          <Routines><Routine Name="Logic"><STContent><Line>X := 2;</Line></STContent></Routine>
          <Routine Name="Ladder"><RLLContent><Rung/></RLLContent></Routine></Routines></Program></Programs>
          </Controller></Project>''')
        result = size.report(root)
        self.assertEqual(result['Totals']['DeclaredDataBytes'], 8 * 16 + 4 + 24)
        self.assertEqual(result['Totals']['StStatementTerminators'], 2)
        self.assertEqual(result['Totals']['RllRungs'], 1)
        self.assertEqual(len(result['Routines']), 3)  # identically named Logic routines kept
        self.assertEqual(result['ExcludedTags'], {'Controller/Instance': 'AOI instance',
            'Controller/Alias': 'alias', 'Controller/Unknown': 'unsupported type: TIMER'})
        self.assertFalse(result['StudioFitVerified'])

    def test_comparison_reports_growth_and_removed_routines(self):
        old = dict(Totals={'StSourceBytes': 100, 'DeclaredDataBytes': 8}, Routines={'A': {'StSourceBytes': 100}})
        new = dict(Totals={'StSourceBytes': 110, 'DeclaredDataBytes': 12}, Routines={'B': {'StSourceBytes': 110}})
        self.assertEqual(size.compare(old, new), dict(TotalDelta={'StSourceBytes': 10, 'DeclaredDataBytes': 4},
            RoutineDelta={'B': {'StSourceBytes': 110}}, RemovedRoutines=['A']))


if __name__ == '__main__':
    unittest.main()
