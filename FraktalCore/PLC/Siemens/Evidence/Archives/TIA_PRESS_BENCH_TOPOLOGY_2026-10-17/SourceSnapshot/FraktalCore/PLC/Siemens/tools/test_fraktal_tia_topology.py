"""Published hardware bounds and truthful input/output observations."""
import copy
import unittest

from fraktal_tia_binding import Catalog
import fraktal_tia_topology as topology


class TopologyTests(unittest.TestCase):
    def setUp(self):
        self.catalog=Catalog.read()
        self.spec=dict(block='GDB_BenchFieldbus',publisher='F_PublishBenchFieldbus',
            image='GDB_BenchIO',healthy='LinkHealthy',nodes=[
                dict(name='Bridge',channels=[]),
                dict(name='DI',parent=1,channels=[dict(tag='_Sensor',description_key='project.sensor',
                    address='%I0.0',source='Sensor',dir='INPUT',module='Press.Sensor')]),
                dict(name='DQ',parent=1,channels=[dict(tag='_Valve',description_key='project.valve',
                    address='%Q0.0',source='Valve',dir='OUTPUT',module='Press.Valve')])])
        self.members={'LinkHealthy','Sensor','Valve'}
        self.modules={'Press.Sensor','Press.Valve'}

    def build(self,spec=None):
        return topology.sources(self.catalog,spec or self.spec,self.members,'Press',self.modules)

    def test_consumed_hardware_sizes_replace_reference_maxima(self):
        sources=self.build()
        self.assertRegex(sources['06_2_ST_FieldbusTopology.udt'],r'Nodes.*Array\[1\.\.3\]')
        self.assertRegex(sources['06_1_ST_BusNode.udt'],r'Channels.*Array\[1\.\.1\]')
        self.assertNotIn('ExternalWritable := \'True\'',sources['38_GDB_BenchFieldbus.db'])

    def test_connected_inputs_do_not_claim_applied_output_feedback(self):
        source=self.build()['38_F_PublishBenchFieldbus.scl']
        self.assertIn('Nodes[2].Channels[1].Quality := #Healthy;',source)
        self.assertIn('Nodes[3].Channels[1].Quality := FALSE;',source)
        self.assertIn('Nodes[3].Channels[1].BoolValue := "GDB_BenchIO".Valve;',source)

    def test_invalid_mapping_fails_before_emission(self):
        for case in ('parent','source','owner','duplicate','width'):
            spec=copy.deepcopy(self.spec)
            row=spec['nodes'][1]['channels'][0]
            if case=='parent':spec['nodes'][1]['parent']=2
            elif case=='source':row['source']='Missing'
            elif case=='owner':row['module']='Other.Sensor'
            elif case=='duplicate':spec['nodes'][1]['channels'].append(copy.deepcopy(row))
            else:row['tag']='x'*1000
            with self.subTest(case=case),self.assertRaises(ValueError):self.build(spec)


if __name__=='__main__':unittest.main()
