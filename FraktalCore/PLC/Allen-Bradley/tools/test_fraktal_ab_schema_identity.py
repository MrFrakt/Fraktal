"""The WP6.6 schema-identity gate: what it records, what it compares, and that
the two S6-Q declarations still publish their recorded pre-collapse surface."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fraktal_ab_schema_identity as si
from test_fraktal_ab_generate import SEED_38

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / 'fixtures' / 'schema_identity'
GATED = ('fraktal_ab_genealogy_s6_host_demo', 'fraktal_ab_press_canonical_echo38')

L5X = """<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content><Controller Name="C">
<DataTypes>
<DataType Name="T_Leaf"><Members>
<Member Name="State" DataType="DINT" Dimension="0" ExternalAccess="Read Only"/>
<Member Name="Rows" DataType="DINT" Dimension="4" ExternalAccess="Read Only"/>
</Members></DataType>
<DataType Name="T_Root"><Members>
<Member Name="Door" DataType="T_Leaf" Dimension="0" ExternalAccess="Read Only"/>
</Members></DataType>
<DataType Name="T_Header"><Members>
<Member Name="Magic" DataType="DINT" Dimension="0"/>
<Member Name="ContentHash" DataType="DINT" Dimension="0"/>
<Member Name="ConfigRevision" DataType="DINT" Dimension="0"/>
<Member Name="LegacyContentHash" DataType="DINT" Dimension="0"/>
</Members></DataType>
<DataType Name="T_Private"><Members><Member Name="X" DataType="DINT" Dimension="0"/></Members></DataType>
</DataTypes>
<AddOnInstructionDefinitions/>
<Tags>
<Tag Name="Root" TagType="Base" DataType="T_Root" ExternalAccess="Read Only"><Data Format="Decorated">
<Structure DataType="T_Root"><StructureMember Name="Door" DataType="T_Leaf">
<DataValueMember Name="State" DataType="DINT" Value="{state}"/>
<ArrayMember Name="Rows" DataType="DINT" Dimensions="4"><Element Index="[0]" Value="1"/><Element Index="[1]" Value="2"/>
<Element Index="[2]" Value="3"/><Element Index="[3]" Value="4"/></ArrayMember>
</StructureMember></Structure></Data></Tag>
<Tag Name="Header" TagType="Base" DataType="T_Header" ExternalAccess="Read Only"><Data Format="Decorated">
<Structure DataType="T_Header"><DataValueMember Name="Magic" DataType="DINT" Value="7"/>
<DataValueMember Name="ContentHash" DataType="DINT" Value="{hash}"/>
<DataValueMember Name="ConfigRevision" DataType="DINT" Value="{hash}"/>
<DataValueMember Name="LegacyContentHash" DataType="DINT" Value="{hash}"/></Structure></Data></Tag>
<Tag Name="Work" TagType="Base" DataType="T_Private" ExternalAccess="None"/>
{extra}
</Tags></Controller></RSLogix5000Content>
"""


def record(state=0, digest=1, extra=''):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'image.L5X'
        path.write_text(L5X.format(state=state, hash=digest, extra=extra), encoding='utf-8')
        return si.surface(path)


LEGACY = '<Tag Name="Legacy" TagType="Base" DataType="T_Private" ExternalAccess="Read/Write"/>'


class Surface(unittest.TestCase):
    def test_records_only_what_a_client_can_reach(self):
        s = record(extra=LEGACY)
        self.assertEqual(sorted(s['tags']), ['Header', 'Legacy', 'Root'])
        self.assertEqual(sorted(s['types']), ['T_Header', 'T_Leaf', 'T_Private', 'T_Root'])
        self.assertNotIn('T_Private', record()['types'], 'a type only an unpublished tag uses is not surface')
        self.assertEqual(s['tags']['Root']['Data'], {'Door': {'State': '0', 'Rows': ['1', '2', '3', '4']}})

    def test_derived_hashes_are_recorded_apart_and_never_compared(self):
        before, after = record(digest=1), record(digest=2)
        self.assertEqual(before['derivedHashes'], {'Header.ContentHash': '1', 'Header.ConfigRevision': '1',
                                                   'Header.LegacyContentHash': '1'})
        self.assertEqual(si.differences(before, after), [])
        self.assertTrue(si.compare(before, after)['passed'])


class Gate(unittest.TestCase):
    def test_identical_surfaces_pass_with_nothing_declared(self):
        self.assertEqual(si.compare(record(), record()),
                         dict(passed=True, uncovered=[], covered=[], unusedDeclarations=[],
                              derivedHashes=dict(before=record()['derivedHashes'],
                                                 after=record()['derivedHashes'])))

    def test_a_leaf_value_change_is_named_by_its_path(self):
        self.assertEqual(si.differences(record(state=0), record(state=3)), [('Root.Data.Door.State', 'changed')])

    def test_a_removed_tag_needs_a_declared_removal(self):
        before, after = record(extra=LEGACY), record()
        self.assertEqual(si.differences(before, after), [('Legacy', 'removed'), ('T_Private', 'removed')])
        self.assertFalse(si.compare(before, after)['passed'])
        declared = [si.Declared('Legacy', 'removed', 'R8'), si.Declared('T_Private', 'removed', 'R8')]
        result = si.compare(before, after, declared)
        self.assertTrue(result['passed'], result)
        self.assertEqual([c['reason'] for c in result['covered']], ['R8', 'R8'])

    def test_a_declaration_covers_only_its_own_kind_of_change(self):
        before, after = record(extra=LEGACY), record()
        result = si.compare(after, before, [si.Declared('Legacy', 'removed', 'R8'),
                                            si.Declared('T_Private', 'removed', 'R8')])
        self.assertFalse(result['passed'], 'a removal does not permit an addition')
        self.assertEqual([u['change'] for u in result['uncovered']], ['added', 'added'])

    def test_a_declaration_that_covers_nothing_fails(self):
        result = si.compare(record(), record(), [si.Declared('Legacy', 'removed', 'R8')])
        self.assertFalse(result['passed'])
        self.assertEqual(result['unusedDeclarations'], [dict(pattern='Legacy', change='removed', reason='R8')])

    def test_a_member_change_and_reordering_are_named(self):
        before = record()
        after = json.loads(json.dumps(before))
        after['types']['T_Leaf']['members'].reverse()
        after['types']['T_Leaf']['members'][0]['ExternalAccess'] = 'Read/Write'
        self.assertEqual(si.differences(before, after),
                         [('T_Leaf.@order[0]', 'changed'), ('T_Leaf.@order[1]', 'changed'),
                          ('T_Leaf.Rows.ExternalAccess', 'changed')])

    def test_an_unknown_change_kind_is_refused(self):
        with self.assertRaises(ValueError):
            si.Declared('X', 'renamed', 'R8')


class RecordedSurfaces(unittest.TestCase):
    """The two S6-Q declarations against their surfaces recorded before WP6.6.

    Each collapse increment adds what it intends to the declaration's
    `.declared.json`; nothing else may move."""

    def test_each_gated_declaration_publishes_its_recorded_surface(self):
        with tempfile.TemporaryDirectory() as folder:
            seed = Path(folder) / 'seed.L5X'
            seed.write_text(SEED_38, encoding='utf-8')
            for declaration in GATED:
                with self.subTest(declaration):
                    args = [sys.executable, str(HERE / 'fraktal_ab_schema_identity.py'), '--declaration', declaration,
                            '--seed', str(seed), '--check', str(FIXTURES / f'{declaration}.json.gz'),
                            '--declared', str(FIXTURES / f'{declaration}.declared.json')]
                    env = {k: v for k, v in os.environ.items() if k != 'FRAKTAL_AB_DECLARATION'}
                    done = subprocess.run(args, capture_output=True, text=True, cwd=HERE, env=env)
                    self.assertEqual(done.returncode, 0, done.stdout[-4000:] + done.stderr[-4000:])


if __name__ == '__main__':
    unittest.main()
