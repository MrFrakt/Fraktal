"""Failure cleanup and public CHANGEOVER ordering for the follow-up apparatus."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
import fraktal_ab_s3f_revision_execute as fixture
import fraktal_ab_genealogy_demo as demo


class RevisionFixtureTests(unittest.TestCase):
    def runner(self):
        class Parent:
            def check(self,ok,message):
                if not ok:raise ValueError(message)
        with patch.object(fixture.previous,'paired_run',return_value=Parent):
            run=object.__new__(fixture.paired_run(Path('unused.json')))
        run.app=demo.application();run.evidence={};return run

    def test_failed_observation_restores_model_live_values_inputs_and_mode(self):
        run=self.runner();app=run.app;events=[]
        values={r.name:{m.name:m.initial for m in r.members} for r in app.records}
        scoped=[(o,r,m) for o,r,m in fixture.gen.editable_values(app) if fixture.gen.is_model_scoped(app,r,m.name)]
        original=deepcopy(values);state=dict(Mode=app.manual_mode,ModelOrdinal=1);inputs={'Air':0}
        def snapshot():return dict(records=deepcopy(values),banks=[{'bank':1},{'bank':2}],codes=['A','B'],inputs=dict(inputs),mode=state['Mode'],active=state['ModelOrdinal'])
        run.revision_snapshot=snapshot;run.unit=lambda:state;run.idle=lambda:None
        run.home=lambda:inputs.update(Air=1)
        run.set=lambda tag,value:inputs.update({tag:value})
        run.config_pair=lambda phase:dict(pair=dict(canonical=dict(values={app.name+'/Status/ConfigRev':100})))
        def change(target,observe=True):
            state['ModelOrdinal']=target
            for o,r,m in scoped:values[r.name][m.name]+=7
            if observe:raise RuntimeError('paired observation failed')
        run.changeover=change
        def command(kind,**args):
            events.append((kind,args))
            if kind==fixture.mb.WRITE_CONFIG:
                o=args[fixture.mb.CONFIG_ORDINAL_MEMBER];_,r,m=next(v for v in scoped if v[0]==o)
                values[r.name][m.name]=args[fixture.mb.CONFIG_VALUE_MEMBER]
            elif kind==fixture.mb.SET_MODE:state['Mode']=args['IntValue']
        run.native_command=command
        with self.assertRaisesRegex(RuntimeError,'paired observation failed'):run.active_model_vector()
        self.assertEqual(values,original);self.assertEqual(inputs,{'Air':0})
        self.assertEqual(state,dict(Mode=app.manual_mode,ModelOrdinal=1))
        self.assertFalse(run._revision_cleaning)
        self.assertEqual(sum(k==fixture.mb.WRITE_CONFIG for k,a in events),len(scoped))

    def test_model_commits_only_after_existing_public_tooling_answer(self):
        run=self.runner();events=[];phases=[]
        state=dict(Error=0,DecisionId=0,Complete=0,ModelOrdinal=1);requested=0
        run.idle=lambda:None;run.unit=lambda:state
        run.wait=lambda predicate,label:run.check(bool(predicate()),label)
        run.config_pair=phases.append
        def command(kind,**args):
            nonlocal requested
            events.append((kind,args))
            if kind==fixture.mb.SET_MODEL:requested=args['IntValue']
            elif kind==fixture.mb.START:state['DecisionId']=fixture.press.DECISION_CHANGEOVER_CONFIRM
            elif kind==fixture.mb.DECISION_ANSWER:
                self.assertEqual(state['ModelOrdinal'],1)
                state.update(Complete=1,ModelOrdinal=requested)
        run.native_command=command;run.changeover(2)
        self.assertEqual([k for k,a in events],[fixture.mb.SET_MODE,fixture.mb.SET_MODEL,fixture.mb.START,fixture.mb.DECISION_ANSWER,fixture.mb.SET_MODE])
        self.assertEqual(phases,['active_model_confirmation'])
        self.assertEqual(state['ModelOrdinal'],2)


if __name__=='__main__':unittest.main()
