"""S3g engineering schema for consumed Core OEE/profiler/health fields.

The existing scan services own accounting and history. Unsigned Core fields
use the same complete-DINT-bit representation as S3f revisions; the generic
manifest decoder already exposes those bits as UInt32.
"""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_unit_core as core
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen

P=pub.PREFIX
OEE=P+'OeeS3gV63'
SAMPLE=P+'OeeSampleS3gV63'
STEP=P+'StepTimingS3gV63'
STATS=P+'TimingRowS3gV63'
CYCLE=P+'CycleProfileS3gV63'
SUMMARY=P+'CycleSummaryS3gV63'
PROFILER=P+'ProfilerS3gV63'
QUALITY=P+'TimeQualityS3gV63'
HEALTH=P+'SystemHealthS3gV63'
WORK=P+'MetricsWorkS3gV63'
LABEL=P+'MetricsLabelS3gV63'
LABELS=P+'MetricsLabelsS3gV63'


def state_tag(app):return f'FRK_{app.name}_CanonicalMetricsState'
def labels_tag(app):return f'FRK_{app.name}_CanonicalMetricsLabels'


def first_steps(app):
    result={}
    for chain in app.chains:
        for step in chain.steps:result.setdefault(step.number,step)
    return tuple(result.values())


def validate(app):
    findings=[]
    if gen.PROFILE_STEPS!=core.core_limit('MAX_PROFILE_STEPS') or gen.CYCLE_HISTORY!=core.core_limit('MAX_CYCLE_HISTORY') or gen.OEE_SAMPLES!=core.core_limit('MAX_OEE_SAMPLES'):
        findings.append('S3g profile/history/trend bounds differ from Core')
    for step in first_steps(app):
        if type(step.number) is not int or not -32768<=step.number<=32767:
            findings.append('S3g waterfall StepNo exceeds Core INT range')
        if len(('project.step.'+step.name).encode('utf-8'))>120:
            findings.append('S3g profiler label exceeds Core STRING(120)')
    return findings


