"""Execute PLC sequence publication against an independent legacy projection."""
from dataclasses import replace
from pathlib import Path
import json
import unittest

import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_sequence as sequence
import fraktal_ab_canonical_status as diagnostic
import fraktal_ab_genealogy_s3c_demo as demo
import fraktal_ab_generate as gen
import fraktal_ab_projection as oracle
import fraktal_ab_s3c_equivalence as equivalence
import fraktal_ab_st_model as st


class SequenceTests(unittest.TestCase):
    def setup_model(self,app=None):
        self.app=app or demo.application();app=self.app
        self.definitions=pub.schema(app)
        def value(kind,initial=None):
            if kind.startswith(pub.PREFIX+'String'):
                raw=(initial or '').encode('utf-8');width=pub.string_width(kind)
                return dict(LEN=len(raw),DATA=list(raw)+[0]*(width-len(raw)))
            if kind not in self.definitions:return initial or 0
            supplied=initial or {}
            return {m.name:([value(m.kind,item) for item in supplied.get(m.name,[None]*m.count)] if m.count
                else value(m.kind,supplied.get(m.name))) for m in self.definitions[kind]}
        tags={app.name:value(pub.root_type(app),pub.initial(app)),pub.header_tag(app):dict(Valid=1,FragmentRevision=0)}
        def serialize(name,kind,initial,**options):
            tags[name]=[value(kind,item) for item in initial] if options.get('array') else value(kind,initial)
            return ''
        sequence.tags(app,serialize);diagnostic.private_tags(app,serialize)
        self.unit=dict(Mode=app.chains[0].mode_ordinal,Running=1,Error=0,Step=0,StepExpectedMs=0,StepTimedOut=0)
        self.chart=st.structure(gen.chart_members(app))
        self.chart['RowEpoch']=7
        self.recipe={m.name:m.initial for m in app.records[0].members}
        tags.update({f'FRK_{app.name}_Unit':self.unit,f'FRK_{app.name}_Chart':self.chart,
                     app.records[0].name+'Tag':self.recipe})
        self.controller=st.Controller(tags,calls={'CPS':st.cps_structure},
            routines={diagnostic.routine_name(app):diagnostic.resolver(app)})
        self.logic='\n'.join(sequence.cyclic(app))

    def run_scan(self):
        # The base publisher owns StepNo and runs before the sequence service.
        prefix=next(line for line in pub.cyclic(self.app) if line.startswith(self.app.name+'.CurrentStep.StepNo :='))
        self.controller.run(prefix+'\n'+self.logic)

    def flattened(self):
        result={}
        def walk(prefix,value):
            if isinstance(value,dict) and set(value)=={'LEN','DATA'}:
                result[prefix]=bytes(x&255 for x in value['DATA'][:value['LEN']]).decode('utf-8')
            elif isinstance(value,dict):
                for key,child in value.items():walk(prefix+'/'+key if prefix else key,child)
            elif isinstance(value,list):
                for i,child in enumerate(value):walk(prefix+f'[{i if prefix=="ActiveSteps" else i+1}]',child)
            else:result[prefix]=bool(value) if prefix.endswith(('/Visited','/ErrorActive','/WarningActive','/TimedOut','/IsError')) or prefix=='SequenceViewEnabled' else value
        root=self.controller.tags[self.app.name]
        for key in ('SequenceViewEnabled','SequenceStepCount','SequenceAnnotationCount','SequenceSteps','SequenceAnnotations','ActiveSteps',
                    'CurrentStepElapsed','CurrentStepTimedOut','CurrentStep'):
            walk(key,root[key])
        walk('SequenceSteps',self.controller.tags[sequence.definition_tag(self.app)]['SequenceSteps'])
        return result

    def assert_oracle(self):
        wanted=oracle.sequence_status(self.app,self.unit,self.chart,{self.app.records[0].name:self.recipe})
        wanted.update({k:v for k,v in oracle.step_status(self.app,self.unit,self.chart).items() if k.startswith('CurrentStep/')})
        wanted.update({'CurrentStep/StepNo':self.unit['Step'],'CurrentStepElapsed':self.chart['CurrentStepMs'],
                       'CurrentStepTimedOut':bool(self.unit['StepTimedOut'])})
        wanted={k.replace('ActiveSteps[1]','ActiveSteps[0]'):v for k,v in wanted.items()}
        self.assertEqual(self.flattened(),wanted)

    def visit(self,numbers):
        order=gen.ordered_steps(self.app)
        self.chart['RowCount']=len(numbers)
        for row,number in enumerate(numbers,1):
            i=order.index(number)
            self.chart['RowOf'][i]=row;self.chart['RowEpochOf'][i]=self.chart['RowEpoch']
            self.chart['LastMs'][i]=row*10
        self.unit['Step']=numbers[-1] if numbers else 0
        self.chart['ActiveStepNumber']=self.unit['Step'];self.chart['CurrentStepMs']=37

    def test_independent_647_path_inventory(self):
        app=demo.application()
        root=Path(__file__).resolve().parents[4]
        inventory=json.loads((root/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3C_INVENTORY_2026-10-22.json').read_text())
        paths=equivalence.subset_paths(app,[m.code for m in app.models],canonical=True)
        self.assertEqual(paths,set(inventory['paths']));self.assertEqual(len(paths),647)

    def test_empty_and_nonnumeric_discovery_order_match_the_oracle(self):
        self.setup_model();self.run_scan();self.assert_oracle()
        order=gen.ordered_steps(self.app);self.visit([order[-1],order[1],order[0]])
        self.run_scan();self.assert_oracle()

    def test_history_changes_without_republishing_definitions(self):
        self.setup_model();order=gen.ordered_steps(self.app);self.visit(order[:3]);self.run_scan()
        header=self.controller.tags[pub.header_tag(self.app)];revision=header['FragmentRevision']
        self.chart['LastMs'][1]=987;self.chart['CurrentStepMs']=444
        self.run_scan();self.assert_oracle();self.assertEqual(header['FragmentRevision'],revision)

    def test_mode_reset_clears_every_published_row_and_invalidates_metadata(self):
        self.setup_model();self.visit(gen.ordered_steps(self.app)[:2]);self.run_scan()
        before=self.controller.tags[pub.header_tag(self.app)]['FragmentRevision']
        self.unit['Mode']=self.app.manual_mode;self.chart['RowEpoch']+=1;self.chart['RowCount']=0
        self.run_scan();self.assert_oracle()
        self.assertGreater(self.controller.tags[pub.header_tag(self.app)]['FragmentRevision'],before)

    def test_recipe_expected_time_refreshes_definition_revision(self):
        self.setup_model();self.visit(gen.ordered_steps(self.app));self.run_scan()
        before=self.controller.tags[pub.header_tag(self.app)]['FragmentRevision']
        import fraktal_ab_declaration as decl
        target=next(decl.expected_member(s) for c in self.app.chains for s in c.steps if decl.expected_member(s))
        self.recipe[target]+=123;self.run_scan();self.assert_oracle()
        self.assertGreater(self.controller.tags[pub.header_tag(self.app)]['FragmentRevision'],before)

    def test_warning_marks_and_sparse_text_come_from_plc_history(self):
        self.setup_model();order=gen.ordered_steps(self.app);self.visit([order[2],order[0]])
        self.chart['WarnReason'][2]=next(v for v in self.app.reasons.values() if v)
        self.chart['WarnSource'][2]=0
        self.run_scan();self.assert_oracle()
        self.chart['WarnReason'][2]=0;self.run_scan();self.assert_oracle()

    def test_reused_step_numbers_in_another_mode_keep_distinct_definitions(self):
        app=demo.application();chain=app.chains[0]
        other=replace(chain,name=chain.name+'Other',mode_ordinal=2,
                      steps=(replace(chain.steps[0],name='OtherModeEntry'),))
        self.setup_model(replace(app,chains=tuple(other if c.mode_ordinal==2 else c for c in app.chains)))
        self.visit([chain.steps[0].number]);self.run_scan();self.assert_oracle()
        self.unit['Mode']=2;self.chart['RowEpoch']+=1;self.visit([chain.steps[0].number])
        self.run_scan();self.assert_oracle()
        self.assertEqual(self.flattened()['SequenceSteps[1]/StepName'],'project.step.OtherModeEntry')

    def test_condition_labels_never_describe_the_previous_steps_inputs(self):
        self.setup_model()
        import fraktal_ab_declaration as decl
        step=next(s for s in self.app.chains[0].steps if decl.step_conditions(s))
        self.unit['Step']=step.number;self.unit['StepExpectedMs']=777;self.unit['StepTimedOut']=1
        self.chart['ActiveStepNumber']=step.number;self.chart['CondOk']=[1]*decl.MAX_STEP_CONDS
        self.run_scan();self.assert_oracle()
        self.assertTrue(self.flattened()['CurrentStep/Conds[1]/Ok'])
        self.chart['ActiveStepNumber']=step.number+9999
        self.run_scan();self.assert_oracle()
        self.assertFalse(any(v for k,v in self.flattened().items() if '/Conds[' in k and k.endswith('/Ok')))


if __name__=='__main__':unittest.main()
