"""The generated V6.11 host-services image against the native rules v38 enforces.

Generated once. Each check is a class of defect the offline gates once passed
and Studio v38 or the controller refused:
- a BOOL comparison operand (both v38 builds, 2026-11-04);
- a writable ingress whose nested members are not writable (CIP 0x0F on the
  first native host request, 2026-11-04).
"""
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_access_audit as access
import fraktal_ab_canonical_commands as commands
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s6_host_demo as candidate
import fraktal_ab_host_services as host
import fraktal_ab_st_bool_operands as bool_operands
from test_fraktal_ab_generate import SEED_38


class Emitted(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = candidate.application()
        cls.folder = tempfile.TemporaryDirectory()
        source = Path(cls.folder.name) / 'seed.L5X'
        source.write_text(SEED_38, encoding='utf-8')
        cls.image = Path(cls.folder.name) / 'app.L5X'
        gen.generate(cls.app, source, cls.image)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_no_bool_operand(self):
        self.assertEqual(bool_operands.findings(ET.parse(self.image).getroot()), [])

    def test_every_member_a_client_writes_is_writable(self):
        ingress = {host.request_tag(self.app), host.commit_tag(self.app),
                   commands.payload_tag(self.app), commands.commit_tag(self.app)}
        tags = access.controller_tags(self.image)
        self.assertEqual({tags[t] for t in ingress}, {'Read/Write'})
        self.assertEqual(access.unwritable_members(self.image, ingress), [])


PROJECT = """<RSLogix5000Content><Controller><DataTypes>
<DataType Name="S_Public" Family="StringFamily"><Members>
<Member Name="LEN" DataType="DINT" ExternalAccess="Read Only"/><Member Name="DATA" DataType="SINT" ExternalAccess="Read Only"/></Members></DataType>
<DataType Name="S_Writable" Family="StringFamily"><Members>
<Member Name="LEN" DataType="DINT" ExternalAccess="Read/Write"/><Member Name="DATA" DataType="SINT" ExternalAccess="Read/Write"/></Members></DataType>
<DataType Name="T_Body"><Members>
<Member Name="Count" DataType="DINT" ExternalAccess="Read/Write"/><Member Name="Text" DataType="{text}" ExternalAccess="Read/Write"/></Members></DataType>
<DataType Name="T_Request"><Members>
<Member Name="Serial" DataType="DINT" ExternalAccess="Read/Write"/><Member Name="Body" DataType="T_Body" ExternalAccess="Read/Write"/></Members></DataType>
</DataTypes><Tags><Tag Name="Request" DataType="T_Request" ExternalAccess="Read/Write"/></Tags></Controller></RSLogix5000Content>"""


class Closure(unittest.TestCase):
    def findings(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'p.L5X'
            path.write_text(PROJECT.format(text=text), encoding='utf-8')
            return access.unwritable_members(path, {'Request'})

    def test_a_nested_read_only_member_is_found_through_every_level(self):
        self.assertEqual(self.findings('S_Public'),
                         ['Request.Body.Text.LEN: Read Only', 'Request.Body.Text.DATA: Read Only'])

    def test_a_fully_writable_closure_passes(self):
        self.assertEqual(self.findings('S_Writable'), [])

    def test_an_unknown_tag_refuses_instead_of_passing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'p.L5X'
            path.write_text(PROJECT.format(text='S_Writable'), encoding='utf-8')
            with self.assertRaises(access.AuditError):
                access.unwritable_members(path, {'Missing'})


if __name__ == '__main__':
    unittest.main()