def augment(app,definitions):
    M=pub.Member;S=pub.string_type
    duration=lambda name:M(name,'DINT','DURATION')
    unsigned=lambda name:M(name,'DINT','BITSTRING32')
    factors=tuple(m for name in ('Availability','Performance','Quality','Oee')
        for m in (M(name,'REAL'),M({'Availability':'AvailValid','Performance':'PerfValid','Quality':'QualValid','Oee':'OeeValid'}[name],'BOOL')))
    definitions[OEE]=tuple(unsigned(name) for name in ('RunMs','DownMs','IdleMs'))+factors
    definitions[SAMPLE]=(M('Oee','REAL'),M('OeeValid','BOOL'))
    definitions[STEP]=(M('StepNo','INT'),M('StepName',S(120)),M('TimeClass','DINT','ENUM'),duration('Duration'),duration('Expected'))
    definitions[STATS]=(M('Id','DINT'),M('Label',S(120)),M('TimeClass','DINT','ENUM'),unsigned('Count'),duration('Avg'),duration('Maximum'))
    definitions[CYCLE]=(unsigned('CycleNo'),M('NSteps','INT'),duration('Total'),duration('WorkTime'),duration('WaitTime'),M('Steps',STEP,count=gen.PROFILE_STEPS,lower=1))
    definitions[SUMMARY]=(unsigned('CycleNo'),duration('Total'),duration('WorkTime'),duration('WaitTime'),M('ByClass','DINT','DURATION',count=len(decl.TIME_CLASSES)))
    definitions[PROFILER]=(M('LastCycle',CYCLE),M('StepStats',STATS,count=gen.PROFILE_STEPS,lower=1),duration('LastCycleTime'),duration('MinCycleTime'),M('HistoryHead','INT'),M('History',SUMMARY,count=gen.CYCLE_HISTORY,lower=1))
    definitions[QUALITY]=(M('Available','BOOL'),M('Synchronized','BOOL'),M('Source',S(32)),M('OffsetUs','DINT'))
    definitions[HEALTH]=(M('Present','BOOL'),M('Healthy','BOOL'),M('TaskAvailable','BOOL'),unsigned('TaskCycleUs'),unsigned('TaskJitterUs'),M('TaskOverrun','BOOL'),
        M('ControllerAvailable','BOOL'),M('CpuLoadPct','LREAL'),unsigned('MemoryAvailableMb'),M('IpcAvailable','BOOL'),M('IpcTemperatureC','LREAL'),M('FanHealthy','BOOL'),M('StorageHealthPct','LREAL'),
        M('FieldbusAvailable','BOOL'),M('FieldbusMasterHealthy','BOOL'),unsigned('LostFrameCount'),unsigned('SlaveErrorCount'),M('DcAvailable','BOOL'),M('DcSynchronized','BOOL'),M('TimeQuality',QUALITY))
    definitions[pub.root_type(app)]+=(M('Oee',OEE),M('OeeTrend',SAMPLE,count=gen.OEE_SAMPLES,lower=1),M('OeeTrendHead','INT'),M('Profiler',PROFILER))
    if app.system_health is not None:definitions[pub.root_type(app)]+=(M('SystemHealth',HEALTH),)
    definitions[LABEL]=(M('StepNo','DINT'),M('Label',S(120)),M('TimeClass','DINT'))
    definitions[LABELS]=(M('Entries',LABEL,count=max(1,len(first_steps(app)))),)
    definitions[WORK]=tuple(M(name,'DINT') for name in ('Initialized','Index','Slot','Buffer','LookupStep','LookupIndex','Found','SeenCycles','SeenHead','SeenEpoch','SeenTrendHead'))+(
        M('SeenCounts','DINT',count=gen.PROFILE_STEPS),M('StepName',S(120)),M('TimeClass','DINT'),
        M('Factors',OEE),M('EmptyStep',STEP),M('EmptyStats',STATS)) + tuple(
        M(name,'LINT') for name in ('Wrap','SignedEdge','Run','Down','Idle','Good','Nok','Total','Denominator','Ideal')) + tuple(
        M(name,'REAL') for name in ('RunReal','GoodReal','TotalReal','DenominatorReal','IdealReal'))


def initialize(app,result):
    result.update(Oee={},OeeTrendHead=0,Profiler={})
    if app.system_health is not None:result['SystemHealth']={}


def tags(app,serialize):
    labels=[dict(StepNo=step.number,Label='project.step.'+step.name,TimeClass=decl.TIME_CLASSES.index(step.time_class)) for step in first_steps(app)]
    return [serialize(state_tag(app),WORK,{},access='None'),serialize(labels_tag(app),LABELS,dict(Entries=labels or [{}]),access='None')]


def health(app):
    """Mirror the existing validated health owner, retaining unavailable groups."""
    if app.system_health is None:return []
    target=app.name+'.SystemHealth';source=gen.system_health_tag(app);probe=gen.health_probe_tag(app)
    lines=[f'{target}.{name} := {source}.{name} <> 0;' for name in ('Present','Healthy','TaskAvailable','TaskOverrun')]
    lines += [f'{target}.TaskCycleUs := {probe}.IntervalUs;',f'{target}.TaskJitterUs := {probe}.JitterUs;']
    lines += [f'{target}.{name} := 0;' for name in ('ControllerAvailable','CpuLoadPct','MemoryAvailableMb','IpcAvailable','IpcTemperatureC','FanHealthy','StorageHealthPct',
        'FieldbusAvailable','FieldbusMasterHealthy','LostFrameCount','SlaveErrorCount','DcAvailable','DcSynchronized')]
    lines += [f'{target}.TimeQuality.Available := 1;',f'{target}.TimeQuality.Synchronized := {probe}.TimeIsSynchronized <> 0;',
        f'{target}.TimeQuality.OffsetUs := 0;',f'{target}.TimeQuality.Source.LEN := 0;',f'IF {probe}.TimePtpEnable <> 0 THEN']
    lines += core.put_text(target+'.TimeQuality.Source','PTP',32)+['END_IF;']
    return lines


