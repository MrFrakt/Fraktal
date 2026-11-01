"""Replay the native failed-count attempt; negative mutations must refuse."""
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
import check_native_read_gates as gate
D=Path(__file__).parent;OLD=D.parent/'session_02'
class ReadGates(unittest.TestCase):
    def test_dynamic_extents_replay_exactly(self):
        result=gate.evaluate(OLD)['gates']
        for name in ['configuration_readback','idle_equivalence','generic_acquisition','native_scan']:
            self.assertTrue(result[name]['passed'],result[name])
        self.assertEqual(result['generic_acquisition']['values'],5212)
        self.assertFalse(result['C1_C11_C13']['passed'])
    def test_generic_missing_type_value_or_wrong_count_refuses(self):
        original=gate.load
        for kind in ['type','value','count','truncated','capture']:
            def changed(path):
                value=original(path)
                if path.name=='generic_snapshot.json.gz':
                    key=next(iter(value['values']))
                    if kind=='type':value['types'].pop(key)
                    if kind=='value':value['values'][key]='offline mutation'
                    if kind=='count':value['nodeCount']+=1
                    if kind=='truncated':value['truncated']=True
                if path.name=='generic_capture.json.gz' and kind=='capture':value['schema']='invalid'
                return value
            with self.subTest(kind=kind),patch.object(gate,'load',side_effect=changed):
                self.assertFalse(gate.evaluate(OLD)['gates']['generic_acquisition']['passed'])
    def test_idle_pass_flag_cannot_hide_value_or_type_difference(self):
        original=gate.load
        for kind in ['type','value','missing']:
            def changed(path):
                value=original(path)
                if path.name=='idle_equivalence.json.gz':
                    canonical=value['pair']['canonical'];key=next(iter(canonical['values']))
                    if kind=='type':canonical['types'][key]='Invalid'
                    if kind=='value':canonical['values'][key]='offline mutation'
                    if kind=='missing':canonical['values'].pop(key)
                return value
            with self.subTest(kind=kind),patch.object(gate,'load',side_effect=changed):
                self.assertFalse(gate.evaluate(OLD)['gates']['idle_equivalence']['passed'])
if __name__=='__main__':unittest.main()
