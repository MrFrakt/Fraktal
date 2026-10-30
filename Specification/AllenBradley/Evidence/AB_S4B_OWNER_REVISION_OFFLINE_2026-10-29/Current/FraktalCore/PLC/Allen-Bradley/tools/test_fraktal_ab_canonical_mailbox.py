"""Execute S3k response rendering against the independent legacy projection."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

import fraktal_ab_canonical_mailbox as publication
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_text as text
import fraktal_ab_genealogy_s3k_demo as demo
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_machine_state as machine
import fraktal_ab_projection as projection
import fraktal_ab_st_model as st
import fraktal_ab_s3k_equivalence as equivalence
import fraktal_ab_canonical_observation as observation
from test_fraktal_ab_canonical_commands import service_tags


def string():return dict(LEN=0,DATA=[0]*255)


def reason():return dict(Description=string(),ReasonCode=0,SourcePath=string(),Kind=0,Bypassable=0)


def decode_text(value):return bytes(b&255 for b in value['DATA'][:value['LEN']]).decode('utf-8')


class MailboxPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=demo.application();cls.keys=publication.catalogue(cls.app)
        cls.body=st.parse('\n'.join(publication.response_logic(cls.app)))
        cls.cyclic=st.parse('\n'.join(publication.cyclic(cls.app)))
        cls.tables=publication.tables(cls.app)
        cls.pool=text.model_tags(cls.app)
        cls.number=st.parse('\n'.join(publication.number_logic(cls.app)))

    def setUp(self):
        a=self.app
        self.root=dict(HmiRequest=dict(Sequence=0),HmiResponse=dict(AckSequence=0,Accepted=0,
            Diagnostic=string(),Report=dict(Released=0,Count=0,Reasons=[reason() for _ in range(24)])))
        self.root.update(GoodCount=0,NokCount=0,ReworkCount=0,Starved=0,Blocked=0)
        self.report=st.structure(gen.release_report_members(a))
        self.response=dict(AckSequence=1,Accepted=1,DiagnosticKey=0,Sequence=0,ResponseRevision=0,CoreSerial=0)
        self.unit=st.structure(gen.unit_context_members(a))
        self.work={n:0 for n in ('Initialized','ResponseValid','LastAck','Slot','Key','Index','Source',
                                'Number','Negative','Digit','DigitCount','Position','LastDiagnostic','LastAccepted','LastSequence')}
        self.work.update(Digits=[0]*10,Render=string())
        tags={a.name:self.root,publication.work_tag(a):self.work,
            publication.blank_tag(a):reason(),gen.release_report_tag(a):self.report,
            mailbox.response_tag_name(a):self.response,mailbox.request_tag_name(a):dict(Sequence=1),
            publication.input_tag(a):self.response,
            __import__('fraktal_ab_canonical_commands').work_tag(a):dict(OwnerSequence=1,OwnerAck=1,ResponseRevision=0,CoreSerial=0,NewCore=0,Index=0),
            f'FRK_{a.name}_Unit':self.unit,pub.header_tag(a):dict(Valid=True),**deepcopy(self.pool),
            # The cyclic block also publishes the set-service status (executed in its own suite).
            **service_tags(a,pub.schema(a))}
        tags.update({n:deepcopy(rows) for n,(base,rows) in self.tables.items()})
        self.plc=st.Controller(tags,calls={'CPS':st.cps_structure},routines={
            publication.routine(a):self.body,publication.number_routine(a):self.number})

    def test_all_24_reasons_and_cleared_tail_equal_the_legacy_reference(self):
        for count in (0,1,8,9,23,24,0):
            with self.subTest(count=count):
                self.report.update(Count=count,Released=int(count==0))
                for i,key in enumerate(sorted(self.keys)[:24]):
                    self.report['Key'][i]=key;self.report['Reason'][i]=10000+i
                    self.report['Source'][i]=i%(len(self.app.modules)+1);self.report['Kind'][i]=i%5
                self.response['AckSequence']+=1;self.plc.run(self.body)
                expected=projection.release_report_values(self.app,self.report,self.keys)
                actual=self.root['HmiResponse']['Report']
                self.assertEqual(actual['Count'],expected['HmiResponse/Report/Count'])
                self.assertEqual(actual['Released'],expected['HmiResponse/Report/Released'])
                for i,row in enumerate(actual['Reasons'],1):
                    base=f'HmiResponse/Report/Reasons/Reasons[{i}]'
                    for field,value in row.items():
                        if field in ('Description','SourcePath'):value=decode_text(value)
                        self.assertEqual(value,expected[base+'/'+field])
                self.assertEqual(self.plc.tags[pub.header_tag(self.app)]['Valid'],1)

    def test_diagnostic_known_empty_unknown_and_signed_minimum(self):
        for key in (0,1,max(self.keys),max(self.keys)+1,2147483647,-1,-2147483648):
            with self.subTest(key=key):
                self.response.update(DiagnosticKey=key,AckSequence=self.response['AckSequence']+1)
                self.plc.run(self.body)
                expected='' if key==0 else self.keys.get(key,f'{mailbox.UNKNOWN_KEY}#{key}')
                self.assertEqual(decode_text(self.root['HmiResponse']['Diagnostic']),expected)
                self.assertEqual(self.root['HmiResponse']['AckSequence'],self.response['AckSequence'])

    def test_report_is_cached_under_ack_and_ack_is_published_after_response(self):
        self.plc.run(self.body);before=deepcopy(self.root['HmiResponse'])
        self.report.update(Count=1,Released=0);self.report['Reason'][0]=1234
        self.plc.run(self.body);self.assertEqual(self.root['HmiResponse'],before)
        self.response['AckSequence']=-2147483648;self.plc.run(self.body)
        self.assertEqual(self.root['HmiResponse']['Report']['Reasons'][0]['ReasonCode'],1234)
        self.assertEqual(self.root['HmiResponse']['AckSequence'],-2147483648)
        code='\n'.join(publication.response_logic(self.app))
        self.assertGreater(code.index(f'{self.app.name}.HmiResponse.AckSequence :='),
                           code.index(f'{self.app.name}.HmiResponse.Report.Count :='))

    def test_incomplete_or_corrupt_report_never_becomes_a_valid_snapshot(self):
        for count,overflow in ((-1,0),(25,0),(24,1)):
            with self.subTest(count=count,overflow=overflow):
                self.report.update(Count=count,Overflow=overflow)
                self.plc.tags[pub.header_tag(self.app)]['Valid']=1
                self.plc.run(self.body)
                self.assertEqual(self.plc.tags[pub.header_tag(self.app)]['Valid'],0)
        self.report.update(Count=1,Overflow=0);self.report['Source'][0]=-1
        self.plc.tags[pub.header_tag(self.app)]['Valid']=1;self.plc.run(self.body)
        self.assertEqual(self.plc.tags[pub.header_tag(self.app)]['Valid'],0)
        self.report['Source'][0]=0;self.plc.tags[pub.header_tag(self.app)]['Valid']=1
        self.plc.run(self.body)
        self.assertEqual(self.plc.tags[pub.header_tag(self.app)]['Valid'],0)

    def test_counters_keep_every_uint32_bit_and_waits_are_derived_each_scan(self):
        for value in (0,1,2147483647,-2147483648,-1):
            self.unit.update(GoodCount=value,ScrapCount=value,ReworkCount=value)
            self.plc.run(self.cyclic)
            for field in ('GoodCount','NokCount','ReworkCount'):
                self.assertEqual(self.root[field]&0xffffffff,value&0xffffffff)
        for chain in self.app.chains:
            for step in chain.steps:
                for running,error in ((1,0),(0,0),(1,1)):
                    self.unit.update(Mode=chain.mode_ordinal,Step=step.number,Running=running,Error=error)
                    self.plc.run(self.cyclic)
                    self.assertEqual((bool(self.root['Starved']),bool(self.root['Blocked'])),machine.waits(self.app,self.unit))

    def test_exact_approved_133_path_inventory_and_native_types(self):
        root=Path(__file__).resolve().parents[4]
        inventory=json.loads((root/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json').read_bytes())
        expected={p for p,v in inventory['paths'].items() if v['stage']=='S3k'}
        self.assertEqual(equivalence.mailbox_paths(self.app,canonical=False),expected)
        self.assertEqual(len(expected),133)
        self.assertEqual(equivalence.mailbox_paths(self.app,canonical=True),
                         {inventory['paths'][p]['proposedCanonicalPath'] for p in expected})
        definitions=pub.schema(self.app)
        self.assertEqual(next(m.kind for m in definitions[publication.REPORT] if m.name=='Count'),'INT')
        reasons=next(m for m in definitions[publication.REPORT] if m.name=='Reasons')
        self.assertEqual((reasons.count,reasons.lower,reasons.count_path),(24,1,''))
        self.assertEqual(next(m.kind for m in definitions[publication.REASON] if m.name=='Bypassable'),'BOOL')

    def test_paired_sources_never_sample_the_credential_bearing_native_request(self):
        names=observation.legacy_sources(self.app)
        self.assertIn(publication.input_tag(self.app),names)
        self.assertIn(mailbox.response_tag_name(self.app),names)
        self.assertIn(gen.release_report_tag(self.app),names)
        self.assertNotIn(mailbox.request_tag_name(self.app),names)
        self.assertFalse(any('Secret' in n or '.Frame' in n for n in names))
        import fraktal_ab_canonical_commands as commands
        typed={commands.payload_tag(self.app),commands.sample_tag(self.app),commands.work_tag(self.app)}
        self.assertFalse(typed&(set(names)|set(observation.public_tags(self.app))))


if __name__=='__main__':unittest.main()
