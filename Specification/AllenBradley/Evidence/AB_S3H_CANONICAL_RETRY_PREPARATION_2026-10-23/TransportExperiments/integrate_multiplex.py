from pathlib import Path
W=Path(__file__).parent;T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
for source,target in (('socket_reads.py','fraktal_ab_paired_socket_reads.py'),('test_socket_reads.py','test_fraktal_ab_paired_socket_reads.py')):
    text=(W/source).read_text().replace('import socket_reads as reads','import fraktal_ab_paired_socket_reads as reads')
    with (T/target).open('x') as f:f.write(text)
p=T/'fraktal_ab_s2_equivalence.py';text=p.read_text()
needle='                secondary_comm=None, secondary_tags=(), fragment_large=False, extra_comms=()):'
assert text.count(needle)==1
text=text.replace(needle,'                secondary_comm=None, secondary_tags=(), fragment_large=False, extra_comms=(), socket_reads=False):',1)
needle='''        if secondary_plan:
            from concurrent.futures import ThreadPoolExecutor'''
assert text.count(needle)==1
text=text.replace(needle,'''        if secondary_plan and socket_reads:
            import fraktal_ab_paired_socket_reads as sockets
            if not fragment_large or len(channels)!=4:
                raise ValueError('socket multiplex requires four fragmented read owners')
            def acquire():
                return dict(rawBatches=[reply for group in sockets.acquire(channels,plans) for reply in group])
            pair=stable_scan_pair(generation,acquire)
            read_plan=[item for p in plans for item in p]
            pair['readConnections']=len(channels)
            pair['readTransport']='one outstanding read per socket; single multiplex owner'
        elif secondary_plan:
            from concurrent.futures import ThreadPoolExecutor''',1)
needle='                             fragment_large=app.canonical_publication_stage>=8,extra_comms=observations[1:])'
assert text.count(needle)==1
text=text.replace(needle,'                             fragment_large=app.canonical_publication_stage>=8,extra_comms=observations[1:],\n                             socket_reads=app.canonical_publication_stage>=10)',1)
p.write_text(text)
# Keep the pre-existing ASCII assertion in its owning test after the callback
# regressions were inserted; no assertion or coverage is removed.
p=T/'test_fraktal_ab_s3h_traceability.py';text=p.read_text()
block="        self.raw_part.update(DataRevision=4,RecordCount=0)\n        self.raw_part['Uid'][:4]=[65,0,66,0]\n        self.scan();self.assertIs(self.plc.tags[pub.header_tag(self.app)]['Valid'],False)\n"
assert text.count(block)==1;text=text.replace(block,'',1)
needle='    def test_stage_path_callback_accepts_boolean_selector_and_independent_ring_count(self):'
assert text.count(needle)==1;text=text.replace(needle,block+'\n'+needle,1)
p.write_text(text)
print('Only the migration observer transport changed; PLC generator and generic reader unchanged')
