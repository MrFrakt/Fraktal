"""Execute session/policy/audit publication against its independent owners."""
from pathlib import Path
import json
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_access as access
import fraktal_ab_canonical_alarms as alarms
import fraktal_ab_canonical_publication as pub
import fraktal_ab_access as owner
import fraktal_ab_data_access as data
import fraktal_ab_genealogy_s3e_demo as demo
import fraktal_ab_manifest as manifest
import fraktal_ab_projection as oracle
import fraktal_ab_s3e_equivalence as equivalence
import fraktal_ab_st_model as st
import fraktal_ab_shelving as shelving
import test_fraktal_ab_canonical_alarms as base


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture=base.AlarmTests()
        with patch.object(base.demo,'application',demo.application):fixture.setup_model()
        self.app=app=fixture.app;self.schema=fixture.schema
        self.state=st.structure(owner.state_members(app));self.audit=st.structure(owner.audit_members())
        self.policy=st.structure(data.policy_members(app));self.policy['Count']=len(app.data_classes)
        for i,c in enumerate(app.data_classes):
            self.policy['ClassKey'][i]=manifest.numeric_key(app,c.class_id)
            self.policy['LabelKey'][i]=manifest.numeric_key(app,c.label_key)
            self.policy['ReadLevel'][i]=c.read_level;self.policy['WriteLevel'][i]=c.write_level
        fixture.controller.tags.update({owner.tag(app,'State'):self.state,owner.tag(app,'Audit'):self.audit,
            data.tag(app,'Policy'):self.policy,access.state_tag(app):fixture.make_value(access.WORK)})
        fixture.logic+='\n'+'\n'.join(access.cyclic(app))

    def scan(self):self.fixture.scan()

    def actual_access(self):
        result={}
        def walk(kind,value,path,logical=''):
            if kind.startswith(pub.PREFIX+'String'):
                result[path]=bytes(x&255 for x in value['DATA'][:value['LEN']]).decode('utf-8')
            elif kind not in self.schema:result[path]=bool(value) if kind=='BOOL' else value&0xffffffff if logical=='BITSTRING32' else value
            else:
                for m in self.schema[kind]:
                    p=path+'/'+m.name
                    if m.count:
                        count=self.fixture.controller.tags[self.app.name]['Access']['ClassCount'] if m.count_path else m.extent or m.count
                        for i in range(count):walk(m.kind,value[m.name][i],f'{p}[{i+m.lower}]',m.logical)
                    else:walk(m.kind,value[m.name],p,m.logical)
        walk(access.ACCESS,self.fixture.controller.tags[self.app.name]['Access'],'Access')
        return result

    def assert_access_oracle(self):
        expected=owner.status(self.app,self.state)
        expected.update(data.policy_status(self.app,manifest.content(self.app),self.policy))
        expected={p.replace('Required['+str(i+1)+']','Required['+str(i)+']') if 'Required[' in p else p:v
                  for p,v in expected.items() for i in ([int(p.rsplit('[',1)[1][:-1])-1] if 'Required[' in p else [0])}
        self.assertEqual(self.actual_access(),expected)

    def assert_alarm_oracle(self):
        expected=oracle.alarm_log_status(self.app,self.fixture.active,self.fixture.ring)
        expected.update(oracle.alarm_meta_status(manifest.content(self.app)))
        expected.update(oracle.state_flags_status(self.app,self.fixture.flags))
        expected.update(owner.audit_status(self.app,manifest.content(self.app),self.audit,self.fixture.ring))
        self.assertEqual(self.fixture.actual(),expected)

    def set_audit(self,index=0,*,actor=b'operator',key='std.audit.operatorAction',**fields):
        self.fixture.event(index,ring=True,State=0,ReasonCode=0,SourceModuleId=1,ComeDate=20261022,ComeTime=123456000,GoneDate=20261022,GoneTime=123456000)
        self.audit['Key'][index]=manifest.numeric_key(self.app,key);self.audit['UserLength'][index]=len(actor)
        for j in range(owner.ACTOR_WORDS):
            word=int.from_bytes(actor[j*4:(j+1)*4].ljust(4,b'\0'),'little')
            self.audit['UserWords'][index*owner.ACTOR_WORDS+j]=word if word<1<<31 else word-(1<<32)
        for name,value in fields.items():self.audit[name][index]=value

    def test_independent_inventory_has_2154_paths_and_unsigned_result_word(self):
        root=Path(__file__).resolve().parents[4]
        inventory=json.loads((root/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3E_INVENTORY_2026-10-22.json').read_text())
        paths=equivalence.subset_paths(self.app,[m.code for m in self.app.models],canonical=True)
        self.assertEqual(paths,set(inventory['paths']));self.assertEqual(len(paths),2154)
        self.assertEqual(equivalence.logical_types(self.app,paths)['Press/Access/LoginResultSequence'],'UInt32')
        self.assertFalse(access.validate(self.app))

    def test_sessions_busy_failure_result_and_all_policy_levels_match_owner(self):
        for user,level,busy,failed,word in ((b'',0,0,0,0),(b'engineer',3,1,0,0x7fffffff),(b'admin',4,0,0,-2147483648),(b'',0,0,1,-1)):
            self.state.update(CurrentLevel=level,UserLength=len(user),UserBytes=list(user.ljust(owner.WIDTH,b'\0')),LoginBusy=busy,LoginFailed=failed,LoginResultSequence=word,SessionTimeout=12345)
            self.state['Required']=[i%5 for i in range(owner.GATE_COUNT)]
            self.policy['ReadLevel']=[4,2];self.policy['WriteLevel']=[1,3]
            self.scan();self.assert_access_oracle();self.assert_alarm_oracle()

    def test_live_class_extents_unknown_keys_and_policy_schema_fail_closed(self):
        self.scan();self.assert_access_oracle()
        self.policy['Count']=1;self.policy['ClassKey'][0]=0;self.policy['LabelKey'][0]=0
        self.scan();self.assert_access_oracle()
        self.policy['SchemaVersion']=999;self.scan();self.assert_access_oracle()
        self.policy['SchemaVersion']=1;self.policy['Count']=2;self.scan();self.assert_access_oracle()

    def test_audit_actor_numbers_and_data_capability_match_projection(self):
        self.set_audit(actor=b'\xff\x80\x00\x7fuser',key=data.DENIED,Kind=-2147483648,Gate=2147483647,Sequence=-1,DataCapability=1,DataRequiredLevel=-2147483648)
        self.scan();self.assert_alarm_oracle()
        self.set_audit(63,actor=b'x'*owner.WIDTH,key='std.audit.loginFailed',Kind=1,Gate=0)
        self.scan();self.assert_alarm_oracle()
        self.audit['DataCapability'][0]=999;self.scan();self.assert_alarm_oracle()

    def test_automatic_shelving_keeps_module_source_and_marker(self):
        self.set_audit(key=shelving.UNSHELVED,Sequence=0,Kind=1,Gate=9)
        self.fixture.ring['RingSourceModuleId'][0]=3
        self.scan();self.assert_alarm_oracle()

    def test_slot_reuse_schema_and_occupancy_changes_clear_old_enrichment(self):
        self.set_audit(Kind=42,Gate=7);self.scan();self.assert_alarm_oracle()
        self.fixture.ring['RingReasonCode'][0]=next(v for v in self.app.reasons.values() if v)
        self.scan();self.assert_alarm_oracle()
        self.fixture.ring['RingReasonCode'][0]=0;self.scan();self.assert_alarm_oracle()
        self.audit['SchemaVersion']=99;self.scan();self.assert_alarm_oracle()
        self.audit['SchemaVersion']=owner.AUDIT_SCHEMA;self.scan();self.assert_alarm_oracle()
        self.fixture.ring['RingState'][0]=1;self.scan();self.assert_alarm_oracle()
        self.fixture.ring['RingState'][0]=0;self.audit['Key'][0]=0;self.scan();self.assert_alarm_oracle()

    def test_unchanged_audits_are_not_reformatted_and_actor_changes_invalidate(self):
        self.set_audit(Kind=13,Gate=4);self.scan();self.assert_alarm_oracle()
        routine=access.audit_routine(self.app);number=access.number_routine(self.app)
        original=self.fixture.controller.routines[routine]
        self.fixture.controller.routines[routine]=st.parse('UnchangedAuditMustNotRun := 1;')
        self.scan();self.assertNotIn('UnchangedAuditMustNotRun',self.fixture.controller.tags)
        self.fixture.controller.routines[routine]=original
        self.audit['UserWords'][0]^=1;self.scan();self.assert_alarm_oracle()