def factor_routine(app):return f'FRK_{app.name}_CanonicalOeeFactors'
def lookup_routine(app):return f'FRK_{app.name}_CanonicalMetricLabel'


def factor_logic(app):
    """One native REAL implementation for the live figure and every sample.

    LINT intermediates make the unsigned operations explicit, including the
    modulo before each Core UDINT-to-REAL conversion. REAL cells round every
    arithmetic operation separately, as the Core REAL contract requires.
    """
    w=state_tag(app);f=w+'.Factors';lines=[]
    for name in ('Run','Down','Idle','Good','Nok'):
        lines += [f'{w}.{name} := {w}.{name} MOD {w}.Wrap;',
            f'IF {w}.{name} < 0 THEN {w}.{name} := {w}.{name} + {w}.Wrap; END_IF;']
    for target,expression in (('Total','Good + '+w+'.Nok'),('Denominator','Run + '+w+'.Down')):
        lines += [f'{w}.{target} := ({w}.{expression}) MOD {w}.Wrap;']
    for name in ('Run','Down','Idle'):
        lines += [f'IF {w}.{name} >= {w}.SignedEdge THEN',
            f'{f}.{name}Ms := {w}.{name} - {w}.Wrap;',
            'ELSE',f'{f}.{name}Ms := {w}.{name};','END_IF;']
    for name in ('Run','Good','Total','Denominator','Ideal'):
        lines += [f'{w}.{name}Real := {w}.{name};']
    lines += [f'{f}.AvailValid := {w}.Denominator > 0;',f'{f}.Availability := 0;',
        f'IF {f}.AvailValid THEN {f}.Availability := {w}.RunReal / {w}.DenominatorReal; END_IF;',
        f'{f}.PerfValid := ({w}.Ideal > 0) AND ({w}.Run > 0);',f'{f}.Performance := 0;',
        f'IF {f}.PerfValid THEN',f'{f}.Performance := {w}.IdealReal * {w}.TotalReal;',
        f'{f}.Performance := {f}.Performance / {w}.RunReal;',
        f'IF {f}.Performance > 1 THEN {f}.Performance := 1; END_IF;','END_IF;',
        f'{f}.QualValid := {w}.Total > 0;',f'{f}.Quality := 0;',
        f'IF {f}.QualValid THEN {f}.Quality := {w}.GoodReal / {w}.TotalReal; END_IF;',
        f'{f}.Oee := 1;',f'{f}.OeeValid := 0;']
    for valid,name in (('AvailValid','Availability'),('PerfValid','Performance'),('QualValid','Quality')):
        lines += [f'IF {f}.{valid} THEN',f'{f}.Oee := {f}.Oee * {f}.{name};',f'{f}.OeeValid := 1;','END_IF;']
    return lines+[f'IF NOT {f}.OeeValid THEN {f}.Oee := 0; END_IF;']


def lookup_logic(app):
    w=state_tag(app);table=labels_tag(app)
    return [f'{w}.StepName.LEN := 0;',f'{w}.TimeClass := 0;',f'{w}.Found := 0;',
        f'FOR {w}.LookupIndex := 0 TO {len(first_steps(app))-1} DO',
        f'IF ({w}.Found = 0) AND ({table}.Entries[{w}.LookupIndex].StepNo = {w}.LookupStep) THEN',
        f'CPS({table}.Entries[{w}.LookupIndex].Label,{w}.StepName,1);',
        f'{w}.TimeClass := {table}.Entries[{w}.LookupIndex].TimeClass;',f'{w}.Found := 1;',
        'END_IF;','END_FOR;'] if first_steps(app) else [f'{w}.StepName.LEN := 0;',f'{w}.TimeClass := 0;']


def routines(app):return [(factor_routine(app),factor_logic(app)),(lookup_routine(app),lookup_logic(app))]


