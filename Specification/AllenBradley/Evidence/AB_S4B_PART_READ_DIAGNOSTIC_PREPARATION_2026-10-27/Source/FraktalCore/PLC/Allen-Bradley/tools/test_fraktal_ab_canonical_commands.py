"""Execute the generated typed/legacy ingress against adversarial ordering."""
from copy import deepcopy
import unittest
import fraktal_ab_canonical_commands as command
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_text as text
import fraktal_ab_genealogy_s3k_demo as demo
import fraktal_ab_mailbox as mailbox
import fraktal_ab_mailbox_frame as frame
import fraktal_ab_st_model as st


def initial(definitions,kind):
    """A zeroed instance of a generated type, as a download leaves it."""
    if kind=='BOOL':return False
    if kind.startswith(pub.PREFIX+'String'):
        return dict(LEN=0,DATA=[0]*pub.string_width(kind))
    if kind in definitions:
        return {m.name:([deepcopy(initial(definitions,m.kind)) for _ in range(m.count)] if m.count else initial(definitions,m.kind))
                for m in definitions[kind]}
    return 0


class IngressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=demo.application();cls.definitions=pub.schema(cls.app)
        cls.ingress=st.parse('\n'.join(command.ingress(cls.app)))
        cls.after=st.parse('\n'.join(command.after_owner(cls.app)))
        cls.routines=dict(command.routines(cls.app))
        cls.pool=text.model_tags(cls.app)

    @classmethod
    def value(cls,kind):return initial(cls.definitions,kind)

    def setUp(self):
        a=self.app
        self.work=self.value(command.WORK);self.work['Armed']=1
        self.payload=self.value(command.PAYLOAD);self.sample=self.value(command.PAYLOAD)
        self.request={n:(dict(LEN=0,DATA=[0]*width) if kind==mailbox.STRING_MEMBER else 0)
                      for n,kind,width,note in mailbox.REQUEST_MEMBERS}
        self.request['Frame']=dict(Words=[0]*frame.word_count(a))
        self.response=dict(AckSequence=0,Accepted=0,DiagnosticKey=0)
        self.tags={'S:FS':False,command.work_tag(a):self.work,command.payload_tag(a):self.payload,
            command.sample_tag(a):self.sample,command.commit_tag(a):0,
            command.route_tag(a):command.rows(a),mailbox.request_tag_name(a):self.request,
            mailbox.response_tag_name(a):self.response,frame.sample_tag(a):dict(Words=[0]*frame.word_count(a)),
            pub.header_tag(a):dict(ConfigRevision=7),a.name:dict(Status=dict(ConfigRev=123)),
            f'FRK_{a.name}_HmiLastSequence':0,f'FRK_{a.name}_HmiWipe':0,**deepcopy(self.pool)}
        self.tags.update({f'FRK_{a.name}_HmiFrame{n}':0 for n in ('Cursor','Word','Byte','Valid','Field')})
        self.plc=st.Controller(self.tags,calls={'CPS':st.cps_structure},routines=self.routines)

    def stage(self,sequence,**arguments):
        self.payload.update(SchemaVersion=1,ManifestRevision=7,StagedSequence=sequence)
        for n,v in arguments.items():
            if isinstance(v,str):
                target=self.payload['Arguments'][n];raw=v.encode()
                target['LEN']=len(raw);target['DATA'][:len(raw)]=raw
            else:self.payload['Arguments'][n]=v
        self.tags[command.commit_tag(self.app)]=sequence

    def test_typed_snapshot_keeps_legacy_commit_and_ack_independent_and_wipes_full_width(self):
        self.payload['Arguments']['Secret']['DATA'][-1]=99
        self.payload['Arguments']['TextValue']['DATA'][-1]=98
        self.stage(1,Kind=mailbox.LOGOUT,Secret='credential',TextValue='preimage')
        self.plc.run(self.ingress)
        self.assertEqual((self.work['Pending'],self.work['Error'],self.request['Kind']),(1,0,mailbox.LOGOUT))
        self.assertEqual(self.request['Sequence'],0)
        self.assertEqual(self.request['Secret']['LEN'],10)
        for base in (self.payload,self.sample):
            for n in ('Secret','TextValue'):
                self.assertEqual(base['Arguments'][n]['LEN'],0)
                self.assertFalse(any(base['Arguments'][n]['DATA']))
        self.response.update(Accepted=1,AckSequence=1)
        self.plc.run(self.after)
        self.assertEqual((self.response['AckSequence'],self.work['OwnerAck']),(0,1))
        self.assertFalse(any(self.request['Secret']['DATA']))
        self.assertFalse(any(self.request['TextValue']['DATA']))

    def test_simultaneous_ingresses_are_consumed_refused_and_not_queued(self):
        self.request['Sequence']=8
        self.request['Frame']['Words']=frame.encode(self.app,dict(Kind=mailbox.START,Sequence=8,Secret='legacy'))
        self.stage(1,Kind=mailbox.STOP,Secret='typed')
        self.plc.run(self.ingress)
        self.assertEqual((self.work['Pending'],self.work['Error']),(1,2))
        self.assertFalse(any(self.request['Frame']['Words']))
        self.assertFalse(any(self.payload['Arguments']['Secret']['DATA']))
        self.assertEqual(self.request['Kind'],0)
        self.plc.run(self.ingress)
        self.assertEqual(self.work['Pending'],0)

    def test_bad_envelope_and_lengths_consumed_before_late_payload_cannot_replay(self):
        for field,bad in [('SchemaVersion',2),('ManifestRevision',0),('StagedSequence',2),('Secret.LEN',999)]:
            with self.subTest(field=field):
                self.setUp();self.stage(1,Kind=mailbox.START,Secret='malformed',TextValue='preimage')
                if '.' in field:self.payload['Arguments']['Secret']['LEN']=bad
                else:self.payload[field]=bad
                self.plc.run(self.ingress)
                self.assertNotEqual(self.work['Error'],0)
                self.assertEqual(self.request['Kind'],0)
                for base in (self.payload,self.sample):
                    for n in ('Secret','TextValue'):
                        self.assertEqual(base['Arguments'][n]['LEN'],0)
                        self.assertFalse(any(base['Arguments'][n]['DATA']))
                self.assertFalse(any(self.request['Secret']['DATA']))
                self.payload.update(SchemaVersion=1,ManifestRevision=7,StagedSequence=1)
                self.plc.run(self.ingress)
                self.assertEqual(self.work['Pending'],0)

    def test_first_scan_does_not_replay_visible_commit(self):
        self.stage(1,Kind=mailbox.START,Secret='not-replayed')
        self.tags['S:FS']=True
        self.plc.run(self.ingress)
        self.assertEqual(self.work['Pending'],0)
        self.tags['S:FS']=False;self.plc.run(self.ingress)
        self.assertEqual(self.work['Pending'],0)

    def test_serial_wrap_and_backward_tokens_do_not_move_the_forward_baseline(self):
        cases=[(2147483647,-2147483648,0),(-1,0,0),(100,99,3),(100,-2147483548,3)]
        for prior,current,error in cases:
            with self.subTest(prior=prior,current=current):
                self.setUp();self.work.update(CoreSerial=prior,LastCoreSeen=prior)
                self.stage(current,Kind=mailbox.LOGOUT);self.plc.run(self.ingress)
                self.assertEqual(self.work['Error'],error)
                self.assertEqual(self.work['CoreSerial'],prior if error else current)

    def test_integer_parser_handles_full_dint_boundaries_and_refuses_partial_values(self):
        parser=st.parse('\n'.join(command.parse_integer(self.app)))
        for value,expected in [('0',0),('-2147483648',-2147483648),('+2147483647',2147483647),
            (' 2500.000 ',2500),('2147483648',None),('-2147483649',None),('1x',None),('1.5',None),('',None),(' + ',None)]:
            with self.subTest(value=value):
                seek=self.work['Seek'];seek['LEN']=len(value);seek['DATA'][:len(value)]=value.encode()
                self.plc.run(parser)
                self.assertEqual(bool(self.work['Valid']),expected is not None)
                if expected is not None:self.assertEqual(self.work['Parsed'],expected)

    def test_config_identity_revision_and_integer_value_resolve_on_plc_only(self):
        from fraktal_ab_generate import editable_values
        ordinal,record,member=editable_values(self.app)[0]
        self.stage(1,Kind=mailbox.WRITE_CONFIG,TargetPath=self.app.name,NameValue=member.write_key,
                   IntValue=123,TextValue='2500.0')
        self.plc.run(self.ingress)
        self.assertEqual(self.work['Error'],0)
        self.assertEqual((self.request['IntValue'],self.request['BoolValue']),(ordinal,2500))
        self.assertEqual(self.payload['Arguments']['IntValue'],123)
        self.stage(2,Kind=mailbox.WRITE_CONFIG,TargetPath='differentRoot',NameValue=member.write_key,IntValue=123,TextValue='1')
        self.plc.run(self.ingress);self.assertEqual(self.work['Error'],command.FOREIGN_ROOT)
        self.stage(3,Kind=mailbox.WRITE_CONFIG,TargetPath=self.app.name,NameValue=member.write_key,IntValue=122,TextValue='1')
        self.plc.run(self.ingress);self.assertEqual(self.work['Error'],command.STALE_REVISION)
        # An unknown key is not a malformed payload: ordinal 0 reaches the
        # owner, whose capability CASE refuses it by name.
        self.stage(4,Kind=mailbox.WRITE_CONFIG,TargetPath=self.app.name,NameValue='not.a.key',IntValue=123,TextValue='1')
        self.plc.run(self.ingress)
        self.assertEqual((self.work['Error'],self.request['IntValue']),(0,0))
        self.stage(5,Kind=mailbox.WRITE_CONFIG,TargetPath=self.app.name,NameValue=member.write_key,IntValue=123,TextValue='1.5')
        self.plc.run(self.ingress);self.assertEqual(self.work['Error'],1)

    def test_stale_serial_is_refused_as_stale_without_sampling_its_payload(self):
        self.work.update(CoreSerial=100,LastCoreSeen=100)
        self.stage(99,Kind=mailbox.START,Secret='late')
        self.payload['SchemaVersion']=2
        self.plc.run(self.ingress)
        self.assertEqual(self.work['Error'],command.STALE_SERIAL)
        self.assertEqual(self.sample['SchemaVersion'],0)
        self.assertFalse(any(self.payload['Arguments']['Secret']['DATA']))

    def test_every_error_code_refuses_with_its_named_reason(self):
        import fraktal_ab_config as config
        import fraktal_ab_manifest as manifest
        body=st.parse('\n'.join(command.refusal(self.app)))
        expected={1:command.INVALID,2:command.COLLISION,3:command.STALE,4:config.CAPTURE_REVISION_KEY,
                  5:mailbox.TARGET_KEY,6:command.INVALID,-1:command.INVALID}
        for code,key in expected.items():
            with self.subTest(code=code):
                self.work['Error']=code;self.response['DiagnosticKey']=0
                self.plc.run(body)
                self.assertEqual(self.response['DiagnosticKey'],manifest.numeric_key(self.app,key))

    def test_live_model_catalogue_overrides_any_supplied_numeric_ordinal(self):
        import fraktal_ab_models as models
        c=dict(SchemaVersion=1,Count=2,CodeLength=[0]*self.app.model_capacity,CodeBytes=[0]*(self.app.model_capacity*models.CODE_MAX))
        code=b'created_after_download';c['CodeLength'][1]=len(code);c['CodeBytes'][models.CODE_MAX:models.CODE_MAX+len(code)]=code
        self.tags[models.tag(self.app)]=c
        self.stage(1,Kind=mailbox.SET_MODEL,IntValue=999,TextValue=code.decode())
        self.plc.run(self.ingress)
        self.assertEqual((self.work['Error'],self.request['IntValue']),(0,2))
        c['Count']=self.app.model_capacity+1
        self.stage(2,Kind=mailbox.SET_MODEL,IntValue=999,TextValue=code.decode())
        self.plc.run(self.ingress);self.assertEqual(self.request['IntValue'],0)

    def test_all_core_operations_have_an_explicit_discovery_disposition(self):
        from fraktal_ab_command_binding import operations
        rows=operations(command.operations(self.app))
        self.assertEqual({r['Kind'] for r in rows},set(mailbox.KINDS.values()))


