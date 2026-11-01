from copy import deepcopy
import unittest
from browser_witness import validate_owner,CHECKS
class Browser(unittest.TestCase):
    def valid(self):
        record=dict(token='test',ownerRecorded=True,passed=True,ownerWords='test-only witness',checks={k:True for k in CHECKS})
        before=dict(serial='601FC87B',mode=1,currentLevel=0,idle=True,loginBusy=False,typedAck=100)
        return record,before,{**before,'typedAck':104}
    def test_complete_current_witness_and_forward_acknowledgements(self):
        r,b,a=self.valid();self.assertTrue(validate_owner(r,'test',b,a)['passed'])
    def test_missing_wrong_token_or_false_check_refuses(self):
        for change in [('token','old'),('ownerRecorded',False),('passed',False),('ownerWords',''),('checks',{})]:
            r,b,a=self.valid();r[change[0]]=change[1]
            with self.subTest(change=change),self.assertRaises(ValueError):validate_owner(r,'test',b,a)
    def test_logged_in_nonmanual_busy_or_no_forward_progress_refuses(self):
        for key,value in [('mode',0),('currentLevel',4),('idle',False),('loginBusy',True),('typedAck',100),('typedAck',99)]:
            r,b,a=self.valid();a[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):validate_owner(r,'test',b,a)
if __name__=='__main__':unittest.main()
