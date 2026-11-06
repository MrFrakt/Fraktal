"""C5: member-sized O10 reads preserve the same strict scan proof."""
import struct
import unittest
from types import SimpleNamespace as NS

import fraktal_ab_canonical_live as live
from test_fraktal_ab_fixture_reader import fixture_capture, SYMBOL, HANDLE
from test_fraktal_ab_canonical_live import Clock, Replay


class Selection(unittest.TestCase):
    def setUp(self):
        self.capture=fixture_capture()
        self.capture['templates'][-1]['name']='FRK_T_PressFixtureV2_ABCDEF01'
        self.clock=Clock();self.calls=[];self.counters=[]
        self.native=struct.pack('<34i',1,-17,*range(32))
        replay=Replay(self.capture)
        def raw(location):
            self.calls.append(location)
            if location.source==SYMBOL:
                return self.native[location.offset:location.offset+location.width]
            return replay.raw(location)
        def counter(symbol):
            self.counters.append(symbol)
            return 0 if len(self.counters)==1 else 2
        self.reader=live.CanonicalRowReader(self.capture,live.LeafBody(raw),counter,
                                           clock_ns=self.clock,sleep=self.clock.sleep)

    def test_scalar_and_array_are_native_selected_values_under_one_scan(self):
        row=self.reader.read_row(['Press/PartSlide/Status/State'],private={SYMBOL:('Door_DoneCount','Chart_Visited')})
        self.assertEqual(row['private'],{SYMBOL:dict(Door_DoneCount=-17,Chart_Visited=list(range(32)))})
        self.assertEqual(row['protocol'],1)
        self.assertEqual(set(self.counters),{'FRK_Press_CanonicalGeneration'})
        self.assertEqual(sum(loc.width for loc in self.calls if loc.source==SYMBOL),132)
        self.assertNotIn('Unit_Running',row['private'][SYMBOL])

    def test_a_large_fixture_never_has_to_be_read_whole(self):
        self.reader._sizes[HANDLE]=64000
        row=self.reader.read_row(['Press/CurrentStep/StepNo'],private={SYMBOL:('Door_DoneCount',)})
        self.assertEqual(row['private'][SYMBOL],{'Door_DoneCount':-17})
        self.assertEqual(next(loc for loc in self.calls if loc.source==SYMBOL).width,4)

    def test_invalid_or_empty_member_selection_refuses_before_io(self):
        for names in ((),('Missing_Field',),('Unit_Running','Unit_Running'),'Unit_Running'):
            with self.subTest(names=names),self.assertRaises(ValueError):
                self.reader.read_row(['Press/CurrentStep/StepNo'],private={SYMBOL:names})
        self.assertEqual(self.calls,[]);self.assertEqual(self.counters,[])

    def test_an_array_read_uses_its_template_element_count_and_length(self):
        location=self.reader._private_selection({SYMBOL:('Chart_Visited',)})['#'+SYMBOL+'/Chart_Visited']
        requests=[]
        comm=NS(ConnectionSize=500,_build_ioi=lambda path,kind:b'\x91\x02XX',
                _add_read_service=lambda ioi,count:requests.append(count) or b'\x4c\x02'+ioi+struct.pack('<H',count))
        body=live.PacketBody(comm,self.reader._sizes,{})
        packet,=body.plan([location])
        self.assertEqual(requests,[32])
        frame=bytes(46)+struct.pack('<BBBBH',0xcc,0,0,0,0xc4)+self.native[8:]
        self.assertEqual(body.parse(packet,frame),(self.native[8:],))
        with self.assertRaisesRegex(ValueError,'length'):
            body.parse(packet,frame[:-4])

    def test_an_odd_or_slow_proof_cannot_borrow_an_owner_window(self):
        old=self.reader._body._raw
        def slow(location):
            self.clock.now+=10_000_000
            return old(location)
        self.reader._body._raw=slow
        with self.assertRaises(live.CoherenceUnavailable):
            self.reader.read_row(['Press/PartSlide/Status/State'],private={SYMBOL:('Unit_Running',)})

    def test_malformed_native_member_name_is_not_a_symbolic_path(self):
        self.capture['templates'][-1]['members'][0]['name']='Unit_Running.Other'
        with self.assertRaises(ValueError):
            other=live.CanonicalRowReader(self.capture,self.reader._body,self.reader._counter)
            other.read_row(['Press/CurrentStep/StepNo'],private={SYMBOL:('Unit_Running.Other',)})
        self.assertEqual(self.calls,[])


if __name__=='__main__':unittest.main()
