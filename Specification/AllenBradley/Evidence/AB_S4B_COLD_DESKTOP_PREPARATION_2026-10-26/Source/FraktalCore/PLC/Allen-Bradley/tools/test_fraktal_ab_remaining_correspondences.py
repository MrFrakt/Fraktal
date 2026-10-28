"""The approved finite namespace amendment never becomes a general coercion."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import fraktal_ab_canonical_equivalence as gate


class RemainingCorrespondenceTests(unittest.TestCase):
    def test_exact_reviewed_122_names_and_line_pair(self):
        aliases=gate.path_correspondences()
        self.assertEqual(len(aliases),122)
        self.assertEqual(aliases['Press/Line/OwnerId'],'Press/Line/Owner')
        self.assertEqual(aliases['Press/Line/LastUpdatedAt'],'Press/Line/LastUpdate')
        self.assertNotIn('Press/Line/Revision',aliases)
        old=dict(values={'Press/Line/OwnerId':'Owner'},types={'Press/Line/OwnerId':'String'})
        new=dict(values={'Press/Line/Owner':'Owner'},types={'Press/Line/Owner':'String'})
        self.assertTrue(gate.compare_documents(old,new)['typeAcceptance'])

    def test_unlisted_path_type_or_value_cannot_be_hidden(self):
        old=dict(values={'Press/Line/OwnerId':'Owner'},types={'Press/Line/OwnerId':'String'})
        for path,value,kind in (('Press/Line/Owner','Other','String'),
                                ('Press/Line/Owner','Owner','Int32'),
                                ('Press/Line/WrongOwner','Owner','String')):
            self.assertFalse(gate.compare_documents(old,dict(values={path:value},types={path:kind}))['equal'])
        wrong=dict(values={'Other/Line/OwnerId':'Owner'},types={'Other/Line/OwnerId':'String'})
        self.assertFalse(gate.compare_documents(wrong,dict(values={'Other/Line/Owner':'Owner'},types={'Other/Line/Owner':'String'}))['equal'])

    def test_duplicate_alias_and_native_path_are_a_collision(self):
        old=dict(values={'Press/Line/OwnerId':'Owner','Press/Line/Owner':'Owner'},
                 types={'Press/Line/OwnerId':'String','Press/Line/Owner':'String'})
        new=dict(values={'Press/Line/Owner':'Owner'},types={'Press/Line/Owner':'String'})
        self.assertTrue(any(row['kind']=='mappingCollision' for row in gate.compare_documents(old,new)['differences']))

    def test_modified_or_unapproved_inventory_fails_closed(self):
        source=json.loads(gate.CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as temporary:
            contract=Path(temporary)/'contracts.json'
            source['approvedRemainingSurfaceCorrection']['ownerApproved']=False
            contract.write_text(json.dumps(source))
            with patch.object(gate,'CONTRACT',contract):
                with self.assertRaisesRegex(ValueError,'owner-approved'):gate.path_correspondences()
            source['approvedRemainingSurfaceCorrection']['ownerApproved']=True
            source['approvedRemainingSurfaceCorrection']['inventory']='inventory.json'
            contract.write_text(json.dumps(source))
            (contract.parent/'inventory.json').write_text('{}')
            with patch.object(gate,'CONTRACT',contract):
                with self.assertRaisesRegex(ValueError,'hash differs'):gate.path_correspondences()


if __name__=='__main__':unittest.main()
