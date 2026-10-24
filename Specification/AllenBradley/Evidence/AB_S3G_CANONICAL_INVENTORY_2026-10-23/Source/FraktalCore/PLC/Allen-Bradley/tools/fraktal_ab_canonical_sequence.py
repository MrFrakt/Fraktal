"""S3c PLC publication: config definitions, on-demand history, live cursor.

The existing Chart owns all visit/history facts. This publication reads those
facts after the owning services; it neither runs a sequence nor accumulates it.
"""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_status as diagnostic
import fraktal_ab_canonical_unit_core as core

P=pub.PREFIX
DEFINITION=P+'StepDefS3cV62'
DEFINITIONS=P+'StepDefTableS3cV62'
HISTORY=P+'StepHistoryS3cV62'
NOTE=P+'StepNoteS3cV62'
CURSOR=P+'StepCursorS3cV62'
STATE=P+'SeqStateS3cV62'
AUTHORED=P+'AuthoredStepS3cV62'
SOURCE=P+'StepSourceS3cV62'
CONDITION=P+'StepCondS3cV62'
CURRENT=P+'CurrentStepS3cV62'


def slots(app):return min(max((len(c.steps) for c in app.chains),default=0),app.chart_steps)
def definition_tag(app):return f'FRK_{app.name}_SequenceDefinitions'
def source_tag(app):return f'FRK_{app.name}_CanonicalStepSource'
def state_tag(app):return f'FRK_{app.name}_CanonicalSequenceState'
def zero_tag(app):return f'FRK_{app.name}_CanonicalStepZero'


def authored_steps(app):
    # The migration oracle exposes the first declared chain for each mode.
    # Reused step numbers in different modes keep separate definitions.
    seen=set();result=[]
    for chain in app.chains:
        if chain.mode_ordinal in seen:continue
        seen.add(chain.mode_ordinal)
        result.extend((chain.mode_ordinal,step) for step in chain.steps)
    return result


def bindings(app):return [dict(SourceSymbol=definition_tag(app),TargetRoot=app.name)]


def validate(app):
    import fraktal_ab_manifest as manifest
    findings=[]
    if not 1<=slots(app)<=core.core_limit('MAX_SEQUENCE_STEPS'):
        findings.append('S3c requires declared steps within the Core sequence capacity')
    for chain in app.chains:
        for step in chain.steps:
            texts=((f'project.step.{step.name}',120),
                (f'{step.module}.{step.command}' if step.module and step.command else '',120),
                (f'{app.name}.{step.module}' if step.module else '',80))
            if any(len(text.encode('utf-8'))>width for text,width in texts):
                findings.append('canonical step definition exceeds Core text width')
            import fraktal_ab_declaration as decl
            if any(len(label.encode('utf-8'))>120 for unused,label in decl.step_conditions(step)):
                findings.append('canonical step condition exceeds Core label width 120')
    if any(len(manifest.reason_key(app,name).encode('utf-8'))>120 for name in app.reasons):
        findings.append('canonical sequence annotation exceeds Core key width 120')
    return findings


def augment(app,definitions):
    M=pub.Member;n=slots(app)
    definitions[DEFINITION]=(M('StepNo','DINT'),M('Branch','DINT'),M('TimeClass','DINT','ENUM'),
        M('ExpectedTime','DINT','DURATION'),M('StepName',pub.string_type(120)),
        M('AwaitingLabel',pub.string_type(120)),M('AwaitsPath',pub.string_type(80)))
    definitions[DEFINITIONS]=(M('SequenceSteps',DEFINITION,count=n,lower=1),)
    definitions[AUTHORED]=(M('Mode','DINT'),M('ChartIndex','DINT'),M('Definition',DEFINITION),
                          M('Labels',pub.string_type(120),count=core.core_limit('MAX_STEP_CONDS')))
    definitions[SOURCE]=(M('Entries',AUTHORED,count=len(authored_steps(app))),)
    definitions[HISTORY]=(M('Visited','BOOL'),M('LastDuration','DINT','DURATION'),
                          M('ErrorActive','BOOL'),M('WarningActive','BOOL'))
    definitions[NOTE]=(M('RowIdx','DINT'),M('IsError','BOOL'),M('Key',pub.string_type(120)),
                       M('SourcePath',pub.string_type(80)))
    definitions[CURSOR]=(M('RowIdx','DINT'),M('Elapsed','DINT','DURATION'),M('TimedOut','BOOL'))
    definitions[CONDITION]=(M('Label',pub.string_type(120)),M('Ok','BOOL'))
    definitions[CURRENT]=(M('StepNo','DINT'),M('StepName',pub.string_type(120)),M('AwaitingLabel',pub.string_type(120)),
        M('ExpectedTime','DINT','DURATION'),M('TimeClass','DINT','ENUM'),
        M('Conds',CONDITION,count=core.core_limit('MAX_STEP_CONDS'),lower=1))
    definitions[pub.root_type(app)]=tuple(M(m.name,CURRENT) if m.name=='CurrentStep' else m
                                          for m in definitions[pub.root_type(app)])
    definitions[pub.root_type(app)] += (M('SequenceViewEnabled','BOOL'),M('SequenceStepCount','DINT'),
        M('SequenceAnnotationCount','DINT'),M('SequenceSteps',HISTORY,count=n,lower=1),
        M('SequenceAnnotations',NOTE,count=n,lower=1),M('ActiveSteps',CURSOR,count=1),
        M('CurrentStepElapsed','DINT','DURATION'),M('CurrentStepTimedOut','BOOL'))
    definitions[STATE]=tuple(M(name,'DINT') for name in (
        'Initialized','LastEpoch','LastCount','LastMode','Count','SlotIndex','StepIndex','BestStep',
        'PreviousRow','BestRow','NoteIndex','ByteIndex','Changed','Expected','ChartIndex',
        'CurrentSelected','CurrentOf','ConditionsSelected','ConditionsOf','CurrentIndex','ConditionIndex'))+tuple(
        M(name,'DINT',count=n) for name in ('RowMap','DefinitionOf','NoteReason','NoteSource','NoteRow'))


