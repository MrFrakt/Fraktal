"""Fixed, separately authorized S3f configuration/provider vectors on local Echo.

The inherited 31 regressions and two Access vectors retain their guards and
cleanup. Added writes use only the public mailbox, its appended provider frame
and the existing set staging. The named-set medium is a new isolated directory.
This apparatus is deliberately station-specific; the provider client is not.
"""
from copy import deepcopy
from pathlib import Path

import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_genealogy_s3f_demo as candidate
import fraktal_ab_canonical_publication as publication
import fraktal_ab_canonical_manifest as manifest_wire
import fraktal_ab_canonical_reader as reader
import fraktal_ab_config_provider as provider
import fraktal_ab_config_provider_wire as wire
import fraktal_ab_config_provider_client as client
import fraktal_ab_canonical_config as config
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as legacy
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_access as access
import fraktal_ab_set_broker as broker
import fraktal_ab_sets as sets
import fraktal_ab_s3a_fixture_execute as capture
import fraktal_ab_s3b_fixture_execute as observer
import fraktal_ab_s3e_fixture_execute as previous
import fraktal_ab_s3f_equivalence as equivalence

SAVE_NAME='s3f_station_snapshot'
IMPORT_NAME='s3f_station_import'
MISSING_NAME='s3f_absent_set'


def expected_manifest(app):
    return manifest_wire.content_hash(publication.field_rows(app),legacy.content_hash(app),app.canonical_publication_stage,
        minor=manifest_wire.SERVICE_MINOR,bindings=publication.publication_bindings(app),services=provider.services(app))


def provider_targets(app):
    prefix=provider.input_tag(app)
    return frozenset(f'{prefix}.{name}'+(f'[{offset}]' if count else '')
        for name,count in wire.layout() for offset in (range(0,count,80) if count else (0,)))


def import_pieces(document):
    """Use the existing bounded line/piece protocol; never invent a second load."""
    for i,row in enumerate(document):
        line=sets.render_line(row)
        for offset in range(0,len(line),255):
            final=offset+255>=len(line)
            yield dict(TextValue=line[offset:offset+255],IntValue=int(not final),
                BoolValue=final and i==len(document)-1)


