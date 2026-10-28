"""Native large-manifest replay remains as strict as Decorated read-back."""
import gzip
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_l5k_values as l5k
from fraktal_ab_readback import ascii_payload,initials

FIXTURE=Path(__file__).parent/'fixtures/canonical/s3b_l5k_manifest_03.json.gz'


class L5kTests(unittest.TestCase):
    def capture(self):
        data=json.loads(gzip.decompress(FIXTURE.read_bytes()))
        root=ET.fromstring(data['xml'])
        tag=root.find('Controller/Tags/Tag')
        expected={key:bytes.fromhex(value['bytes']) if 'bytes' in value else value['value']
                  for key,value in data['expected'].items()}
        return data,root,tag,expected

    def test_all_1717_authored_values_survive_native_l5k_export(self):
        data,root,tag,expected=self.capture()
        path=root.find('Controller').get('Name')+'/'+tag.get('Name')
        self.assertEqual(len(expected),1717)
        self.assertEqual(initials(root,fallback_tags={path}),expected)
        self.assertEqual(initials(root),{})

    def test_one_changed_native_scalar_is_a_difference(self):
        _,root,tag,expected=self.capture()
        node=tag.find("Data[@Format='L5K']")
        before='[1179798326,6,1,4,'
        self.assertEqual(node.text.count(before),1)
        node.text=node.text.replace(before,'[1179798326,7,1,4,',1)
        path=root.find('Controller').get('Name')+'/'+tag.get('Name')
        actual=l5k.decode(root,tag,path,ascii_payload)
        self.assertEqual([key for key in expected if actual.get(key)!=expected[key]],[path+'/SchemaMajor'])

    def test_nonzero_string_padding_is_not_discarded(self):
        _,root,tag,_=self.capture()
        node=tag.find("Data[@Format='L5K']")
        node.text=node.text.replace('$00','$41',1)
        with self.assertRaisesRegex(ValueError,'padding'):
            l5k.decode(root,tag,'Manifest',ascii_payload)

    def test_truncation_bad_delimiters_and_unsupported_atoms_refuse(self):
        for text in ('[1,]','[1','[1 2]','[1] trailing',"['unterminated]",'[16#FF]'):
            with self.subTest(text=text),self.assertRaises(ValueError):l5k.parse(text)

    def test_ascii_escaping_does_not_create_extra_tokens(self):
        values=l5k.parse("[2,'a$'b$$$00',[-1,2]]")
        self.assertEqual(ascii_payload(values[1]),b"a'b$\x00")
        self.assertEqual(values[2],['-1','2'])

    def test_declared_array_extent_remains_authoritative(self):
        _,root,tag,_=self.capture()
        kind=tag.get('DataType')
        members=root.find("Controller/DataTypes/DataType[@Name='"+kind+"']/Members")
        fields=members.find("Member[@Name='Fields']")
        fields.set('Dimension',str(int(fields.get('Dimension'))+1))
        with self.assertRaisesRegex(ValueError,'extent'):
            l5k.decode(root,tag,'Manifest',ascii_payload)

    def test_binary_bool_and_scientific_lreal_keep_exact_native_values(self):
        self.assertEqual(l5k.parse('[2#1,0.0000000000000000e+000]'),['2#1','0.0000000000000000e+000'])
        self.assertEqual(l5k.native_value('BOOL','2#1'),'1')
        self.assertEqual(l5k.native_value('LREAL','0.0'),l5k.native_value('LREAL','0.0000000000000000e+000'))
        self.assertNotEqual(l5k.native_value('LREAL','0.0'),l5k.native_value('LREAL','-0.0'))
        self.assertEqual(l5k.native_value('LREAL','1.0000000000000002'),'LREAL:010000000000f03f')
        for text in ('2#2','2#10','1e','nan','inf'):
            with self.assertRaises(ValueError):l5k.parse('['+text+']')
        with self.assertRaises(ValueError):l5k.native_value('INT','2#1')
        with self.assertRaises(ValueError):l5k.native_value('REAL','1e400')


if __name__=='__main__':unittest.main()
