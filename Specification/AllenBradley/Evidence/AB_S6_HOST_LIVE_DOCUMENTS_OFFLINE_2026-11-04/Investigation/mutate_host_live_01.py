"""Mutate the emitted V6.11 LiveDocuments ST; each mutant must fail the live suite.

Generates the live press's V6.11 sections once, then for each mutant replaces
exactly one emitted line and runs test_fraktal_ab_host_live on a bench built
from the mutated program text. The unmutated text must pass. No controller is
contacted; no source file is changed.
"""
import json
import re
import sys
import unittest
from pathlib import Path

TOOLS = Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
sys.path.insert(0, str(TOOLS))
import dataclasses
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s4b_owner_demo as demo
import fraktal_ab_st_bench as st_bench
import test_fraktal_ab_host_live as suite

W, R, S = 'FRK_Press_HostSetWork', 'FRK_Press_HostWork', 'FRK_Press_HostSetStaged'
MUTANTS = [
    ('verdict not kept', f'        {W}.Verdict := FRK_Press_HmiResponse.Accepted;', f'        {W}.Verdict := 1;'),
    ('a silent pass keeps the host sequence', f'    FRK_Press_CoreCommandWork.OwnerSequence := {W}.SavedOwner;',
     '    FRK_Press_CoreCommandWork.OwnerSequence := 0;'),
    ('a silent pass acknowledges', f'        {W}.Hold := 1;', f'        {W}.Hold := 0;'),
    ('a restore outside a restore', f'                {R}.Error := 9;', f'                {R}.Error := 0;'),
    ('a restore without the set gate', f'                {R}.Error := 7;', f'                {R}.Error := 0;'),
    ('a lost document not staged', f'                    {S}.StoreResult := 2;', f'                    {S}.StoreResult := 1;'),
    ('a keep failure ignored', f'                    {W}.KeepFailed := 1;', f'                    {W}.KeepFailed := 0;'),
    ('a keep job not preempted', f'    AND ({R}.Reply.JobPhase = 4) THEN', f'    AND ({R}.Reply.JobPhase = 99) THEN'),
    ('a keep publishes another value',
     f'                        {R}.Reply.Snapshot.Values[4] := FRK_T_PressStationCfgTag.StationNumber;',
     f'                        {R}.Reply.Snapshot.Values[4] := 0;'),
    ('the session permit published regardless', f'    {R}.Reply.SessionPermits := {W}.Permits;',
     f'    {R}.Reply.SessionPermits := 1;'),
    ('the verdict not published', f'        {R}.Reply.JobBool := {W}.Verdict;', f'        {R}.Reply.JobBool := 1;'),
    ('a failed host pass runs', f'    ELSIF ({W}.Failed <> 0) OR ({W}.ParkedMs >= 1800) THEN', '    ELSIF 1 = 0 THEN'),
]
# A line that occurs more than once, anchored by the line before it.
REGEX_MUTANTS = [
    ('a keep while restoring',
     r'(<!\[CDATA\[ {12}IF \(FRK_T_PressStationCfgTag\.SchemaVersion = 0\) THEN\]\]></Line>\s*<Line Number="\d+">'
     r'<!\[CDATA\[ {16}' + R + r'\.Error := )8(;)', r'\g<1>0\g<2>'),
]


def line(text):
    return f'<![CDATA[{text}]]>'


def run(sections, programs):
    st_bench.for_application = lambda app: st_bench.Bench(*sections[:3], programs)
    loaded = unittest.defaultTestLoader.loadTestsFromModule(suite)
    result = unittest.TextTestRunner(stream=open('nul', 'w'), verbosity=0).run(loaded)
    return result.testsRun, len(result.failures) + len(result.errors)


def main():
    app = dataclasses.replace(demo.application(), canonical_host_services=True)
    sections = (gen.data_types(app), gen.aoi_definitions(app), gen.controller_tags(app), gen.programs(app))
    programs = sections[3]
    report = dict(baseline=None, mutants=[])
    ran, failed = run(sections, programs)
    report['baseline'] = dict(tests=ran, failed=failed)
    print('baseline', ran, failed, flush=True)
    for label, text, replacement in MUTANTS:
        if programs.count(line(text)) != 1:
            raise SystemExit(f'mutant anchor not unique: {label} ({programs.count(line(text))})')
        ran, failed = run(sections, programs.replace(line(text), line(replacement)))
        report['mutants'].append(dict(label=label, tests=ran, failed=failed, killed=failed > 0))
        print(('killed  ' if failed else 'SURVIVED'), failed, label, flush=True)
    for label, pattern, replacement in REGEX_MUTANTS:
        mutated, count = re.subn(pattern, replacement, programs)
        if count != 1:
            raise SystemExit(f'mutant anchor not unique: {label} ({count})')
        ran, failed = run(sections, mutated)
        report['mutants'].append(dict(label=label, tests=ran, failed=failed, killed=failed > 0))
        print(('killed  ' if failed else 'SURVIVED'), failed, label, flush=True)
    report['passed'] = report['baseline']['failed'] == 0 and all(m['killed'] for m in report['mutants'])
    if len(sys.argv) > 1:
        with Path(sys.argv[1]).open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(report, stream, indent=2)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