def paired_run(destination,*,candidate_factory=None,equivalence_gate=None,prefix='s3f'):
    state=dict(page=0,model=0,provider_state={})
    selected=equivalence.run if equivalence_gate is None else equivalence_gate
    selected_factory=candidate.application if candidate_factory is None else candidate_factory
    def gate(comm):return selected(comm,**state)
    parent=previous.paired_run(destination,gate=gate,prefix=prefix)

    class ConfigRun(parent):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.candidate=selected_factory()
            _,self.provider_capture=reader.read_document(self.comm,expect_serial=self.evidence['serial'])
            self.check(self.provider_capture['manifest']['contentHash']==expected_manifest(self.candidate),
                       f'exact {prefix[0].upper()+prefix[1:]} publication required before fixture writes')
            # A fixed, versioned extension of the inherited apparatus allow-list.
            self.comm.allowed=self.comm.allowed|provider_targets(self.candidate)
            self.provider_state=state['provider_state']
            self.store_session=sets.Session()

        def config_pair(self,phase):
            return capture.capture_pair(self,destination,lambda comm:observer.capture_gate(comm,gate),
                key=prefix+'ConfigPairs',kind='configuration',metadata=dict(phase=phase,page=state['page'],model=state['model']))

        def config_row(self,case,**details):
            self.evidence.setdefault(prefix+'ConfigRows',[]).append(dict(case=case,passed=True,**details))

        def command(self,kind,**arguments):
            answer=super().command(kind,**arguments)
            if (kind==mb.SET_ACCESS_LEVEL and arguments.get('IntValue')==access.GATES[mb.MANUAL_COMMAND]
                    and not self.evidence.get('error')):
                self.config_pair('manual_policy_observed')
            return answer

        def query_page(self,page=0,model=0):
            answer=self.command(mb.QUERY_CONFIG,IntValue=page,DurationMs=model)
            state.update(page=page,model=model)
            symbol=next(s for s in self.provider_capture['symbols'] if s['name']==config.query_status_tag(self.candidate))
            def settled():
                raw=self.comm.Read(symbol['name'])
                if raw.Status!='Success':return None
                reply=reader.decode_record(bytes(raw.Value),symbol['handle'],self.provider_capture['templates'])
                return reply if reply['AckSequence']&0xffffffff==answer['sequence'] and reply['Accepted']==1 else None
            self.wait(settled,'query acknowledgement')
            return self.config_pair('query_page')

        def restore_configuration(self):
            super().restore_configuration()
            if not self.evidence.get('error') and not getattr(self,'_s3f_vectors_started',False):
                self._s3f_vectors_started=True
                self.page_vectors()
                self.store_vectors()

        def page_vectors(self):
            first=self.query_page();second=self.query_page(1)
            def keys(report):
                values=report['pair']['canonical']['values'];base=self.app.name+'/HmiResponse/ConfigPage/'
                count=values[base+'EntryCount']
                return [values[base+f'Entries[{i}]/WriteKey'] for i in range(1,count+1)]
            wanted=[m.write_key for _,_,m in gen.editable_values(self.candidate)]
            self.check(keys(first)+keys(second)==wanted and len(set(wanted))==len(wanted),'page walk must enumerate all ordered keys once')
            self.query_page(2);self.query_page(0,2);initial=self.query_page()
            self.config_row('page_walk_and_model_bank',entries=len(wanted),pageEntries=[16,14,0],queriedModel=2)
            # One ordinary station parameter; the exact original always returns.
            ordinal,record,member=next(v for v in gen.editable_values(self.candidate)
                if v[1].station_cfg and v[2].kind!='boolean' and v[2].minimum<v[2].maximum)
            original=execute.read_scalar(self.comm,record.name+'Tag.'+member.name)
            self.check(type(original) is int,'configuration fixture original unavailable')
            temporary=original+1 if original<member.maximum else original-1
            revision=initial['pair']['canonical']['values'][self.app.name+'/Status/ConfigRev']
            try:
                self.command(mb.WRITE_CONFIG,**{mb.CONFIG_ORDINAL_MEMBER:ordinal,mb.CONFIG_VALUE_MEMBER:temporary})
                changed=self.query_page()
                self.check(changed['pair']['canonical']['values'][self.app.name+'/Status/ConfigRev']!=revision,'accepted edit must change revision')
            finally:
                super().command(mb.WRITE_CONFIG,**{mb.CONFIG_ORDINAL_MEMBER:ordinal,mb.CONFIG_VALUE_MEMBER:original})
                self.check(execute.read_scalar(self.comm,record.name+'Tag.'+member.name)==original,'configuration edit not restored')
            self.query_page();self.config_row('edit_revision_and_exact_restoration',ordinal=ordinal)
            # Raise one existing class, log out, and prove its values disappear.
            policy=projection.read_data_access(self.comm,policy=True)
            index=len(self.app.data_classes)-1;identity=self.app.data_classes[index].class_id
            original=policy['ReadLevel'][index]
            try:
                self.command(mb.SET_CLASS_LEVEL,NameValue=identity,IntValue=4,BoolValue=False)
                self.command(mb.LOGOUT)
                reports=[self.query_page(0),self.query_page(1)]
                hidden=0
                for report in reports:
                    values=report['pair']['canonical']['values']
                    for p,v in values.items():
                        if p.endswith('/Readable') and '/ConfigPage/Entries[' in p and not v:
                            self.check(values[p.removesuffix('Readable')+'ValueText']=='','hidden config value leaked')
                            hidden+=1
                self.check(hidden>0,'class fixture did not hide a value')
            finally:
                # Parent login skips additional config vectors. Observation errors
                # must never prevent this policy restoration.
                super().login()
                super().command(mb.SET_CLASS_LEVEL,NameValue=identity,IntValue=original,BoolValue=False)
                self.check(projection.read_data_access(self.comm,policy=True)==policy,'hidden-value policy not restored')
            self.query_page();self.config_row('hidden_values_and_policy_restoration',hiddenEntries=hidden)

        def store_command(self,kind,*,accepted=True,observe=True,**arguments):
            from fraktal_ab_gateway import MailboxWriter
            serial=self.evidence['serial'];app=self.candidate
            writer=MailboxWriter('127.0.0.1',0,serial,app=app,set_store=self.fixture_store)
            previous_seq=execute.seed_sequence(self.comm)
            ack=execute.read_scalar(self.comm,mb.response_tag_name(app)+'.AckSequence')
            self.check(ack is not None and ack&0xffffffff==previous_seq,'set mailbox unsettled')
            sequence=(previous_seq+1)&0xffffffff
            types={'IntValue':'int32','BoolValue':'boolean','TextValue':'string'}
            root=app.name+'/HmiRequest/'
            writes=[(root+'Kind','int32',kind)]+[(root+n,types[n],v) for n,v in arguments.items()]+[(root+'Sequence','uint32',sequence)]
            ok=broker.process(self.comm,app,self.fixture_store,self.store_session,writes,writer._write_base,expect_serial=serial)
            self.check(ok,'store transaction delivery failed')
            response=broker.wait_response(self.comm,app,sequence)
            self.check(bool(response['Accepted']) is accepted,'unexpected native store acceptance/refusal')
            values=self.store_session.values;base=app.name+'/'
            if kind==mb.LIST_CONFIG_SETS and accepted:self.provider_state['headers']=deepcopy(self.fixture_store.list())
            if kind in (mb.LIST_CONFIG_SETS,mb.EXPORT_CONFIG_SET,mb.EXPORT_CURRENT_CONFIG):
                for target,key in [('document','ConfigSetDocument'),('documentLine','ConfigSetDocumentLine'),('documentLines','ConfigSetDocumentLines')]:
                    self.provider_state[target]=values.get(base+key,'' if target=='document' else 0)
            for target,key in [('rejectScope','LastRejectScope'),('rejectKey','LastRejectKey')]:
                self.provider_state[target]=values.get(base+'ConfigPersist/'+key,'')
            if kind==mb.SAVE_CONFIG_SET and accepted:
                native=broker.read_state(self.comm,app);i=native['Head']-1
                self.provider_state.update(pendingSequence=native['PendingSequence'],pendingDate=native['AuditDate'][i],pendingClock=native['AuditClock'][i])
            if observe:return self.config_pair('store_'+str(kind))

        def refused_provider_vectors(self):
            service,answer=client.binding(self.provider_capture)
            access=projection.read_access(self.comm)
            parent_state=broker.read_state(self.comm,self.candidate)
            for case,mutate in (
                ('stale_parent',lambda p:p.update(RequestSequence=p['RequestSequence']-1)),
                ('stale_login',lambda p:p.update(LoginSequence=p['LoginSequence']-1)),
                ('catalog_overflow',lambda p:p.update(Flags=wire.CATALOG,Count=wire.MAX_SETS+1)),
                ('invalid_utf8',lambda p:(p['TextLength'].__setitem__(wire.MAX_SETS*3+2,2),
                    p['TextBytes'].__setitem__(slice(wire.OFFSETS[-1],wire.OFFSETS[-1]+2),[0xC0,0x80])))):
                raw=self.comm.Read(service['ResponseSymbol'])
                self.check(raw.Status=='Success','provider ack unavailable')
                prior=reader.decode_record(bytes(raw.Value),answer['handle'],self.provider_capture['templates'])
                seq=prior['AckSequence']%2147483646+1
                packet=wire.payload(sequence=seq,request_sequence=parent_state['Sequence'],
                    login_sequence=access['LoginResultSequence']&0xffffffff,build_revision=service['BuildRevision'],operation=mb.LIST_CONFIG_SETS)
                mutate(packet)
                for tag,value in client.write_plan(service,packet):self.comm.Write(tag,value)
                def refused():
                    raw=self.comm.Read(service['ResponseSymbol'])
                    if raw.Status!='Success':return None
                    response=reader.decode_record(bytes(raw.Value),answer['handle'],self.provider_capture['templates'])
                    return response if response['AckSequence']==seq else None
                response=self.wait(refused,'provider refusal')
                self.check(response['Accepted']==0 and response['ErrorCode']!=0,'invalid response must be refused')
                self.config_pair(case);self.config_row('provider_'+case+'_refused')

        def store_vectors(self):
            directory=destination.with_name(destination.stem+'_isolated_sets')
            self.check(not directory.exists(),'isolated set directory already exists')
            directory.mkdir()
            self.fixture_store=sets.FileStore(directory)
            self.evidence['s3fSetMedium']=str(directory)
            # Exact live ParCfg snapshot: LOAD below must leave all values equal.
            before={r.name:execute.read_flat(self.comm,r.name+'Tag',tuple(m.name for m in r.members)) for r in self.app.records}
            self.check(all(v is not None for v in before.values()),'configuration snapshot unavailable')
            try:
                self.store_command(mb.LIST_CONFIG_SETS)
                self.store_command(mb.SAVE_CONFIG_SET,TextValue=SAVE_NAME,IntValue=1)
                saved=self.fixture_store.read(SAVE_NAME)
                self.evidence['s3fSavedDocument']=deepcopy(saved)
                self.check(saved[0]['records']==len(saved)-1,'saved document count mismatch')
                self.store_command(mb.LIST_CONFIG_SETS)
                for line in range(len(saved)):
                    self.store_command(mb.EXPORT_CONFIG_SET,TextValue=SAVE_NAME,IntValue=line)
                    self.check(self.provider_state['document']==sets.render_line(saved[line]),'export line mismatch')
                imported=deepcopy(saved);imported[0]['set']=IMPORT_NAME
                self.evidence['s3fImportedDocument']=deepcopy(imported)
                for arguments in import_pieces(imported):self.store_command(mb.IMPORT_CONFIG_SET,observe=False,**arguments)
                self.config_pair('import_committed')
                self.check(self.fixture_store.read(IMPORT_NAME)==imported,'import did not preserve complete document')
                self.store_command(mb.LIST_CONFIG_SETS)
                self.store_command(mb.LOAD_CONFIG_SET,TextValue=SAVE_NAME)
                after={r.name:execute.read_flat(self.comm,r.name+'Tag',tuple(m.name for m in r.members)) for r in self.app.records}
                self.check(after==before,'snapshot LOAD changed live values')
                self.store_command(mb.EXPORT_CONFIG_SET,TextValue=MISSING_NAME,IntValue=0,accepted=False)
                self.check(self.provider_state['rejectKey']==MISSING_NAME,'refusal must retain rejected identity')
                self.store_command(mb.DELETE_CONFIG_SET,TextValue=SAVE_NAME)
                self.store_command(mb.DELETE_CONFIG_SET,TextValue=IMPORT_NAME)
                self.store_command(mb.LIST_CONFIG_SETS)
                self.refused_provider_vectors()
                self.config_row('store_save_list_export_import_load_delete',records=len(saved)-1,exportedLines=len(saved))
            finally:
                # The only deletions are these two fixed names in our new store.
                # Keep failed evidence and leave the empty directory in place.
                for name in (SAVE_NAME,IMPORT_NAME):
                    if any(h['set']==name for h in self.fixture_store.list()):
                        self.store_command(mb.DELETE_CONFIG_SET,TextValue=name,observe=False)
                self.store_command(mb.LIST_CONFIG_SETS,observe=False)
                self.evidence['s3fSetMediumEmpty']=not self.fixture_store.list()
            self.query_page()
    return ConfigRun


def main(argv=None):return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3f-genealogy-fixture')
if __name__=='__main__':raise SystemExit(main())
