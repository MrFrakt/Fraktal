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

    def forcing(self):
        spec=copy.deepcopy(self.spec)
        spec.update(forcing=True,apply='F_ApplyBenchForces')
        spec['nodes'][2]['channels'][0]['forceable']=True
        return spec

    def test_production_image_carries_no_force_surface(self):
        sources=self.build()
        self.assertNotIn('16e_OutputForcing.scl',sources)
        self.assertNotIn('Forceable := TRUE',sources['38_GDB_BenchFieldbus.db'])
        self.assertIn('"Forceable" {ExternalAccessible := \'False\'',sources['06_0_ST_IoChannel.udt'])
        self.assertEqual(topology.unit_calls(self.spec,self.catalog),{})

    def test_engineering_image_publishes_only_the_declared_capability(self):
        sources=self.build(self.forcing())
        self.assertIn('"Forceable" : Bool;',sources['06_0_ST_IoChannel.udt'])
        for private in ('ForceBool','ForceAnalog'):
            self.assertIn('"%s" {ExternalAccessible := \'False\''%private,sources['06_0_ST_IoChannel.udt'])
        self.assertIn('"ForcesEnabled" {ExternalAccessible := \'False\'',sources['06_2_ST_FieldbusTopology.udt'])
        self.assertEqual(sources['38_GDB_BenchFieldbus.db'].count('Forceable := TRUE'),1)
        self.assertIn('Topology.Nodes[3].Channels[1].Forceable := TRUE;',sources['38_GDB_BenchFieldbus.db'])
        self.assertNotRegex(sources['16e_OutputForcing.scl'],r'@[A-Za-z_.]+@')
        apply=sources['38_F_ApplyBenchForces.scl']
        self.assertIn('IF NOT "GDB_BenchFieldbus".Topology.ForcesEnabled THEN RETURN; END_IF;',apply)
        self.assertIn('IF "GDB_BenchFieldbus".Topology.Nodes[3].Channels[1].Forced THEN "GDB_BenchIO".Valve := "GDB_BenchFieldbus".Topology.Nodes[3].Channels[1].ForceBool; END_IF;',apply)
        calls=topology.unit_calls(self.forcing(),self.catalog)
        manual,ready=self.catalog.enums['E_Mode']['MANUAL'],self.catalog.enums['E_ExecState']['READY']
        self.assertIn('Permit := #Unit.Mode = %d AND #Core.Exec = %d'%(manual,ready),calls['tick'])
        self.assertIn('Topology := "GDB_BenchFieldbus".Topology',calls['request'])

    def test_force_capability_refused_where_rules_forbid_it(self):
        for case in ('input','undriven','shared','apply','gate'):
            spec=self.forcing()
            if case=='input':spec['nodes'][1]['channels'][0]['forceable']=True
            elif case=='undriven':spec['nodes'][2]['channels'][0]['source']=None
            elif case=='shared':
                twin=copy.deepcopy(spec['nodes'][2]['channels'][0]);twin['tag']='_Valve2'
                spec['nodes'][2]['channels'].append(twin)
            elif case=='apply':del spec['apply']
            else:spec['forcing']=1
            with self.subTest(case=case),self.assertRaises(ValueError):self.build(spec)


if __name__=='__main__':unittest.main()
