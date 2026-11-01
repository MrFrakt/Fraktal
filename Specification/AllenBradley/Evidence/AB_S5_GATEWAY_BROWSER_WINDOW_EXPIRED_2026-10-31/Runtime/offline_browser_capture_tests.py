import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import browser_witness as witness

class WitnessCapture(unittest.TestCase):
    def state(self,ack):
        return dict(serial='601FC87B',mode=1,currentLevel=0,loginBusy=False,idle=True,typedAck=ack,readOnly=True)
    def exercise(self,ack):
        records={};order=[]
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            def state():order.append('state');return self.state(22 if order.count('state')==1 else ack)
            def save(name,value):records[name]=value;order.append(name)
            def ready():
                order.append('open-browser')
                record=dict(token=records['browser_ready.json']['token'],ownerRecorded=True,passed=True,
                    ownerWords='synthetic offline answer; never used with Echo',checks={key:True for key in witness.CHECKS})
                (directory/'browser_owner_checklist.json').write_text(json.dumps(record))
            with patch.object(witness,'D',directory),patch.object(witness,'state',state):
                if ack==22:
                    with self.assertRaisesRegex(ValueError,'No forward'):witness.witness(save,timeout=1,on_ready=ready)
                else:self.assertTrue(witness.witness(save,timeout=1,on_ready=ready)['passed'])
        self.assertLess(order.index('state'),order.index('open-browser'))
        self.assertEqual(records['browser_native_boundary_after.json']['after']['typedAck'],ack)
        return records
    def test_refused_ack_progress_is_preserved_without_pass(self):
        records=self.exercise(22)
        self.assertNotIn('browser_C12_result.json',records)
    def test_actual_progress_keeps_existing_guard(self):
        self.assertIn('browser_C12_result.json',self.exercise(28))

if __name__=='__main__':unittest.main()
