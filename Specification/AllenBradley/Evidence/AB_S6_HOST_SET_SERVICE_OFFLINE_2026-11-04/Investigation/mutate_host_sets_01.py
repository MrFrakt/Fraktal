"""Mutate the emitted V6.11 set-service ST; each mutant must fail the suite.

Generates the V6.11 sections once, then for each mutant replaces exactly one
emitted line (its occurrence named) and runs test_fraktal_ab_host_sets on a
bench built from the mutated program text. The unmutated text must pass.
No controller is contacted; no source file is changed.
"""
import json
import sys
import unittest
from pathlib import Path

TOOLS = Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
sys.path.insert(0, str(TOOLS))
import fraktal_ab_generate as gen
import fraktal_ab_st_bench as st_bench
import test_fraktal_ab_host_sets as suite

W, S, R = 'FRK_Press_HostSetWork', 'FRK_Press_HostSetStaged', 'FRK_Press_HostWork'
# (label, emitted line, occurrence, replacement)
MUTANTS = [
    ('parked answer not restored', f'        FRK_Press_HmiResponse.Accepted := FRK_Press_CoreCommandWork.OwnerAccepted;', 0,
     '        FRK_Press_HmiResponse.Accepted := 0;'),
    ('handler acknowledges a parked command', f'    IF {W}.Hold = 0 THEN', 0, f'    IF {W}.Hold >= 0 THEN'),
    ('owner ack advances while parked', f'    IF {W}.Hold = 0 THEN', 1, f'    IF {W}.Hold >= 0 THEN'),
    ('typed reply published while parked', f'IF (FRK_Press_CoreCommandWork.NewCore <> 0) AND ({W}.Hold = 0)', 0,
     f'IF (FRK_Press_CoreCommandWork.NewCore <> 0) AND ({W}.Hold >= 0)'),
    ('second set command not refused', f'ELSIF ({W}.Parked <> 0) OR ({R}.Reply.JobSequence <> 0) THEN', 0,
     f'ELSIF ({W}.Parked = 99) THEN'),
    ('resume ignores a same-scan command', f'IF ({W}.Ready <> 0) AND (FRK_Press_CoreCommandWork.Pending = 0) THEN', 0,
     f'IF ({W}.Ready <> 0) THEN'),
    ('late resume still runs', 'ParkedMs >= 1800', 1, 'ParkedMs >= 999999'),
    ('foreign records resolve', f'                            IF {W}.Scoped = 1 THEN', 0,
     f'                            IF {W}.Scoped >= 0 THEN'),
    ('stored name length unchecked', f'                        IF FRK_Press_HostSample.Body.Name.LEN <> {R}.Reply.JobName.LEN THEN', 0,
     f'                        IF FRK_Press_HostSample.Body.Name.LEN < 0 THEN'),
    ('failed receipt reads as stored', f'                {W}.StoreResult := 2;', 0, f'                {W}.StoreResult := 1;'),
    ('abandoned job leaves the command parked', f'        IF ({R}.Outcome = 2) OR ({R}.Outcome = 3) THEN', 0,
     f'        IF ({R}.Outcome = 99) THEN'),
    ('rejection names another key', f'.Value = {S}.Ordinal', 0, f'.Value <> {S}.Ordinal'),
    ('non-ASCII name accepted', f'            {W}.Bad := 1;', 0, f'            {W}.Bad := 0;'),
    ('transaction reads no host staging', f'CPS({S}, FRK_Press_SetStaged, 1);', 0,
     'CPS(FRK_Press_SetStaged, FRK_Press_SetStaged, 1);'),
    ('refused export publishes its line', f'        AND ({W}.HasLine <> 0) THEN', 0,
     f'        OR ({W}.HasLine <> 0) THEN'),
    ('store snapshot not copied',
     f'                {R}.Reply.Snapshot.Values[{W}.Index] := FRK_Press_ConfigSetState.Snapshot[{W}.Index];', 0,
     f'                {R}.Reply.Snapshot.Values[{W}.Index] := 0;'),
    ('header root unchecked', f'                            {S}.RootId := 0;', 0,
     f'                            {S}.RootId := 1;'),
    ('final accepted on an incomplete document', f'                    AND ({W}.Records = {W}.Total)', 0,
     f'                    AND ({W}.Records >= 0)'),
]
# A line that occurs more than once, anchored by the line after it.
REGEX_MUTANTS = [
    ('host refusal stages a valid transaction',
     r'(<!\[CDATA\[ {16}' + S + r'\.Valid := )0(;\]\]></Line>\s*<Line Number="\d+"><!\[CDATA\[ {16}' + W + r'\.Ready := 1;)',
     r'\g<1>1\g<2>'),
]


def line(text):
    return f'<![CDATA[{text}]]>'


def run(sections, programs):
    suite.st_bench.for_application = lambda app: st_bench.Bench(*sections[:3], programs)
    loaded = unittest.defaultTestLoader.loadTestsFromModule(suite)
    result = unittest.TextTestRunner(stream=open('nul', 'w'), verbosity=0).run(loaded)
    return result.testsRun, len(result.failures) + len(result.errors)


def main():
    app = suite.application()
    sections = (gen.data_types(app), gen.aoi_definitions(app), gen.controller_tags(app), gen.programs(app))
    programs = sections[3]
    report = dict(baseline=None, mutants=[])
    ran, failed = run(sections, programs)
    report['baseline'] = dict(tests=ran, failed=failed)
    print('baseline', ran, failed, flush=True)
    for label, text, occurrence, replacement in MUTANTS:
        old = text if text.startswith('ParkedMs') or text.startswith('.Value') else line(text)
        new = replacement if old == text else line(replacement)
        positions, start = [], 0
        while (index := programs.find(old, start)) >= 0:
            positions.append(index)
            start = index + 1
        if occurrence >= len(positions):
            raise SystemExit(f'mutant anchor missing: {label}')
        at = positions[occurrence]
        mutated = programs[:at] + new + programs[at + len(old):]
        ran, failed = run(sections, mutated)
        report['mutants'].append(dict(label=label, occurrences=len(positions), tests=ran, failed=failed,
                                      killed=failed > 0))
        print(('killed  ' if failed else 'SURVIVED'), failed, label, flush=True)
    import re
    for label, pattern, replacement in REGEX_MUTANTS:
        mutated, count = re.subn(pattern, replacement, programs)
        if count != 1:
            raise SystemExit(f'mutant anchor not unique: {label} ({count})')
        ran, failed = run(sections, mutated)
        report['mutants'].append(dict(label=label, occurrences=count, tests=ran, failed=failed, killed=failed > 0))
        print(('killed  ' if failed else 'SURVIVED'), failed, label, flush=True)
    report['passed'] = report['baseline']['failed'] == 0 and all(m['killed'] for m in report['mutants'])
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if out:
        with out.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(report, stream, indent=2)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