def cyclic(app):
    root=app.name;w=state_tag(app);o=gen.oee_tag(app);p=gen.profiler_tag(app)
    unit=f'FRK_{app.name}_Unit';f=w+'.Factors';index=w+'.Index';slot=w+'.Slot'
    lines=[f'IF S:FS THEN {w}.Initialized := 0; END_IF;',
        f'{w}.Wrap := 2147483647;',f'{w}.Wrap := {w}.Wrap * 2 + 2;',
        f'{w}.SignedEdge := {w}.Wrap / 2;']
    # Widen BEFORE multiplication/subtraction; the LINT target alone does not
    # guarantee the width of an expression over DINT operands on Logix.
    for name in ('Run','Down','Idle'):
        lines += [f'{w}.{name} := {o}.{name}S;',f'{w}.{name} := {w}.{name} * 1000 + {o}.{name}Ms;']
    for name,counter,baseline in (('Good','GoodCount','GoodBase'),('Nok','ScrapCount','NokBase')):
        lines += [f'{w}.{name} := {unit}.{counter};',f'{w}.{name} := {w}.{name} - {o}.{baseline};']
    lines += [f'{w}.Ideal := {gen._oee_ideal(app)};',f'JSR({factor_routine(app)},0);',f'CPS({f},{root}.Oee,1);',
        f'{root}.OeeTrendHead := {o}.Head;',
        f'IF ({w}.Initialized = 0) OR ({w}.SeenEpoch <> {o}.Epoch) OR ({w}.SeenTrendHead <> {o}.Head) THEN',
        # An epoch invalidates all slots; otherwise only the newly owned slot
        # changes. First scan covers every retained slot after Program/Run.
        f'FOR {index} := 0 TO {gen.OEE_SAMPLES-1} DO',
        f'IF ({w}.Initialized = 0) OR ({w}.SeenEpoch <> {o}.Epoch) OR ({index} = {o}.Head - 1) THEN',
        f'{root}.OeeTrend[{index}].Oee := 0;',f'{root}.OeeTrend[{index}].OeeValid := 0;',
        f'IF {o}.SmpEpoch[{index}] = {o}.Epoch THEN']
    for name in ('Run','Down'):
        lines += [f'{w}.{name} := {o}.Smp{name}S[{index}];',f'{w}.{name} := {w}.{name} * 1000 + {o}.Smp{name}Ms[{index}];']
    lines += [f'{w}.Idle := 0;',f'{w}.Good := {o}.SmpGood[{index}];',f'{w}.Nok := {o}.SmpNok[{index}];',
        f'{w}.Ideal := {o}.SmpIdealMs[{index}];',f'JSR({factor_routine(app)},0);',
        f'{root}.OeeTrend[{index}].Oee := {f}.Oee;',f'{root}.OeeTrend[{index}].OeeValid := {f}.OeeValid;',
        'END_IF;','END_IF;','END_FOR;',f'{w}.SeenEpoch := {o}.Epoch;',f'{w}.SeenTrendHead := {o}.Head;','END_IF;']
    return lines+profiler(app)+health(app)+[f'{w}.Initialized := 1;']