def service_tags(app,definitions):
    """The tags the set-service status reads, at their declared initial values."""
    import fraktal_ab_access as access
    import fraktal_ab_data_access as data
    import fraktal_ab_manifest as manifest
    import fraktal_ab_sets as sets
    status=lambda:initial(definitions,command.SET_STATUS)
    return {command.set_status_tag(app):status(),command.empty_status_tag(app):status(),
        access.tag(app,'State'):st.structure(access.state_members(app)),sets.state_tag(app):st.structure(sets.state_members(app)),
        sets.staged_tag(app):st.structure(sets.request_members()),data.tag(app,'Levels'):st.structure(data.levels_members(app)),
        f'FRK_{app.name}_MfWriteCapabilities':deepcopy(manifest.content(app)['WriteCapabilities'])}


class ServiceStatusTests(unittest.TestCase):
    """The set-service reply publishes only an accepted, permitted, bounded answer."""
    @classmethod
    def value(cls,kind):return initial(cls.definitions,kind)

    @classmethod
    def setUpClass(cls):
        cls.app=demo.application();cls.definitions=pub.schema(cls.app)
        cls.body=st.parse('\n'.join(command.service_status(cls.app)))

    def setUp(self):
        import fraktal_ab_access as access
        import fraktal_ab_data_access as data
        import fraktal_ab_sets as sets
        a=self.app;self.tags=service_tags(a,self.definitions)
        self.work=self.value(command.WORK);self.response=dict(Accepted=1)
        self.tags.update({command.work_tag(a):self.work,mailbox.response_tag_name(a):self.response})
        self.level=self.tags[access.tag(a,'State')];self.state=self.tags[sets.state_tag(a)]
        self.staged=self.tags[sets.staged_tag(a)];self.flags=self.tags[data.tag(a,'Levels')]
        self.level['CurrentLevel']=access.ENGINEER
        self.level['Required'][access.GATES[mailbox.SAVE_CONFIG_SET]]=access.ENGINEER
        self.state.update(Sequence=7,Count=3,Reason=0);self.work['OwnerAck']=7
        self.staged.update(Operation=mailbox.SAVE_CONFIG_SET,Kind=2,NameLength=4);self.staged['NameBytes'][:4]=list(b'Ramp')
        self.caps=self.tags[f'FRK_{a.name}_MfWriteCapabilities']
        for i,row in enumerate(self.caps):
            self.state['Snapshot'][i]=1000+i;self.flags['Readable'][i]=int(i%2==0)
        self.plc=st.Controller(self.tags,calls={'CPS':st.cps_structure})

    @property
    def status(self):
        # CPS replaces the destination object, so always read the live tag.
        return self.plc.tags[command.set_status_tag(self.app)]

    def published(self):
        return any(self.status['Values']) or self.status['Sequence'] or self.status['Name']['LEN']

    def test_accepted_permitted_answer_names_the_set_and_only_readable_values_of_its_kind(self):
        self.plc.run(self.body)
        self.assertEqual((self.status['SchemaVersion'],self.status['Sequence'],self.status['Operation'],self.status['Count']),
                         (1,7,mailbox.SAVE_CONFIG_SET,3))
        self.assertEqual(bytes(self.status['Name']['DATA'][:self.status['Name']['LEN']]),b'Ramp')
        for i,row in enumerate(self.caps):
            shown=row['ConfigKind']==2 and i%2==0
            self.assertEqual((self.status['Values'][i],self.status['Readable'][i]),(1000+i,1) if shown else (0,0))

    def test_each_failed_condition_publishes_the_empty_answer(self):
        import fraktal_ab_access as access
        gate=access.GATES[mailbox.SAVE_CONFIG_SET]
        cases=[('anonymous',lambda:self.level.update(CurrentLevel=0)),
               ('below the gate',lambda:self.level.update(CurrentLevel=access.ENGINEER-1)),
               ('corrupt requirement',lambda:self.level['Required'].__setitem__(gate,access.ADMIN+1)),
               ('refused',lambda:self.response.update(Accepted=0)),
               ('another sequence',lambda:self.work.update(OwnerAck=8)),
               ('negative name',lambda:self.staged.update(NameLength=-1)),
               ('oversized name',lambda:self.staged.update(NameLength=81))]
        for name,corrupt in cases:
            with self.subTest(name):
                self.setUp();self.plc.run(self.body);self.assertTrue(self.published())
                corrupt();self.plc.run(self.body)
                self.assertFalse(self.published())


if __name__=='__main__':unittest.main()
