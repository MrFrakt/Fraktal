"""Consumed-size Core 3.13 tables and generated ownership dispatch.

The owning Unit frame controls the scan/mode boundary. Sequence helpers record
visits, waits and annotations; applications do not schedule the view separately.
"""
import hashlib
import re
from pathlib import Path

from fraktal_tia_binding import PRIVATE, READONLY, REPO, type_source

TEMPLATE = Path(__file__).resolve().parents[1] / 'Framework/Core/sequence_view.scl.in'
PARAMS = {'Defs':'SequenceStepDef', 'Rows':'SequenceSteps', 'Cursors':'ActiveSteps',
          'Notes':'SequenceAnnotations', 'Count':'SequenceStepCount', 'NoteCount':'SequenceAnnotationCount',
          'Current':'CurrentStep', 'Book':'SequenceViewBook', 'Touched':'SequenceViewTouched',
          'Depths':'SequenceViewDepths', 'Visits':'SequenceViewVisits'}


def published_types(capacity, branches, annotations):
    return {'SequenceViewEnabled':'Bool', 'SequenceStepCount':'Int', 'SequenceAnnotationCount':'Int',
              'CurrentStep':'"ST_StepRecord"', 'CurrentStepElapsed':'Time', 'CurrentStepTimedOut':'Bool',
              'SequenceSteps':f'Array[1..{capacity}] of "ST_SequenceStep"',
              'ActiveSteps':f'Array[0..{branches}] of "ST_SequenceCursor"',
              'SequenceAnnotations':f'Array[1..{annotations}] of "ST_SequenceAnnotation"'}


def declarations(t):
    capacity, branches, annotations = t.sequence_view
    public = published_types(capacity, branches, annotations)
    private = {'SequenceStepDef':f'Array[1..{capacity}] of "ST_SequenceStepDef"'}
    return ['    '+n+(READONLY if n in public else PRIVATE)+' : '+v+';' for n,v in {**public,**private}.items()]


def frame_call(operation, t, model):
    args = {'Owner':'#Core.RegIndex'}
    if operation == 'Begin':
        args.update(Clear='#Startup OR #Core.EvModeChanged', ResetErrors='#Unit.EvReset', Enabled='#SequenceViewEnabled')
    else:
        args.update(Revision='#ConfigRev')
    lines = ['    "FRK_SeqView'+operation+'"('+', '.join(n+' := '+v for n,v in args.items())+');']
    if operation == 'End':
        lines += mirror(t, model)
    return '\n'.join(lines)


def mirror(t, model, owner='#'):
    """One generated publication map for normal scans and cold quiescence."""
    lines=['    CASE '+owner+'Core.RegIndex OF']
    for inst in model.instances:
        if inst.type_name != t.name: continue
        prefix='"FRK_Views".V%03d.'%inst.index
        lines.append('        '+str(inst.index)+':')
        for n in ('Defs','Rows','Cursors','Notes','Count','NoteCount','Current'):
            lines.append('            '+owner+PARAMS[n]+' := '+prefix+n+';')
        lines += ['            '+owner+'CurrentStepElapsed := '+prefix+'Cursors[0].Elapsed;',
                  '            '+owner+'CurrentStepTimedOut := '+prefix+'Cursors[0].TimedOut;']
    return lines+['        ELSE '+owner+'SequenceViewEnabled := FALSE;', '    END_CASE;']


