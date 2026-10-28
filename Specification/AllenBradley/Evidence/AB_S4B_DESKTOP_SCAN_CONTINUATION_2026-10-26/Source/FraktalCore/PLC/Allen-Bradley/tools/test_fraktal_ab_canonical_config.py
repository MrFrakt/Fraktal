"""Execute the emitted S3f services against independent configuration owners."""
from copy import deepcopy
import unittest
from unittest.mock import patch

import fraktal_ab_access as access
import fraktal_ab_canonical_config as config
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_status as timestamp
import fraktal_ab_config_provider as provider
import fraktal_ab_data_access as data
import fraktal_ab_genealogy_s3f_demo as demo
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_manifest as manifest
import fraktal_ab_models as models
import fraktal_ab_projection as oracle
import fraktal_ab_sets as sets
import fraktal_ab_st_model as st


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.app=app=demo.application();self.schema=schema=pub.schema(app)
        def value(kind,initial=None):
            if kind.startswith(pub.PREFIX+'String'):
                raw=(initial or '').encode('utf-8');return dict(LEN=len(raw),DATA=list(raw)+[0]*(pub.string_width(kind)-len(raw)))
            if kind=='BOOL':return bool(initial)
            if kind not in schema:return initial or 0
            initial=initial or {}
            return {m.name:([value(m.kind,x) for x in initial.get(m.name,[None]*m.count)] if m.count
                else value(m.kind,initial.get(m.name))) for m in schema[kind]}
        self.value=value
        tags={app.name:value(pub.root_type(app),pub.initial(app)),pub.header_tag(app):dict(Valid=1),
              config.state_tag(app):value(config.WORK),provider.state_tag(app):value(provider.WORK),
              provider.staged_tag(app):value(provider.INPUT),provider.ack_tag(app):value(provider.ACK),
              config.query_status_tag(app):value(config.QUERY_STATUS),timestamp.work_tag(app):value(timestamp.WORK),
              'S:FS':False,'FRK_Press_Unit':dict(ModelOrdinal=1),'FRK_Press_NowDate':20261022,'FRK_Press_NowTime':123456789}
        for record in app.records:tags[record.name+'Tag']=st.structure(record.members)
        self.records={r.name:tags[r.name+'Tag'] for r in app.records}
        tags[gen.model_cfg_tag(app)]=[st.structure(m) for m in gen.model_cfg_elements(app)]
        tags[models.tag(app)]=dict(Count=len(app.models))
        tags[gen.config_persist_tag(app)]=st.structure(gen.config_persist_members())
        tags[sets.state_tag(app)]=st.structure(sets.state_members(app))
        tags[sets.staged_tag(app)]=st.structure(sets.request_members())
        tags[request:=mailbox.request_tag_name(app)]={'ConfigProvider':value(provider.INPUT),'Sequence':0,'IntValue':0,'DurationMs':0}
        tags[mailbox.response_tag_name(app)]=dict(AckSequence=0)
        tags[access.tag(app,'State')]=st.structure(access.state_members(app))
        self.authority=tags[access.tag(app,'State')]
        self.authority.update(CurrentLevel=4,UserLength=5,LoginResultSequence=23)
        tags[data.tag(app,'Levels')]=st.structure(data.levels_members(app))
        self.levels=tags[data.tag(app,'Levels')];self.levels['Count']=len(gen.editable_values(app))
        self.levels['Readable']=[1]*len(self.levels['Readable'])
        self.boot=10000000
        def gsv(plc,args):plc.write(args[3],self.boot)
        class TypedBoolController(st.Controller):
            # The shared integer-only model predates native BOOL storage.
            # Preserve the declared Boolean cells instead of treating them
            # as DINTs. Native compilation checks the expression types.
            def write(self,ref,value):
                holder,key=self._container(ref)
                if type(holder[key]) is bool:holder[key]=bool(value)
                else:super().write(ref,value)
        self.controller=TypedBoolController(tags,calls={'CPS':st.cps_structure,'GSV':gsv},routines=dict(gen.canonical_routines(app)))
        self.root=tags[app.name];self.work=tags[config.state_tag(app)]

    def execute(self,lines):
        # Calendar LINT is separately compiler/native tested. The small model
        # has one arithmetic width, so use its existing 64-bit test mode.
        with patch.object(st,'_wrap',lambda x:(x+(1<<63))%(1<<64)-(1<<63)):
            self.controller.run('\n'.join(lines))

    def scan(self):self.execute(config.cyclic(self.app))

    def query(self,index=0,model=0):
        self.work.update(PageIndex=index,ModelIndex=model,PageBuilt=0)
        self.scan()

    @staticmethod
    def text(value):return bytes(b&255 for b in value['DATA'][:value['LEN']]).decode('utf-8')

    def entries(self):
        page=self.root['HmiResponse']['ConfigPage'];result=[]
        for row in page['Entries'][:page['EntryCount']]:
            result.append({m.name:self.text(row[m.name]) if m.kind.startswith(pub.PREFIX+'String') else
                bool(row[m.name]) if m.kind=='BOOL' else float(row[m.name]) if m.kind=='LREAL' else row[m.name]
                for m in self.schema[config.ENTRY]})
        return result

    def expected(self,model=0):
        expected=oracle.config_page(self.app,manifest.content(self.app),self.records,
            self.controller.tags[gen.model_cfg_tag(self.app)],model,self.levels)
        result=[]
        for i in range(1,31):
            prefix=f'HmiResponse/ConfigPage/Entries[{i}]/'
            row={p[len(prefix):]:v for p,v in expected.items() if p.startswith(prefix)}
            for name in ('Minimum','Maximum'):row[name]=float(row[name])
            result.append(row)
        return result

    def test_retained_restart_seed_cannot_return_the_previous_token(self):
        self.scan();self.controller.tags['S:FS']=True
        for choose in (lambda old:old-1,lambda old:old,lambda old:0,lambda old:2147483646):
            before=self.work['Revision'];self.boot=choose(before);self.scan()
            self.assertNotEqual(self.work['Revision'],before)
            self.assertTrue(1<=self.work['Revision']<=2147483646)
            self.assertEqual(self.root['Status']['ConfigRev'],self.root['HmiResponse']['ConfigPage']['Revision'])

    def test_bounded_pages_equal_all_independent_oracle_entries_once(self):
        expected=self.expected();all_rows=[]
        for index,count in ((0,16),(1,14),(2,0),(32767,0)):
            self.query(index);page=self.root['HmiResponse']['ConfigPage']
            self.assertEqual((page['PageCount'],page['PageIndex'],page['EntryCount']),(2,index,count))
            rows=self.entries();self.assertEqual(rows,expected[index*16:(index+1)*16]);all_rows.extend(rows)
        self.assertEqual(all_rows,expected)
        self.assertEqual(len({r['WriteKey'] for r in all_rows}),30)

    def test_model_bank_and_live_values_do_not_get_mixed(self):
        bank=self.controller.tags[gen.model_cfg_tag(self.app)]
        bank[1]['PressDwellMs']=913;self.query(0,2)
        self.assertEqual(self.entries(),self.expected(2)[:16])
        self.query(0,0);self.assertEqual(self.entries(),self.expected(0)[:16])

    def test_hidden_values_have_levels_metadata_and_no_value_text(self):
        self.levels['Readable'][4]=0;self.levels['ReadLevel'][4]=3;self.levels['WriteLevel'][4]=4
        self.query();self.assertEqual(self.entries(),self.expected()[:16])
        self.assertEqual(self.entries()[4]['ValueText'],'')

    def test_revision_changes_on_values_bank_access_model_and_restart(self):
        self.scan();old=self.work['Revision'];self.scan();self.assertEqual(self.work['Revision'],old)
        for change in (lambda:self.records['FRK_T_PressStationCfg'].__setitem__('StationNumber',73),
                       lambda:self.controller.tags[gen.model_cfg_tag(self.app)][2].__setitem__('PressDwellMs',777),
                       lambda:self.levels['Readable'].__setitem__(1,0),
                       lambda:self.controller.tags['FRK_Press_Unit'].__setitem__('ModelOrdinal',2)):
            change();self.scan();new=self.work['Revision'];self.assertNotEqual(new,old);old=new
            self.assertEqual(self.root['HmiResponse']['ConfigPage']['Revision'],new)
        self.controller.tags['S:FS']=True;self.boot+=1;self.scan();self.assertNotEqual(old,self.work['Revision'])

    def test_pending_timestamp_uses_date_and_preserves_ms(self):
        self.work.update(PendingDate=20261021,PendingClock=123456789);self.scan();first=self.root['ConfigPersist']['PendingSince']
        self.work['PendingDate']=20261022;self.scan();second=self.root['ConfigPersist']['PendingSince']
        self.assertEqual(second-first,86400*1000000000)
        self.assertEqual(second%1000000000,789000000)

    def test_invalid_model_and_empty_tail_do_not_expose_stale_rows(self):
        self.query(0,0);self.assertEqual(len(self.entries()),16)
        self.query(0,999);self.assertEqual(self.entries(),[])
        self.query(1,0);self.assertEqual(len(self.entries()),14)

    def test_complete_generator_routes_the_new_native_query_and_provider(self):
        import xml.etree.ElementTree as ET
        programs=gen.programs(self.app)
        tree=ET.fromstring(programs)
        names={node.attrib['Name'] for node in tree.findall('.//Routine')}
        self.assertIn(config.page_routine(self.app),names)
        self.assertIn(provider.routine_name(self.app),names)
        self.assertIn(provider.validate_text_routine(self.app),names)
        self.assertIn('ConfigProvider', ''.join(mailbox.data_types(self.app)))

    def test_reference_pager_and_types_equal_publication_at_each_window(self):
        import fraktal_ab_s3f_equivalence as contract
        for index,count in ((0,2617),(1,2567),(2,2217)):
            self.query(index)
            additional=dict(query=self.controller.tags[config.query_status_tag(self.app)],
                sets=self.controller.tags[sets.state_tag(self.app)],records=self.records,
                models=self.controller.tags[gen.model_cfg_tag(self.app)],levels=self.levels,
                persist=self.controller.tags[gen.config_persist_tag(self.app)])
            additional['query']['SchemaVersion']=1
            expected=contract.reference_config(self.app,additional,page=index)
            self.assertEqual(expected['Press/HmiResponse/ConfigPage/EntryCount'],len(self.entries()))
            self.assertEqual(len(contract.subset_paths(self.app,[m.code for m in self.app.models],canonical=True,page=index)),count)
            for i,row in enumerate(self.entries(),1):
                for k,v in row.items():self.assertEqual(expected[f'Press/HmiResponse/ConfigPage/Entries[{i}]/{k}'],v)
            types=contract.logical_types(self.app,set(expected))
            self.assertEqual(types['Press/ConfigSets[1]/SetSchema'],'UInt16')
            self.assertEqual(types['Press/HmiResponse/ConfigPage/EntryCount'],'Int16')