def initialize(app,values):values['SequenceViewEnabled']=bool(app.chains)


def tags(app,serialize):
    import fraktal_ab_generate as gen
    import fraktal_ab_declaration as decl
    order=gen.ordered_steps(app)
    static=[dict(Mode=mode,ChartIndex=order.index(step.number),Definition=dict(StepNo=step.number,
        Branch=0,TimeClass=decl.TIME_CLASSES.index(step.time_class),StepName=f'project.step.{step.name}',
        AwaitingLabel=f'{step.module}.{step.command}' if step.module and step.command else '',
        AwaitsPath=f'{app.name}.{step.module}' if step.module else ''),
        Labels=[(decl.step_conditions(step)[i][1] if i<len(decl.step_conditions(step)) else '')
                for i in range(core.core_limit('MAX_STEP_CONDS'))]) for mode,step in authored_steps(app)]
    # The immutable source has one entry per authored step; the public record
    # is the discovered, mode-scoped row order and is copied only on changes.
    return [serialize(definition_tag(app),DEFINITIONS,{}),
        serialize(source_tag(app),SOURCE,dict(Entries=static),access='None'),
        serialize(state_tag(app),STATE,{},access='None'),
        serialize(zero_tag(app),DEFINITION,{},access='None')]


def cyclic(app):
    import fraktal_ab_generate as gen
    import fraktal_ab_declaration as decl
    n=slots(app);order=gen.ordered_steps(app)
    root=app.name;unit=f'FRK_{root}_Unit';chart=f'FRK_{root}_Chart'
    state=state_tag(app);defs=definition_tag(app)+'.SequenceSteps';source=source_tag(app)+'.Entries'
    index=state+'.SlotIndex';step=state+'.StepIndex';note=state+'.NoteIndex'
    chart_index=state+'.ChartIndex';source_index=f'{source}[{step}].ChartIndex'
    source_def=f'{source}[{step}].Definition'
    row=f'{root}.SequenceSteps[{index}]';definition=f'{defs}[{index}]'
    lines=[f'{state}.Changed := 0;',
        f'IF ({chart}.RowCount < 0) OR ({chart}.RowCount > {app.chart_steps}) THEN',
        f'{pub.header_tag(app)}.Valid := 0;','ELSE',
        f'IF ({state}.Initialized = 0) OR ({state}.LastEpoch <> {chart}.RowEpoch) OR',
        f'({state}.LastCount <> {chart}.RowCount) OR ({state}.LastMode <> {unit}.Mode) THEN',
        f'{state}.Count := 0;',f'{state}.PreviousRow := 0;',
        f'FOR {index} := 0 TO {n-1} DO',f'{state}.RowMap[{index}] := 0;',
        f'{state}.BestRow := 2147483647;',f'{state}.BestStep := 0;',
        f'FOR {step} := 0 TO {len(authored_steps(app))-1} DO',
        f'{chart_index} := {source_index};',
        f'IF ({source}[{step}].Mode = {unit}.Mode) AND ({chart}.RowEpochOf[{chart_index}] = {chart}.RowEpoch) AND',
        f'({chart}.RowOf[{chart_index}] > {state}.PreviousRow) AND ({chart}.RowOf[{chart_index}] <= {chart}.RowCount) AND',
        f'({chart}.RowOf[{chart_index}] < {state}.BestRow) THEN',
        f'{state}.BestRow := {chart}.RowOf[{chart_index}];',f'{state}.BestStep := {step} + 1;',
        'END_IF;','END_FOR;',f'IF {state}.BestStep <> 0 THEN',
        f'{state}.RowMap[{index}] := {state}.BestStep;',f'{state}.Count := {state}.Count + 1;',
        f'{state}.PreviousRow := {state}.BestRow;','END_IF;','END_FOR;',
        f'{state}.LastEpoch := {chart}.RowEpoch;',f'{state}.LastCount := {chart}.RowCount;',
        f'{state}.LastMode := {unit}.Mode;',f'{state}.Initialized := 1;','END_IF;',
        f'{root}.SequenceStepCount := {state}.Count;',f'{root}.ActiveSteps[0].RowIdx := 0;',
        f'{root}.ActiveSteps[0].Elapsed := 0;',f'{root}.ActiveSteps[0].TimedOut := 0;',
        f'{note} := 0;',f'FOR {index} := 0 TO {n-1} DO',
        f'{row}.Visited := 0;',f'{row}.LastDuration := 0;',f'{row}.ErrorActive := 0;',f'{row}.WarningActive := 0;',
        f'IF {state}.RowMap[{index}] <> 0 THEN',f'{step} := {state}.RowMap[{index}] - 1;',
        f'{chart_index} := {source_index};',
        f'IF {state}.DefinitionOf[{index}] <> {state}.RowMap[{index}] THEN',
        f'CPS({source_def},{definition},1);',f'{state}.DefinitionOf[{index}] := {state}.RowMap[{index}];',
        f'{state}.Changed := 1;','END_IF;',
        f'{state}.Expected := 0;']
    expected=[(i,decl.expected_member(s)) for i,(unused,s) in enumerate(authored_steps(app)) if decl.expected_member(s)]
    if expected:
        lines += [f'CASE {step} OF']
        lines += [f'{i}: {state}.Expected := {app.records[0].name}Tag.{member};' for i,member in expected]
        lines += ['ELSE','(* Steps with no recipe guard publish zero. *)','END_CASE;']
    lines += [f'IF {definition}.ExpectedTime <> {state}.Expected THEN',
        f'{definition}.ExpectedTime := {state}.Expected;',f'{state}.Changed := 1;','END_IF;',
        f'{row}.Visited := 1;',f'{row}.LastDuration := {chart}.LastMs[{chart_index}];',
        f'{row}.WarningActive := {chart}.WarnReason[{chart_index}] <> 0;',
        f'IF ({unit}.Running <> 0) AND ({unit}.Error = 0) AND',
        f'({chart}.ActiveStepNumber = {unit}.Step) AND ({definition}.StepNo = {unit}.Step) THEN',
        f'{root}.ActiveSteps[0].RowIdx := {index} + 1;',f'{root}.ActiveSteps[0].Elapsed := {chart}.CurrentStepMs;','END_IF;',
        f'IF {chart}.WarnReason[{chart_index}] <> 0 THEN']
    target=f'{root}.SequenceAnnotations[{note}]'
    lines += [f'{target}.RowIdx := {index} + 1;',f'{target}.IsError := 0;',
        f'IF ({state}.NoteReason[{note}] <> {chart}.WarnReason[{chart_index}]) OR',
        f'({state}.NoteSource[{note}] <> {chart}.WarnSource[{chart_index}]) OR',
        f'({state}.NoteRow[{note}] <> {index} + 1) THEN']
    work=diagnostic.work_tag(app);inputs=work+'.Inputs'
    # Reuse the one reason-key resolver. The annotation has no onset or I/O
    # join; zeroing all other inputs prevents stale diagnostic work leaking in.
    lines += [f'{inputs}.{name} := 0;' for name in diagnostic.INPUT_NAMES]
    lines += [f'{inputs}.Reason := {chart}.WarnReason[{chart_index}];',f'JSR({diagnostic.routine_name(app)},0);',
        f'{target}.Key.LEN := {work}.Diagnostic.Description.LEN;',
        f'FOR {state}.ByteIndex := 0 TO {target}.Key.LEN - 1 DO',
        f'{target}.Key.DATA[{state}.ByteIndex] := {work}.Diagnostic.Description.DATA[{state}.ByteIndex];','END_FOR;',
        f'{target}.SourcePath.LEN := 0;',f'CASE {chart}.WarnSource[{chart_index}] OF']
    for ordinal,module in enumerate((None,*app.modules)):
        source_path=root+('.'+module.name if module else '')+'.Status.Name'
        lines += [f'{ordinal}:',f'{target}.SourcePath.LEN := {source_path}.LEN;',
            f'FOR {state}.ByteIndex := 0 TO {target}.SourcePath.LEN - 1 DO',
            f'{target}.SourcePath.DATA[{state}.ByteIndex] := {source_path}.DATA[{state}.ByteIndex];','END_FOR;']
    lines += ['ELSE','(* Unknown source has no invented drill-down path. *)','END_CASE;',
        f'{state}.NoteReason[{note}] := {chart}.WarnReason[{chart_index}];',
        f'{state}.NoteSource[{note}] := {chart}.WarnSource[{chart_index}];',f'{state}.NoteRow[{note}] := {index} + 1;',
        'END_IF;',f'{note} := {note} + 1;','END_IF;','ELSE',
        f'IF {state}.DefinitionOf[{index}] <> 0 THEN',f'CPS({zero_tag(app)},{definition},1);',f'{state}.Changed := 1;',
        'END_IF;',f'{state}.DefinitionOf[{index}] := 0;','END_IF;','END_FOR;',f'{root}.SequenceAnnotationCount := {note};',
        f'{step} := {note};',f'FOR {note} := {step} TO {n-1} DO',f'{target}.RowIdx := 0;',f'{target}.IsError := 0;',
        f'{target}.Key.LEN := 0;',f'{target}.SourcePath.LEN := 0;',
        f'{state}.NoteReason[{note}] := 0;',f'{state}.NoteSource[{note}] := 0;',f'{state}.NoteRow[{note}] := 0;',
        'END_FOR;',f'IF {state}.Changed <> 0 THEN',
        f'IF {pub.header_tag(app)}.FragmentRevision >= 2147483646 THEN',f'{pub.header_tag(app)}.FragmentRevision := 0;','END_IF;',
        f'{pub.header_tag(app)}.FragmentRevision := {pub.header_tag(app)}.FragmentRevision + 1;','END_IF;','END_IF;']
    return lines+current_logic(app)


