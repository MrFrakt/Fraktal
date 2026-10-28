import contextlib
import io
import unittest
from unittest.mock import patch

import fraktal_ab_tower_execute as execute


class ExactTowerFixture(unittest.TestCase):
    def test_no_arm_refuses_before_reading_credentials_or_connecting(self):
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            execute.main(['--expect-serial','601FC87B','--credential-file','absent.json','--output','absent.json'])

    def test_another_declaration_refuses_even_when_armed(self):
        with patch.object(execute.station,'module_name',return_value='fraktal_ab_part_demo'), \
             contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            execute.main(['--execute-fixture','--expect-serial','601FC87B',
                          '--credential-file','absent.json','--output','absent.json'])


if __name__=='__main__':
    unittest.main()
