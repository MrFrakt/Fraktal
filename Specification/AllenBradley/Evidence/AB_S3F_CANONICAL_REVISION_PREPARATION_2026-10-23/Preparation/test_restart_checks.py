from copy import deepcopy
import unittest
from restart_checks import compare


class RestartChecks(unittest.TestCase):
    def test_requires_retained_values_and_a_new_valid_revision(self):
        before={n:{'value':1} for n in ('records','banks','codes','active','mode','policy','page')};before['revision']=100
        after=deepcopy(before);after['revision']=200;compare(before,after)
        for key in ('records','banks','codes','active','mode','policy','page'):
            bad=deepcopy(after);bad[key]={'value':2}
            with self.assertRaises(ValueError):compare(before,bad)
        for value in (100,0,True,2147483647):
            bad=deepcopy(after);bad['revision']=value
            with self.assertRaises(ValueError):compare(before,bad)