def build(model, catalog):
    from fraktal_tia_config import function
    sources = {}
    sources['06_FRK_ViewBook.udt'] = type_source('FRK_ViewBook', [
        {'member':n,'native_type':t,'accessible':False,'initial':''} for n,t in
        [('Dirty','Bool'),('ChangedMs','UDInt'),('Overflow','Bool'),('CondIndex','Int'),('PendingFound','Bool')]])
    sources['07_FRK_ViewScratch.db'] = '\n'.join(['DATA_BLOCK "FRK_ViewScratch"',
        "{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1','NON_RETAIN','VAR',
        *['    '+n+PRIVATE+' : "'+t+'";' for n,t in [('Def','ST_SequenceStepDef'),('Row','ST_SequenceStep'),
            ('Cursor','ST_SequenceCursor'),('Note','ST_SequenceAnnotation'),('Step','ST_StepRecord')]],
        'END_VAR','BEGIN','END_DATA_BLOCK',''])
    authority = REPO/'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Params/PL_Fraktal.TcGVL'
    settle = int(re.search(r'CHART_REV_SETTLE_MS\s*:\s*DWORD\s*:=\s*(\d+)',authority.read_text('utf-8-sig'),re.I)[1])
    fields = []
    for f in catalog.resolve(['ST_SequenceStepDef'])['ST_SequenceStepDef']:
        member = f['member']; value = '#Defs[#Index].'+member
        text = ('STRING_TO_WSTRING('+value+')' if f['native_type'].startswith('String') else
                'DINT_TO_WSTRING(TIME_TO_DINT('+value+'))' if f['native_type'] == 'Time' else
                'INT_TO_WSTRING('+value+')' if f['native_type'] == 'Int' else 'DINT_TO_WSTRING('+value+')')
        value_type = catalog.enums['E_ConfigValueType']['TEXT' if f['native_type'].startswith('String') else 'NUMBER']
        fields += ["        #Item := CONCAT(IN1 := #Prefix, IN2 := '"+member+"');",
            '        "FRK_ConfigAppend"(Scope := #Scope, Item := #Item, ValueText := '+text+', ValueType := '+str(value_type)+', ReadLevel := #ReadLevel, Readable := #Readable, Cursor := #Cursor, Page := #Page);']
    sources['17_SequenceView.scl'] = TEMPLATE.read_text('ascii').replace('@SETTLE_MS@',str(settle)).replace('@MANIFEST_FIELDS@','\n'.join(fields)).replace('@MAX_STEP_CONDS@',str(catalog.capacities['MAX_STEP_CONDS']))
    operations = {
        'Step':(['StepNo : DInt;', 'Branch : DInt;', 'Depth : Int;', 'Visit : UDInt;',
                 'StepName : String;', 'AwaitingLabel : String;', 'AwaitsPath : String;',
                 'TimeClass : DInt;', 'ExpectedTime : Time;', 'Elapsed : Time;'], 'Record'),
        'Await':(['StepNo : DInt;', 'Branch : DInt;', 'Label : String;', 'Ok : Bool;'], 'Await'),
        'Note':(['StepNo : DInt;', 'Branch : DInt;', 'IsError : Bool;', 'Key : String;', 'SourcePath : String;'], 'Note')}
    operations.update({'Begin':(['Clear : Bool;', 'ResetErrors : Bool;'],'Begin'), 'End':([], 'End'), 'Withdraw':([], 'Withdraw')})
    lookup = {t.name:t for t in model.types}
    owners=[]
    for t in model.types:
        if not t.sequence_view: continue
        capacity,branches,annotations=t.sequence_view
        shape={'Defs':f'Array[1..{capacity}] of "ST_SequenceStepDef"','Rows':f'Array[1..{capacity}] of "ST_SequenceStep"',
               'Cursors':f'Array[0..{branches}] of "ST_SequenceCursor"','Notes':f'Array[1..{annotations}] of "ST_SequenceAnnotation"',
               'Count':'Int','NoteCount':'Int','Current':'"ST_StepRecord"','Book':'"FRK_ViewBook"',
               'Touched':f'Array[0..{branches}] of Bool','Depths':f'Array[0..{branches}] of Int','Visits':f'Array[1..{capacity}] of UDInt'}
        name='FRK_ViewOwned_'+t.name.removeprefix('FB_')
        sources['07_'+name+'.udt']=type_source(name,[{'member':n,'native_type':ty,'accessible':False,'initial':''} for n,ty in shape.items()])
        owners += ['V%03d'%i.index+PRIVATE+' : "'+name+'";' for i in model.instances if i.type_name==t.name]
    from fraktal_tia_generate import db
    sources['08_FRK_Views.db']=db('FRK_Views',owners)
    bindings = []
    for op,(inputs,target) in operations.items():
        body = ['    CASE #Owner OF']
        for inst in model.instances:
            if not lookup[inst.type_name].sequence_view: continue
            prefix = '"FRK_Views".V%03d.'%inst.index
            args = {re.match(r'(\w+)',d)[1]:'#'+re.match(r'(\w+)',d)[1] for d in inputs}
            used = PARAMS if op in ('Step','Begin') else {n:PARAMS[n] for n in
                (('Defs','Cursors','Count','Current','Book') if op == 'Await' else
                 ('Cursors','Book','Touched','Current') if op == 'End' else ('Defs','Rows','Notes','Count','NoteCount'))}
            if op == 'Withdraw':used={n:PARAMS[n] for n in ('Cursors','Book','Touched','Current')}
            args.update({n:prefix+n for n in used})
            if op == 'Begin':args['Enabled']='#Enabled'
            if op == 'End':args.update(Revision='#Revision')
            body.append('        '+str(inst.index)+': "FRK_View'+target+'"('+', '.join(n+' := '+v for n,v in args.items())+');')
        body += ['        ELSE RETURN;', '    END_CASE;']
        bindings.append(function('FRK_SeqView'+op, ['Owner : DInt;',*inputs],
            ['Enabled : Bool;'] if op=='Begin' else ['Revision : UDInt;'] if op=='End' else [], [], body))
    # Neither helpers nor chart FCs depend on the root FB's native GRAPH type.
    sources['17_SequenceView.scl'] += '\n'.join(bindings)
    return sources, {p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (TEMPLATE,authority,Path(__file__))}
