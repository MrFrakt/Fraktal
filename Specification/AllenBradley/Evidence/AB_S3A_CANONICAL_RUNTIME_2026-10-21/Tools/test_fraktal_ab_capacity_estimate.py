"""Capacity forecasts refuse unsupported allocations and never assert measurement."""
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_capacity_estimate as capacity


def project(count=1,body='Value := 1;',opaque=False):
    root=ET.Element('RSLogix5000Content')
    controller=ET.SubElement(root,'Controller',ProcessorType='1756-L81E',MajorRev='38')
    types=ET.SubElement(controller,'DataTypes')
    members=ET.SubElement(ET.SubElement(types,'DataType',Name='Record'),'Members')
    ET.SubElement(members,'Member',Name='Values',DataType='DINT',Dimension=str(count))
    tags=ET.SubElement(controller,'Tags')
    tag=ET.SubElement(tags,'Tag',Name='One',DataType='Record',TagType='Base')
    ET.SubElement(tag,'Data',Format='Decorated').text='initial value'
    if opaque:ET.SubElement(tags,'Tag',Name='Timer',DataType='FBD_TIMER',TagType='Base')
    programs=ET.SubElement(controller,'Programs')
    program=ET.SubElement(programs,'Program',Name='Main')
    routine=ET.SubElement(ET.SubElement(program,'Routines'),'Routine',Type='ST',Name='Logic')
    ET.SubElement(ET.SubElement(routine,'STContent'),'Line').text=body
    return ET.tostring(root)


class CapacityTests(unittest.TestCase):
    def samples(self):
        return [dict(label=str(count),features=capacity.inventory(project(count)),used=used,total=1000000)
                for count,used in ((1,100000),(8,100100))]

    def test_reserved_extent_is_counted_independently_of_initial_values(self):
        small=capacity.inventory(project(1))
        large=capacity.inventory(project(64))
        self.assertGreater(large['modeledDataUnits'],small['modeledDataUnits'])
        root=ET.fromstring(project(64))
        root.find('.//Data').text='a different value'
        changed=capacity.inventory(ET.tostring(root))
        self.assertEqual(changed['score'],large['score'])
        self.assertNotEqual(changed['sourceSha256'],large['sourceSha256'])

    def test_comments_do_not_change_the_code_score(self):
        self.assertEqual(capacity.inventory(project(body='(* documentation *) Value := 1;'))['score'],
                         capacity.inventory(project())['score'])

    def test_arrays_of_records_allocate_each_instance(self):
        root=ET.fromstring(project(8))
        root.find('.//Tags/Tag').set('Dimensions','2,3')
        self.assertEqual(capacity.inventory(ET.tostring(root))['modeledDataUnits'],6*32)

    def test_model_units_are_not_reported_as_measured_blocks(self):
        report=capacity.forecast(self.samples(),capacity.inventory(project(16)))
        self.assertFalse(report['measured'])
        self.assertFalse(report['acceptanceGateSatisfied'])
        self.assertGreater(report['planningBudgetBlocks'],report['estimatedUsedBlocks'])

    def test_opaque_allocation_change_requires_new_calibration(self):
        with self.assertRaisesRegex(ValueError,'uncalibrated'):
            capacity.forecast(self.samples(),capacity.inventory(project(16,opaque=True)))

    def test_other_controller_is_not_assumed_equivalent(self):
        root=ET.fromstring(project())
        root.find('Controller').set('ProcessorType','1756-L82E')
        with self.assertRaisesRegex(ValueError,'calibrated only'):
            capacity.inventory(ET.tostring(root))

    def test_nonmonotonic_samples_are_refused(self):
        rows=self.samples()
        rows[1]['used']=rows[0]['used']-1
        with self.assertRaisesRegex(ValueError,'nonmonotonic'):
            capacity.forecast(rows,capacity.inventory(project(16)))

    def test_unknown_udt_member_and_recursive_type_are_refused(self):
        for datatype in ('VendorType','Record'):
            root=ET.fromstring(project())
            root.find('.//Member').set('DataType',datatype)
            with self.subTest(datatype=datatype),self.assertRaises(ValueError):
                capacity.inventory(ET.tostring(root))

    def test_calibration_hash_tampering_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'source.xml').write_bytes(project())
            (root/'capacity.json').write_text('{}')
            (root/'samples.json').write_text(json.dumps(dict(samples=[dict(
                source='source.xml',capacity='capacity.json',sourceSha256='0'*64,
                capacitySha256='0'*64)])))
            with self.assertRaisesRegex(ValueError,'hash differs'):
                capacity.load_observations(root/'samples.json')

    def test_measurement_must_bind_the_named_acd(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=project()
            measured=json.dumps(dict(OwnerConfirmedFit=True,CapacityUnit='Blocks',
                UsedStandardBlocks=10,AvailableBlocks=90,TotalBlocks=100,CanonicalSha256='1'*64)).encode()
            (root/'source.xml').write_bytes(source)
            (root/'capacity.json').write_bytes(measured)
            (root/'samples.json').write_text(json.dumps(dict(samples=[dict(label='test',
                source='source.xml',capacity='capacity.json',sourceSha256=capacity._hash(source),
                capacitySha256=capacity._hash(measured),acdSha256='2'*64)])))
            with self.assertRaisesRegex(ValueError,'does not bind'):
                capacity.load_observations(root/'samples.json')


if __name__=='__main__':unittest.main()
