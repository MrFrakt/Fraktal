from copy import deepcopy
from pathlib import Path
import json,unittest
from capacity_readiness import validate,FIELDS
D=Path(__file__).parent
class CapacityReadiness(unittest.TestCase):
    def setUp(self):
        self.template=json.loads((D/'authorization.template.json').read_bytes())
        self.measurement=json.loads((D/'capacity_review.json').read_bytes())
        self.pin=(D/'canonical.sha256').read_text().strip()
    def test_exact_measured_confirmation_matches_while_approval_stays_false(self):
        self.assertFalse(self.template['CurrentOwnerApproved'])
        self.assertTrue(validate(self.template,self.measurement,self.pin))
        self.assertEqual(self.template['OwnerCapacityConfirmed'],{k:self.measurement[k] for k in FIELDS})
    def test_prior_image_figures_refuse_even_when_their_arithmetic_is_valid(self):
        self.template['OwnerCapacityConfirmed'].update(UsedStandardBlocks=2066212,
            AvailableBlocks=1079516,DisplayedUsagePercent=65)
        with self.assertRaisesRegex(ValueError,'differs'):validate(self.template,self.measurement,self.pin)
    def test_wrong_pin_or_each_mismatched_number_refuses(self):
        with self.assertRaises(ValueError):validate(self.template,self.measurement,'0'*64)
        for field in FIELDS:
            bad=deepcopy(self.template);bad['OwnerCapacityConfirmed'][field]+=1
            with self.subTest(field=field),self.assertRaises(ValueError):validate(bad,self.measurement,self.pin)
if __name__=='__main__':unittest.main(verbosity=2)