def profiler(app):
    """Publish from the single accounting owner; used unchanged by native tests."""
    root=app.name;w=state_tag(app);p=gen.profiler_tag(app);index=w+'.Index';slot=w+'.Slot'
    lines=[]
    # Stats are owned by step-close; do not rebuild rows that did not change.
    stats=root+f'.Profiler.StepStats[{index}]'
    labels=labels_tag(app)
    lines += [f'FOR {index} := 0 TO {gen.PROFILE_STEPS-1} DO']
    if gen.ordered_steps(app):
        lines += [f'IF {index} < {min(len(gen.ordered_steps(app)),gen.PROFILE_STEPS)} THEN',
            f'IF ({w}.Initialized = 0) OR ({w}.SeenCounts[{index}] <> {p}.StatCount[{index}]) THEN',
            f'CPS({w}.EmptyStats,{stats},1);',f'IF {p}.StatCount[{index}] <> 0 THEN',
            f'{stats}.Id := {labels}.Entries[{index}].StepNo;',f'CPS({labels}.Entries[{index}].Label,{stats}.Label,1);',
            f'{stats}.TimeClass := {labels}.Entries[{index}].TimeClass;',f'{stats}.Count := {p}.StatCount[{index}];',
            f'{stats}.Avg := {p}.StatAvg[{index}];',f'{stats}.Maximum := {p}.StatMax[{index}];','END_IF;',
            f'{w}.SeenCounts[{index}] := {p}.StatCount[{index}];','END_IF;','ELSE',f'CPS({w}.EmptyStats,{stats},1);','END_IF;']
    else:lines += [f'CPS({w}.EmptyStats,{stats},1);']
    lines += ['END_FOR;']
    last=root+'.Profiler.LastCycle';step=last+f'.Steps[{index}]'
    lines += [f'IF ({w}.Initialized = 0) OR ({w}.SeenCycles <> {p}.LastCycleNo) THEN',
        f'{last}.CycleNo := {p}.LastCycleNo;',f'{last}.NSteps := 0;',
        *(f'{last}.{name} := 0;' for name in ('Total','WorkTime','WaitTime')),
        f'IF {p}.LastCycleNo <> 0 THEN',
        f'IF ({p}.LastN >= 0) AND ({p}.LastN <= {gen.PROFILE_STEPS}) AND ({p}.CurBuf >= 0) AND ({p}.CurBuf <= 1) THEN',
        f'{last}.NSteps := {p}.LastN;',f'{last}.Total := {p}.LastTotal;',f'{last}.WorkTime := {p}.LastWork;',
        f'{last}.WaitTime := {p}.LastTotal - {p}.LastWork;',
        'ELSE',f'{pub.header_tag(app)}.Valid := 0;','END_IF;','END_IF;',
        f'{w}.Buffer := (1 - {p}.CurBuf) * {gen.PROFILE_STEPS};',
        f'FOR {index} := 0 TO {gen.PROFILE_STEPS-1} DO',f'CPS({w}.EmptyStep,{step},1);',
        f'IF {index} < {last}.NSteps THEN',f'{slot} := {w}.Buffer + {index};',
        f'{step}.StepNo := {p}.WfStepNo[{slot}];',f'{w}.LookupStep := {p}.WfStepNo[{slot}];',
        f'JSR({lookup_routine(app)},0);',f'CPS({w}.StepName,{step}.StepName,1);',
        f'{step}.TimeClass := {w}.TimeClass;',f'{step}.Duration := {p}.WfDurMs[{slot}];',f'{step}.Expected := {p}.WfExpMs[{slot}];',
        'END_IF;','END_FOR;',f'{w}.SeenCycles := {p}.LastCycleNo;','END_IF;',
        f'{root}.Profiler.LastCycleTime := {p}.LastCycleTime;',f'{root}.Profiler.MinCycleTime := {p}.MinCycleTime;',
        f'{root}.Profiler.HistoryHead := {p}.HistoryHead;',
        f'IF ({w}.Initialized = 0) OR ({w}.SeenHead <> {p}.HistoryHead) THEN',
        f'FOR {index} := 0 TO {gen.CYCLE_HISTORY-1} DO',
        f'IF ({w}.Initialized = 0) OR ({index} = {p}.HistoryHead - 1) THEN']
    history=root+f'.Profiler.History[{index}]'
    lines += [f'{history}.CycleNo := {p}.HisCycleNo[{index}];',f'{history}.Total := {p}.HisTotal[{index}];',
        f'{history}.WorkTime := {p}.HisWork[{index}];',f'{history}.WaitTime := {p}.HisTotal[{index}] - {p}.HisWork[{index}];']
    lines += [f'{history}.ByClass[{i}] := {p}.HisByClass[{index}*{len(decl.TIME_CLASSES)}+{i}];' for i in range(len(decl.TIME_CLASSES))]
    lines += ['END_IF;','END_FOR;',f'{w}.SeenHead := {p}.HistoryHead;','END_IF;']
    return lines
