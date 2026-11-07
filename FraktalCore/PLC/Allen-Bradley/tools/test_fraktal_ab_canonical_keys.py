"""C5b assertion metadata comes from the image, not declaration-side ordinals.

The namespace/templates are a native S5 capture; key bytes and revision
progress below are synthetic transport seams, not a new controller result.
"""
from copy import deepcopy
import struct
import unittest

import fraktal_ab_canonical_live as live
import fraktal_ab_canonical_reader as reader
from test_fraktal_ab_canonical_live import CAPTURE, Clock, Replay


class Keys(unittest.TestCase):
    def setUp(self):
        self.capture=reader.load_json(CAPTURE)
        descriptor=self.capture['manifest']['commandBindings'][0]
        old=descriptor['KeysSymbol'];descriptor.update(KeysSymbol='UnrelatedCatalogue',KeysCount=3)
        symbol=next(s for s in self.capture['symbols'] if s['name']==old)
        symbol['name']='UnrelatedCatalogue';self.handle=symbol['handle']
        self.clock=Clock();self.reads=[];self.progress=0;self.epoch_reads=0;self.change_epoch=False
        self.entries=[(731,'std.fixture.denied'),(8,'std.fixture.unknown'),(403,'std.fixture.stale')]

    def build(self, *, mutate=None):
        self.capture['manifest']['commandBindings'][0]['KeysCount']=len(self.entries)
        self.objects,self.sizes=reader.template_objects(self.capture['templates'])
        self.fields={m['name']:m for m in reader.member_table(self.objects[self.handle])}
        text=self.fields['PortableKey']
        self.parts={m['name']:m for m in reader.member_table(self.objects[text['handle']])}
        size=self.sizes[self.handle];self.raw=bytearray(size*len(self.entries))
        for i,(number,label) in enumerate(self.entries):
            at=i*size
            struct.pack_into('<i',self.raw,at+self.fields['NumericKey']['offset'],number)
            start=at+text['offset'];encoded=label.encode('utf-8')
            struct.pack_into('<i',self.raw,start+self.parts['LEN']['offset'],len(encoded))
            offset=start+self.parts['DATA']['offset'];self.raw[offset:offset+len(encoded)]=encoded
        if mutate:mutate(self.capture)
        replay=Replay(self.capture)
        def raw(loc):
            self.reads.append(loc)
            if loc.source=='UnrelatedCatalogue':return self.raw[loc.offset:loc.offset+loc.width]
            if loc.path=='Press/Status/ConfigRev':
                self.epoch_reads+=1
                return struct.pack('<i',2 if self.change_epoch and self.epoch_reads>1 else 1)
            return replay.raw(loc)
        def counter(symbol):
            if symbol.endswith('CanonicalGeneration'):
                value=self.progress;self.progress+=2;return value
            return 2
        self.subject=live.CanonicalRowReader(self.capture,live.LeafBody(raw),counter,
                                            clock_ns=self.clock,sleep=self.clock.sleep)
        return self.subject

    def test_native_names_widths_and_sparse_numbers_govern_and_cache_is_immutable(self):
        subject=self.build();keys=subject.command_keys('Press')
        self.assertEqual(dict(keys),{s:n for n,s in self.entries})
        self.assertEqual(sum(loc.source=='UnrelatedCatalogue' for loc in self.reads),6)
        count=len(self.reads)
        self.assertIs(subject.command_keys('Press'),keys)
        self.assertEqual(len(self.reads),count)
        with self.assertRaises(TypeError):keys['invented']=1

    def test_more_than_one_packet_group_uses_only_the_published_count(self):
        self.entries=[(1000+i,'std.fixture.key'+str(i)) for i in range(65)]
        subject=self.build();self.assertEqual(len(subject.command_keys('Press')),65)
        calls=[loc for loc in self.reads if loc.source=='UnrelatedCatalogue']
        self.assertEqual(len(calls),130)
        self.assertFalse(any('[65]' in loc.symbol for loc in calls))

    def test_duplicate_numbers_or_text_and_empty_slots_refuse(self):
        for entries in ([(1,'one'),(1,'two')],[(1,'one'),(2,'one')],[(0,'')]):
            with self.subTest(entries=entries):
                self.setUp();self.entries=entries
                with self.assertRaises(ValueError):self.build().command_keys('Press')

    def test_bad_string_never_caches_a_partial_table(self):
        subject=self.build();saved=bytes(self.raw)
        offset=self.fields['PortableKey']['offset']+self.parts['LEN']['offset']
        struct.pack_into('<i',self.raw,offset,10000)
        with self.assertRaises(ValueError):subject.command_keys('Press')
        self.raw[:]=saved
        self.assertEqual(dict(subject.command_keys('Press')),{s:n for n,s in self.entries})

    def test_changed_revision_refuses_and_requires_a_fresh_acquisition(self):
        subject=self.build();self.change_epoch=True
        with self.assertRaisesRegex(ValueError,'crossed a root revision'):subject.command_keys('Press')
        first=len(self.reads);self.change_epoch=False;self.epoch_reads=0
        self.assertEqual(len(subject.command_keys('Press')),3)
        self.assertGreater(len(self.reads),first)

    def test_unknown_root_and_invalid_side_table_shape_refuse_before_body_reads(self):
        subject=self.build()
        with self.assertRaises(ValueError):subject.command_keys('Other')
        self.assertEqual(self.reads,[])
        for change in ('array','number','overlap'):
            self.setUp()
            def mutate(c):
                if change=='array':
                    next(s for s in c['symbols'] if s['name']=='UnrelatedCatalogue')['arrayRank']=0
                else:
                    row=next(t for t in c['templates'] if t['handle']==self.handle)['members'][0]
                    row.update(code=0xc1 if change=='number' else row['code'],offset=4 if change=='overlap' else row['offset'])
            with self.subTest(change=change),self.assertRaises(ValueError):self.build(mutate=mutate).command_keys('Press')
            self.assertEqual(self.reads,[])


if __name__=='__main__':unittest.main()