def current_logic(app):
    state=state_tag(app);root=app.name;unit=f'FRK_{root}_Unit';chart=f'FRK_{root}_Chart'
    source=source_tag(app)+'.Entries';i=state+'.CurrentIndex';c=state+'.ConditionIndex'
    current=root+'.CurrentStep';count=core.core_limit('MAX_STEP_CONDS')
    lines=[f'{root}.CurrentStepElapsed := {chart}.CurrentStepMs;',
        f'{root}.CurrentStepTimedOut := {unit}.StepTimedOut <> 0;',f'{state}.CurrentSelected := 0;',
        f'FOR {i} := 0 TO {len(authored_steps(app))-1} DO',
        f'IF ({source}[{i}].Mode = {unit}.Mode) AND ({source}[{i}].Definition.StepNo = {unit}.Step) THEN',
        f'{state}.CurrentSelected := {i} + 1;','END_IF;','END_FOR;',
        f'IF {state}.CurrentOf <> {state}.CurrentSelected THEN',
        f'{current}.StepName.LEN := 0;',f'{current}.AwaitingLabel.LEN := 0;',f'{current}.TimeClass := 0;',
        f'IF {state}.CurrentSelected <> 0 THEN',f'{i} := {state}.CurrentSelected - 1;',
        f'CPS({source}[{i}].Definition.StepName,{current}.StepName,1);',
        f'CPS({source}[{i}].Definition.AwaitingLabel,{current}.AwaitingLabel,1);',
        f'{current}.TimeClass := {source}[{i}].Definition.TimeClass;','END_IF;',
        f'{state}.CurrentOf := {state}.CurrentSelected;','END_IF;',f'{current}.ExpectedTime := 0;',
        f'IF {state}.CurrentSelected <> 0 THEN {current}.ExpectedTime := {unit}.StepExpectedMs; END_IF;',
        f'{state}.ConditionsSelected := 0;',
        f'IF {chart}.ActiveStepNumber = {unit}.Step THEN {state}.ConditionsSelected := {state}.CurrentSelected; END_IF;',
        f'IF {state}.ConditionsOf <> {state}.ConditionsSelected THEN',
        f'FOR {c} := 0 TO {count-1} DO',f'{current}.Conds[{c}].Label.LEN := 0;',
        f'IF {state}.ConditionsSelected <> 0 THEN',f'{i} := {state}.ConditionsSelected - 1;',
        f'CPS({source}[{i}].Labels[{c}],{current}.Conds[{c}].Label,1);',
        'END_IF;','END_FOR;',f'{state}.ConditionsOf := {state}.ConditionsSelected;','END_IF;',
        f'FOR {c} := 0 TO {count-1} DO',f'{current}.Conds[{c}].Ok := 0;',
        f'IF {state}.ConditionsSelected <> 0 THEN',
        f'{current}.Conds[{c}].Ok := ({current}.Conds[{c}].Label.LEN > 0) AND ({chart}.CondOk[{c}] <> 0);',
        'END_IF;','END_FOR;']
    return lines