class ProviderTests(unittest.TestCase):
    execute=ConfigurationTests.execute
    text=staticmethod(ConfigurationTests.text)

    def setUp(self):
        ConfigurationTests.setUp(self);self.sequence=0;self.request_sequence=19
        self.controller.tags[sets.state_tag(self.app)]['Sequence']=19
        self.controller.tags[sets.staged_tag(self.app)]['Operation']=mailbox.LIST_CONFIG_SETS
        self.controller.tags[mailbox.response_tag_name(self.app)]['AckSequence']=19

    def packet(self,**overrides):
        self.sequence+=1
        arguments=dict(sequence=self.sequence,request_sequence=self.request_sequence,login_sequence=23,
            build_revision=manifest.config_revision(self.app),operation=mailbox.LIST_CONFIG_SETS,
            headers=[dict(set='one',root='Press',kind=1,model='',records=5,configRev=12,schema=1,created=0xffffffff,clock=0)])
        arguments.update(overrides);return provider.payload(**arguments)

    def deliver(self,packet):
        self.controller.tags[mailbox.request_tag_name(self.app)]['ConfigProvider']=deepcopy(packet)
        self.execute(provider.logic(self.app));return self.controller.tags[provider.ack_tag(self.app)]

    def test_nonempty_catalog_utf8_unsigned_epoch_and_empty_replacement(self):
        packet=self.packet();self.assertEqual(self.deliver(packet)['Accepted'],1)
        row=self.root['ConfigSets'][0]
        self.assertTrue(row['Used']);self.assertEqual(self.text(row['SetName']),'one')
        self.assertEqual(row['CreatedAt'],0xffffffff*1000000000)
        packet=self.packet(headers=[]);self.assertEqual(self.deliver(packet)['Accepted'],1)
        self.assertEqual(self.root['ConfigSetCount'],0);self.assertFalse(self.root['ConfigSets'][0]['Used'])

    def test_bad_session_request_build_and_replay_cannot_mutate_publication(self):
        self.assertEqual(self.deliver(self.packet())['Accepted'],1);before=deepcopy(self.root)
        for field,bad in (('RequestSequence',17),('LoginSequence',22),('BuildRevision',42),('Sequence',-1)):
            packet=self.packet();packet[field]=bad
            self.assertEqual(self.deliver(packet)['Accepted'],0);self.assertEqual(self.root,before)
        packet=self.packet();self.deliver(packet);new=self.packet();self.deliver(new)
        self.assertEqual(self.deliver(packet)['Accepted'],0)

    def test_malformed_counts_lengths_utf8_and_header_ranges_do_not_fault_or_apply(self):
        for field,index,bad in (('Count',None,5),('Count',None,-1),('TextLength',0,-1),('TextLength',0,81),
                               ('SetSchema',0,65536),('RecordCount',0,65),('RecordKind',0,3)):
            packet=self.packet();before=deepcopy(self.root)
            if index is None:packet[field]=bad
            else:packet[field][index]=bad
            self.assertEqual(self.deliver(packet)['Accepted'],0,(field,bad));self.assertEqual(self.root,before)
        for raw in (b'\xc0\x80',b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\xe2\x82',b'\x00',b'\x80'):
            packet=self.packet();packet['TextLength'][0]=len(raw);packet['TextBytes'][:len(raw)]=raw
            self.assertEqual(self.deliver(packet)['Accepted'],0,raw)

    def test_anonymous_and_busy_sessions_are_rejected(self):
        for level,busy in ((0,0),(4,1)):
            self.authority.update(CurrentLevel=level,LoginBusy=busy)
            self.assertEqual(self.deliver(self.packet())['Accepted'],0)

    def test_document_and_reject_fields_are_published_without_erasing_catalog(self):
        self.deliver(self.packet());packet=self.packet(headers=None,document='{"set":"x"}',document_lines=3,
            reject_scope='Press',reject_key='station.number')
        self.assertEqual(self.deliver(packet)['Accepted'],1)
        self.assertEqual(self.root['ConfigSetCount'],1)
        self.assertEqual(self.text(self.root['ConfigSetDocument']),'{"set":"x"}')
        self.assertEqual(self.text(self.root['ConfigPersist']['LastRejectKey']),'station.number')


if __name__=='__main__':unittest.main()
