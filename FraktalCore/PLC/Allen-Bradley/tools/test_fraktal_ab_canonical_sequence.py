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
import fraktal_ab_st_model as st


import fraktal_ab_declaration as decl
import fraktal_ab_manifest as manifest

def sequence_slots(app):
    return sequence.slots(app)

def reason_description(app, reason):
    return app.reasons.get(reason, f'std.reason.{reason}')

def _module_path(app, ordinal):
    if ordinal <= 0:
        return ""
    if ordinal == 1:
        return app.name
    index = ordinal - 2
    return f"{app.name}.{app.modules[index].name}" if 0 <= index < len(app.modules) else ""

def current_step(app, unit):
    mode = unit.get('Mode')
    chain = next((c for c in app.chains if c.mode_ordinal == mode), None)
    step_no = unit.get('Step')
    return next((s for s in chain.steps if s.number == step_no), None) if chain else None

def condition_records(step, unit, chart):
    records = decl.step_conditions(step) if step else ()
    coherent = (chart is not None and step is not None and chart.get("ActiveStepNumber") == unit.get("Step"))
    ok = chart.get("CondOk", []) if coherent else []
    values = {}
    for i in range(decl.MAX_STEP_CONDS):
        label = records[i][1] if coherent and i < len(records) else ""
        values[f"CurrentStep/Conds[{i + 1}]/Label"] = label
        values[f"CurrentStep/Conds[{i + 1}]/Ok"] = bool(label) and bool(ok[i] if i < len(ok) else 0)
    return values

def step_status(app, unit, chart=None):
    step = current_step(app, unit)
    busy = unit.get("Running", 0) != 0 and unit.get("Error", 0) == 0
    values = {
        'CurrentStep/StepName': f'project.step.{step.name}' if step else '',
        'CurrentStep/AwaitingLabel': f'{step.module}.{step.command}' if step and step.module and step.command else '',
        'CurrentStep/ExpectedTime': unit.get("StepExpectedMs", 0) if step else 0,
        'Starved': busy and (step.time_class == "WAIT_UPSTREAM" if step else False),
        'Blocked': busy and (step.time_class == "WAIT_DOWNSTREAM" if step else False),
    }
    time_class = step.time_class if step else "WORK"
    values["CurrentStep/TimeClass"] = decl.TIME_CLASSES.index(time_class)
    values.update(condition_records(step, unit, chart))
    return values

def sequence_status(app, unit, chart, record_values=None):
    slots = sequence_slots(app)
    values = {'SequenceViewEnabled': bool(app.chains)}
    recipe = (record_values or {}).get(app.records[0].name, {}) if app.records else {}
    order = gen.ordered_steps(app)
    chain = next((c for c in app.chains if c.mode_ordinal == unit.get('Mode')), None)
    by_number = {s.number: s for s in chain.steps} if chain else {}
    rows = []
    if chart is not None and chain is not None:
        epoch = chart.get('RowEpoch', 0)
        count = chart.get('RowCount', 0)
        for index, number in enumerate(order):
            row = chart['RowOf'][index]
            if (chart['RowEpochOf'][index] == epoch and 1 <= row <= count and number in by_number):
                rows.append((row, index))
    rows.sort()
    rows = rows[:slots]
    row_of_index = {index: position for position, (_, index) in enumerate(rows, start=1)}
    values['SequenceStepCount'] = len(rows)
    notes = []
    for position in range(1, slots + 1):
        base = f'SequenceSteps[{position}]'
        if position <= len(rows):
            index = rows[position - 1][1]
            step = by_number[order[index]]
            warn = chart['WarnReason'][index]
            if warn:
                notes.append((position, warn, chart['WarnSource'][index]))
            values.update({
                f'{base}/StepNo': step.number,
                f'{base}/Branch': 0,
                f'{base}/StepName': f'project.step.{step.name}',
                f'{base}/AwaitingLabel': f'{step.module}.{step.command}' if step.module and step.command else '',
                f'{base}/AwaitsPath': f'{app.name}.{step.module}' if step.module else '',
                f'{base}/TimeClass': decl.TIME_CLASSES.index(step.time_class),
                f'{base}/ExpectedTime': recipe.get(decl.expected_member(step), 0) if decl.expected_member(step) else 0,
                f'{base}/Visited': True,
                f'{base}/LastDuration': chart['LastMs'][index],
                f'{base}/ErrorActive': False,
                f'{base}/WarningActive': bool(warn),
            })
        else:
            values.update({
                f'{base}/StepNo': 0, f'{base}/Branch': 0, f'{base}/StepName': '',
                f'{base}/AwaitingLabel': '', f'{base}/AwaitsPath': '',
                f'{base}/TimeClass': 0, f'{base}/ExpectedTime': 0,
                f'{base}/Visited': False, f'{base}/LastDuration': 0,
                f'{base}/ErrorActive': False, f'{base}/WarningActive': False,
            })
    values['SequenceAnnotationCount'] = len(notes)
    for position in range(1, slots + 1):
        base = f'SequenceAnnotations[{position}]'
        row, reason, source = notes[position - 1] if position <= len(notes) else (0, 0, 0)
        values.update({
            f'{base}/RowIdx': row,
            f'{base}/IsError': False,
            f'{base}/Key': reason_description(app, reason) if row else '',
            f'{base}/SourcePath': _module_path(app, source + 1) if row else '',
        })
    running = bool(unit.get('Running')) and not unit.get('Error')
    cursor = 0
    if running and chart is not None and chart.get('ActiveStepNumber') == unit.get('Step'):
        index = order.index(unit['Step']) if unit.get('Step') in order else -1
        cursor = row_of_index.get(index, 0)
    values['ActiveSteps[1]/RowIdx'] = cursor
    values['ActiveSteps[1]/Elapsed'] = (chart or {}).get('CurrentStepMs', 0) if cursor else 0
    values['ActiveSteps[1]/TimedOut'] = False
    return values

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
        wanted=sequence_status(self.app,self.unit,self.chart,{self.app.records[0].name:self.recipe})
        wanted.update({k:v for k,v in step_status(self.app,self.unit,self.chart).items() if k.startswith('CurrentStep/')})
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
        root=Path(__file__).resolve().parents[4]
        inventory=json.loads((root/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3C_INVENTORY_2026-10-22.json').read_text())
        self.assertEqual(len(inventory['paths']),647)

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
