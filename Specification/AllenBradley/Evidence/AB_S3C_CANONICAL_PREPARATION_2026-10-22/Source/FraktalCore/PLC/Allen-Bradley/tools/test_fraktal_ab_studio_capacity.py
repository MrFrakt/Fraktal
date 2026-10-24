"""Replay qualified native controls; refuse ambiguous or unbound measurements."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest

import fraktal_ab_studio_capacity as capacity

ROOT=Path(__file__).resolve().parents[4]
FIXTURE=Path(__file__).parent/'fixtures/canonical/studio_capacity_reference_01.json.gz'


class StudioCapacityTests(unittest.TestCase):
    def setUp(self):
        self.capture=json.loads(gzip.decompress(FIXTURE.read_bytes()).decode('utf-8-sig'))
        self.pin=self.capture['SourceSha256']

    def test_native_measurement_matches_the_sealed_owner_record(self):
        owner=json.loads((ROOT/'Specification/AllenBradley/Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21/Runtime/capacity_review.json').read_text())
        report=capacity.normalize(self.capture,self.pin)
        for key in ('CanonicalSha256','UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent'):
            self.assertEqual(report[key],owner[key])
        self.assertTrue(report['Measured'] and report['VerifiedFit'])
        self.assertEqual(report['Provider'],'StudioUIAutomation')

    def test_source_change_refuses_the_measurement(self):
        self.capture['SourceSha256After']='0'*64
        with self.assertRaisesRegex(ValueError,'pinned source'):capacity.normalize(self.capture,self.pin)

    def test_safety_panel_cannot_be_mistaken_for_standard_capacity(self):
        self.capture['Snapshots'][0]['StandardParent']+=1
        with self.assertRaisesRegex(ValueError,'Standard capacity'):capacity.normalize(self.capture,self.pin)

    def test_labels_and_control_ids_must_agree(self):
        next(row for row in self.capture['Snapshots'][0]['Controls'] if row['Id']==1763)['Name']='Used Safety:'
        with self.assertRaisesRegex(ValueError,'label/control'):capacity.normalize(self.capture,self.pin)

    def test_changed_samples_refuse_even_when_each_sample_adds_up(self):
        rows={row['Id']:row for row in self.capture['Snapshots'][1]['Controls']}
        rows[1764]['Name']='2,328,251';rows[1765]['Name']='817,477'
        with self.assertRaisesRegex(ValueError,'samples changed'):capacity.normalize(self.capture,self.pin)

    def test_duplicate_ids_refuse(self):
        self.capture['Snapshots'][0]['Controls'].append(deepcopy(self.capture['Snapshots'][0]['Controls'][0]))
        with self.assertRaisesRegex(ValueError,'ambiguous'):capacity.normalize(self.capture,self.pin)

    def test_offline_and_clean_process_closure_are_required(self):
        for key in ('Offline','ProcessClosed'):
            changed=deepcopy(self.capture);changed[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):capacity.normalize(changed,self.pin)

    def test_malformed_numbers_refuse(self):
        next(row for row in self.capture['Snapshots'][0]['Controls'] if row['Id']==1765)['Name']='817,47,6'
        with self.assertRaisesRegex(ValueError,'number'):capacity.normalize(self.capture,self.pin)

    def test_bar_percentage_cross_checks_the_number_pairing(self):
        next(row for row in self.capture['Snapshots'][0]['Controls'] if row['Id']==1759)['Name']='26%'
        with self.assertRaisesRegex(ValueError,'arithmetic'):capacity.normalize(self.capture,self.pin)

    def test_other_family_is_not_implicitly_qualified(self):
        self.capture['FrameTitle']=self.capture['FrameTitle'].replace('1756-L81E','1756-L82E')
        with self.assertRaisesRegex(ValueError,'L81E v38'):capacity.normalize(self.capture,self.pin)


if __name__=='__main__':unittest.main()
