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
        M('SeenCounts','DINT',count=gen.PROFILE_STEPS),M('StepName',S(120)),M('TimeClass','DINT'))


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
