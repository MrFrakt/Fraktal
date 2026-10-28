"""Versioned 24-reason owner; legacy layouts and emitted logic stay released."""
from dataclasses import replace
import unittest

import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s3j_demo as prior
import fraktal_ab_canonical_unit_core as core
import fraktal_ab_st_model as st


class ReleaseOwnerTests(unittest.TestCase):
    def setUp(self):
        self.old=prior.application()
        self.app=replace(self.old,canonical_publication_stage=13)
        self.value=st.structure(gen.release_report_members(self.app))
        self.plc=st.Controller({'Report':self.value})

    def run_lines(self,lines):
        self.plc.run('\n'.join(lines))

    def test_owner_versions_capacity_from_core_without_changing_v1(self):
        self.assertEqual(gen.release_capacity(self.old),8)
        self.assertEqual(gen.release_capacity(self.app),core.core_limit('MAX_RELEASE_REASONS'))
        self.assertEqual(gen.release_capacity(self.app),24)
        self.assertEqual(gen.release_report_name(self.app),gen.release_report_name(self.old)+'V2')
        old={m.name:m for m in gen.release_report_members(self.old)}
        new={m.name:m for m in gen.release_report_members(self.app)}
        self.assertNotIn('Overflow',old)
        for field in ('Key','Reason','Source','Kind'):
            self.assertEqual(old[field].dimension,8)
            self.assertEqual(new[field].dimension,24)

    def test_ninth_and_twenty_fourth_failure_remain_in_the_complete_owner(self):
        self.run_lines(gen.report_open('Report',app=self.app))
        for i in range(24):
            self.run_lines(gen.report_add('Report',100+i,200+i,i%7,'INTERLOCK',app=self.app))
        self.run_lines(gen.report_close('Report',app=self.app))
        self.assertEqual((self.value['Count'],self.value['Released'],self.value['Overflow']),(24,0,0))
        self.assertEqual(self.value['Key'],list(range(100,124)))
        self.assertEqual(self.value['Reason'],list(range(200,224)))

    def test_saturation_and_corrupt_index_fail_closed_without_overwriting_a_row(self):
        for count in (-1,24,25,2147483647):
            with self.subTest(count=count):
                self.value.update(Count=count,Overflow=0,Released=1)
                self.value['Key'][:]=list(range(24))
                self.run_lines(gen.report_add('Report',999,999,0,'OTHER',app=self.app))
                self.run_lines(gen.report_close('Report',app=self.app))
                self.assertEqual(self.value['Count'],count)
                self.assertEqual(self.value['Key'],list(range(24)))
                self.assertEqual((self.value['Overflow'],self.value['Released']),(1,0))

    def test_reopening_clears_overflow_and_empty_report_is_released(self):
        self.value.update(Count=25,Overflow=1,Released=0)
        self.run_lines(gen.report_open('Report',app=self.app)+gen.report_close('Report',app=self.app))
        self.assertEqual((self.value['Count'],self.value['Overflow'],self.value['Released']),(0,0,1))


if __name__=='__main__':unittest.main()
