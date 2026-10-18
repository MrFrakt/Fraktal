"""Consumed Unit profiling, fed by the sequence-view and finish boundaries."""
import hashlib
from pathlib import Path
from fraktal_tia_binding import PRIVATE,READONLY,REPO,type_source

TEMPLATE=Path(__file__).resolve().parents[1]/'Framework/Core/cycle_profile.scl.in'

def type_text(name,fields):
    return type_source(name,[dict(member=n,native_type=t,accessible=False,initial='') for n,t in fields.items()])

def names(t):
    stem=t.name.removeprefix('FB_')
    return 'FRK_Profiler_'+stem,'FRK_ProfileOwned_'+stem,'FRK_CycleProfile_'+stem

def declarations(t):
    return ['    Profiler'+READONLY+' : "'+names(t)[0]+'";',
            '    Starved'+READONLY+' : Bool;', '    Blocked'+READONLY+' : Bool;']

def build(model,catalog):
    from fraktal_tia_generate import db
    from fraktal_tia_config import function
    sources={}
    book={'Collecting':'Bool','Running':'Bool','HasOpen':'Bool','Invalid':'Bool','CompleteRequested':'Bool',
          'StartMs':'UDInt','OpenMs':'UDInt','OpenNo':'Int','OpenVisit':'UDInt',
          'OpenName':'String[120]','OpenClass':'DInt','OpenExpected':'Time','OpenStamp':'LDT',
          'CompletedNo':'Int','CompletedVisit':'UDInt','NSteps':'Int','Truncated':'Bool',
          'LastNSteps':'Int','LastTruncated':'Bool','StatsTruncated':'Bool','Head':'Int',
          'LastCycleTime':'Time','MinCycleTime':'Time','Current':'"ST_CycleSummary"','Last':'"ST_CycleSummary"'}
    sources['06_FRK_ProfileBook.udt']=type_text('FRK_ProfileBook',book)
    sources['07_FRK_ProfileScratch.db']=db('FRK_ProfileScratch',[
        'Summary'+PRIVATE+' : "ST_CycleSummary";','Step'+PRIVATE+' : "ST_StepTiming";'])
    data=[]
    for t in model.types:
        if not t.sequence_view:continue
        capacity=min(t.sequence_view[0],catalog.capacities['MAX_PROFILE_STEPS'])
        history=catalog.capacities['MAX_CYCLE_HISTORY']
        view,owned,cycle=names(t)
        fields={f['member']:f['native_type'] for f in catalog.resolve(['ST_CycleProfile'])['ST_CycleProfile']}
        fields['Steps']=f'Array[1..{capacity}] of "ST_StepTiming"'
        sources['07_'+cycle+'.udt']=type_source(cycle,[dict(member=n,native_type=ty,accessible=True,initial='') for n,ty in fields.items()])
        public={'LastCycle':'"'+cycle+'"','StepStats':f'Array[1..{capacity}] of "ST_TimingRow"',
                'StatsTruncated':'Bool','LastCycleTime':'Time','MinCycleTime':'Time',
                'History':f'Array[1..{history}] of "ST_CycleSummary"','HistoryHead':'Int'}
        sources['07_'+view+'.udt']=type_source(view,[dict(member=n,native_type=ty,accessible=True,initial='') for n,ty in public.items()])
        private={'Book':'"FRK_ProfileBook"','Steps':f'Array[1..{capacity}] of "ST_StepTiming"',
                 'LastSteps':f'Array[1..{capacity}] of "ST_StepTiming"','Stats':public['StepStats'],'History':public['History']}
        sources['07_'+owned+'.udt']=type_text(owned,private)
        data += ['P%03d'%i.index+PRIVATE+' : "'+owned+'";' for i in model.instances if i.type_name==t.name]
    sources['08_FRK_Profiles.db']=db('FRK_Profiles',data)
    text=TEMPLATE.read_text('ascii').replace('@E_TimeClass.WORK@',str(catalog.enums['E_TimeClass']['WORK']))
    operations={'Prepare':(['Run : Bool;','Withdraw : Bool;'],('Book',)),
        'Step':(['StepNo : DInt;','Visit : UDInt;','StepName : String;','TimeClass : DInt;',
                 'Expected : Time;','NowMs : UDInt;','Stamp : LDT;'],('Book','Steps','Stats')),
        'Complete':([],('Book',)),
        'End':(['StepNo : DInt;','Expected : Time;','NowMs : UDInt;'],('Book','Steps','LastSteps','Stats','History'))}
    lookup={t.name:t for t in model.types}
    for op,(inputs,members) in operations.items():
        body=['    CASE #Owner OF']
        for inst in model.instances:
            if not lookup[inst.type_name].sequence_view:continue
            prefix='"FRK_Profiles".P%03d.'%inst.index
            args={s.split(' : ')[0]:'#'+s.split(' : ')[0] for s in inputs}
            args.update({n:prefix+n for n in members})
            target='Request' if op=='Complete' else op
            body+=['        '+str(inst.index)+': "FRK_Profile'+target+'"('+', '.join(n+' := '+v for n,v in args.items())+');']
        body+=['        ELSE RETURN;','    END_CASE;']
        text+=function('FRK_SeqProfile'+op,['Owner : DInt;',*inputs],[],[],body)
    sources['18a_CycleProfile.scl']=text
    return sources,{p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (TEMPLATE,Path(__file__))}

def prepare(t,catalog,owner='#',withdraw=False):
    run='FALSE' if withdraw else owner+'Core.Exec = '+str(catalog.enums['E_ExecState']['BUSY'])+' AND '+owner+'Unit.Mode = '+str(catalog.enums['E_Mode']['AUTO'])
    return ['    "FRK_SeqProfilePrepare"(Owner := '+owner+'Core.RegIndex, Run := '+run+', Withdraw := '+('TRUE' if withdraw else owner+'Startup OR '+owner+'Core.EvModeChanged')+');']

def mirror(t,model,owner='#'):
    lines=['    CASE '+owner+'Core.RegIndex OF']
    for inst in model.instances:
        if inst.type_name!=t.name:continue
        prefix='"FRK_Profiles".P%03d.'%inst.index
        lines+=['        '+str(inst.index)+':']
        for n in ('CycleNo','Started','StartedTimeSynchronized','Total','WorkTime','WaitTime','ByClass'):
            lines+=['            '+owner+'Profiler.LastCycle.'+n+' := '+prefix+'Book.Last.'+n+';']
        for n,field in [('NSteps','Book.LastNSteps'),('Truncated','Book.LastTruncated'),('Steps','LastSteps')]:
            lines+=['            '+owner+'Profiler.LastCycle.'+n+' := '+prefix+field+';']
        for n,field in [('StepStats','Stats'),('StatsTruncated','Book.StatsTruncated'),('LastCycleTime','Book.LastCycleTime'),('MinCycleTime','Book.MinCycleTime'),('History','History'),('HistoryHead','Book.Head')]:
            lines+=['            '+owner+'Profiler.'+n+' := '+prefix+field+';']
    lines+=['        ELSE RETURN;','    END_CASE;']
    return lines
