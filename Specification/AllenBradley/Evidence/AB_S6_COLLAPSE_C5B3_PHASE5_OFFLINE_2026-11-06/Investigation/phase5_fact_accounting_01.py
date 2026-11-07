"""Account the 39 appended Phase 5 O10 facts and verify their presence in all 86 accepted press captures."""
from pathlib import Path
import json, sys, xml.etree.ElementTree as ET

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
sys.path.insert(0, str(R / 'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_fixture_observation as observed
import fraktal_ab_press_s6_collapse_echo38 as profile
import fraktal_ab_press_s6_shelving_echo38 as shelving
import test_fraktal_ab_fixture_reads as replay

old_l5x = Path('C:/work/fraktal-ab-c5b3-control-20261106/prepare_01/press.L5X')
root = ET.parse(old_l5x).getroot()
old_type = next(t.get('DataType') for t in root.iter('Tag') if t.get('Name') == 'FRK_Press_FixtureObservation')
prior = {m.get('Name') for t in root.iter('DataType') if t.get('Name') == old_type for m in t.findall('./Members/Member')}
assert len(prior) == 102, len(prior)

app = profile.application()
shelf_app = shelving.application()
assert app.fixture_observation == shelf_app.fixture_observation
all_facts = observed.facts(app)
assert len(all_facts) == 141, len(all_facts)

PURPOSES = {
    'Unit': 'Run-style and HOLD_TO_RUN state (HoldRun, Issued, StepPending) asserted by Phase 5a',
    'Door': 'Cylinder Busy state and RunCount asserted by Phase 5a/5f',
    'PartSlide': 'Cylinder Busy, Extended, Held and RunCount asserted by Phase 5a/5f',
    'PressRam': 'Cylinder RunCount asserted by Phase 5a parity module_counters',
    'PartPresentSensor': 'Sensor OutImm_Value wait predicate asserted by Phase 5g two-hand readiness',
    'Profiler': 'CycleOpen, Open, LastCycleNo, LastCycleTime, HistoryHead, StatCount, DegradedCount and DegradedWorkMs asserted by Phase 5e/5f',
    'AlarmActive': 'ActSeverity, ActResetClass, ActSourceModuleId and RingHead asserted by Phase 5f/5h',
    'AlarmRing': 'RingReasonCode, RingSeverity, RingResetClass and RingSourceModuleId asserted by Phase 5f degradation watch',
    'Oee': 'Epoch, Head and Smp* sample columns asserted by Phase 5c OEE reset and one-minute sample rows',
}

rows = []
problems = []
for surface, member, name, source in all_facts:
    if name in prior:
        continue
    rows.append(dict(
        surface=surface,
        member=member.name,
        observedName=name,
        dimension=member.dimension,
        source=source,
        nativeType='DINT',
        purpose=PURPOSES[surface],
    ))

assert len(rows) == 39, len(rows)

for label, pair in replay.pairs():
    for row in rows:
        held = replay.legacy_surface(pair, row['surface'])
        member = row['member']
        if held is None or member not in held:
            problems.append(dict(capture=label, surface=row['surface'], member=member, problem='missing native bytes'))
            continue
        value = held[member]
        dim = row['dimension']
        if dim and (not isinstance(value, list) or len(value) != dim):
            problems.append(dict(capture=label, surface=row['surface'], member=member, expected=dim, actual=len(value) if isinstance(value, list) else type(value).__name__))

result = dict(
    schema='fraktal.ab.c5b3-phase5-fact-accounting',
    schemaVersion=1,
    passed=not problems,
    priorFactCount=len(prior),
    newFactCount=len(rows),
    totalFactCount=len(all_facts),
    sharedAcrossProfiles=['fraktal_ab_press_s6_collapse_echo38', 'fraktal_ab_press_s6_shelving_echo38'],
    publicCanonicalAliases={
        'Door': ['OutImm_ExecState', 'TimCount[1..2]', 'TimLast[1..2]'],
        'PartSlide': ['OutImm_ExecState', 'TimCount[1..2]', 'TimLast[1..2]'],
        'PressRam': ['OutImm_ExecState', 'TimCount[1..2]', 'TimLast[1..2]'],
    },
    facts=rows,
    captures=86,
    problems=problems,
    controllerAccess=False,
)
with (W / 'phase5_fact_accounting_01.json').open('x', encoding='utf-8') as out:
    json.dump(result, out, indent=2)
print(json.dumps(dict(passed=result['passed'], newFacts=len(rows), totalFacts=len(all_facts), captures=86, problems=len(problems))))
raise SystemExit(0 if result['passed'] else 1)
