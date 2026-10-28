"""Bounded private v38 TASK interval-reset experiment on the resource fixture.

SSV changes only MaxInterval/MinInterval statistics, four times after startup.
No scheduler, clock, fault, overlap, output or application state is written.
This experiment takes ownership of those task-wide extrema; it is deliberately
not a production health provider. Download needs explicit target authorization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import tempfile

import fraktal_ab_generate as gen
import fraktal_ab_observer_fixture as fixture
from fraktal_ab_phase0_fixture import sha256
import fraktal_ab_resource_demo as resource

TAG = 'FRK_TaskWindowProbe'
TYPE = 'FRK_T_TaskWindowProbeV1'
ROUTINE = 'FRK_TaskWindowObserve'
SIGNATURE = 18003804
WINDOW_SCANS = 100
WINDOWS = 4
SENTINEL = 0x7fffffff7fffffff
DINTS = ('SchemaVersion', 'Signature', 'Revision', 'Samples', 'TaskRateUs',
         'Window', 'WindowScans', 'Done', 'MajorFaultBits', 'MinorFaultBits',
         'FaultSeen', 'OverlapCount', 'InitialOverlapCount', 'ResetCount',
         'MaxLow', 'MaxHigh', 'MinLow', 'MinHigh', 'SeedMaxLow', 'SeedMaxHigh',
         'SeedMinLow', 'SeedMinHigh', 'DoReset', 'LastScanUs')
ARRAYS = ('ResetMax', 'ResetMin', 'WindowMax', 'WindowMin')
FIELDS = DINTS + tuple(f'{name}{i}' for name in ARRAYS for i in range(WINDOWS))
FORMAT = '<' + 'i' * len(DINTS) + 'q' * (len(ARRAYS) * WINDOWS)
BYTES = struct.calcsize(FORMAT)


def logic(app):
    p, task = TAG, app.task_name
    body = [f'{p}.Revision := {p}.Revision + 1;',
            f'{p}.SchemaVersion := 1;', f'{p}.Signature := {SIGNATURE};']
    for obj, instance, attribute, field in (
            ('TASK', task, 'Rate', 'TaskRateUs'),
            ('TASK', task, 'LastScanTime', 'LastScanUs'),
            ('TASK', task, 'OverlapCount', 'OverlapCount'),
            ('FaultLog', '', 'MajorFaultBits', 'MajorFaultBits'),
            ('FaultLog', '', 'MinorFaultBits', 'MinorFaultBits')):
        body.append(f'GSV({obj},{instance},{attribute},{p}.{field});')
    body += [f'IF ({p}.MajorFaultBits <> 0) OR ({p}.MinorFaultBits <> 0) THEN',
             f'{p}.FaultSeen := 1;', 'END_IF;',
             f'IF {p}.Samples = 0 THEN',
             f'{p}.InitialOverlapCount := {p}.OverlapCount;',
             f'{p}.DoReset := 1;',
             f'ELSIF {p}.Done = 0 THEN',
             f'{p}.WindowScans := {p}.WindowScans + 1;',
             f'IF {p}.WindowScans = {WINDOW_SCANS} THEN',
             f'GSV(TASK,{task},MaxInterval,{p}.MaxWords[0]);',
             f'GSV(TASK,{task},MinInterval,{p}.MinWords[0]);',
             f'COP({p}.MaxWords[0],{p}.WindowMax[{p}.Window],1);',
             f'COP({p}.MinWords[0],{p}.WindowMin[{p}.Window],1);',
             f'{p}.Window := {p}.Window + 1;',
             f'IF {p}.Window = {WINDOWS} THEN',
             f'{p}.Done := 1;',
             'ELSE', f'{p}.DoReset := 1;', 'END_IF;', 'END_IF;', 'END_IF;',
             f'IF {p}.DoReset <> 0 THEN',
             f'{p}.SeedMaxWords[0] := 0;', f'{p}.SeedMaxWords[1] := 0;',
             f'{p}.SeedMinWords[0] := 0;', f'{p}.SeedMinWords[1] := 0;',
             f'IF ({p}.Window MOD 2) = 1 THEN',
             f'{p}.SeedMinWords[0] := 2147483647;',
             f'{p}.SeedMinWords[1] := 2147483647;', 'END_IF;',
             f'SSV(TASK,{task},MaxInterval,{p}.SeedMaxWords[0]);',
             f'SSV(TASK,{task},MinInterval,{p}.SeedMinWords[0]);',
             f'GSV(TASK,{task},MaxInterval,{p}.MaxWords[0]);',
             f'GSV(TASK,{task},MinInterval,{p}.MinWords[0]);',
             f'COP({p}.MaxWords[0],{p}.ResetMax[{p}.Window],1);',
             f'COP({p}.MinWords[0],{p}.ResetMin[{p}.Window],1);',
             f'{p}.ResetCount := {p}.ResetCount + 1;',
             f'{p}.WindowScans := 0;', f'{p}.DoReset := 0;', 'END_IF;',
             # Stop publication as well as SSV after completion: no overflow or
             # evidence mutation later during the ordinary regression matrix.
             f'{p}.Samples := {p}.Samples + 1;',
             f'{p}.Revision := {p}.Revision + 1;']
    return [f'IF {p}.Done = 0 THEN', *body, 'END_IF;']


def augment(text, app):
    members = []
    for name in DINTS:
        if name.endswith('High'):
            continue
        dimension = 0
        if name.endswith('Low'):
            name, dimension = name[:-3] + 'Words', 2
        members.append((name, 'DINT', dimension))
    members += [(name, 'LINT', WINDOWS) for name in ARRAYS]
    record = (f'<DataType Name="{TYPE}" Family="NoFamily" Class="User"><Members>'
              + ''.join(f'<Member Name="{name}" DataType="{kind}" Dimension="{dimension}" '
                        'Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>'
                        for name, kind, dimension in members) + '</Members></DataType>')
    tag = (f'<Tag Name="{TAG}" TagType="Base" DataType="{TYPE}" '
           'Constant="false" ExternalAccess="Read Only"/>')
    return fixture.augment(text, app, record=record, tags=[tag], routine=ROUTINE, body=logic(app))


def generate(seed: Path, output: Path):
    if output.exists():
        raise ValueError('refusing to overwrite probe output')
    app = resource.application()
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory) / 'resources.L5X'
        generated = gen.generate(app, seed, base)
        result = augment(base.read_text(encoding='utf-8'), app)
    output.write_text(result, encoding='utf-8', newline='\n')
    return dict(Schema='fraktal.ab.task-window-probe', SchemaVersion=1,
                SeedSha256=sha256(seed), BaseFixtureSha256=generated['OutputSha256'],
                OutputSha256=sha256(output), Manifest=generated['Manifest'],
                RecordBytes=BYTES, Signature=SIGNATURE,
                StatisticsWritten=['TASK.MaxInterval', 'TASK.MinInterval'],
                ResetLimit=WINDOWS, WindowScans=WINDOW_SCANS,
                RuntimeAccepted=False, ProductionHealthProviderChanged=False)


def decode(raw):
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != BYTES:
        raise ValueError('invalid task-window record length/type')
    record = dict(zip(FIELDS, struct.unpack(FORMAT, raw)))
    if record['SchemaVersion'] != 1 or record['Signature'] != SIGNATURE:
        raise ValueError('task-window schema/signature mismatch')
    if record['Revision'] <= 0 or record['Revision'] % 2:
        raise ValueError('observer publication incomplete')
    if record['TaskRateUs'] != 10000 or not 1 <= record['Samples'] <= WINDOWS * WINDOW_SCANS + 1:
        raise ValueError('unexpected task-window task/counter')
    if not (0 <= record['Window'] <= WINDOWS and 0 <= record['WindowScans'] <= WINDOW_SCANS
            and record['Done'] in (0, 1) and 1 <= record['ResetCount'] <= WINDOWS):
        raise ValueError('invalid task-window progress')
    if record['Done'] and (record['Window'] != WINDOWS or record['ResetCount'] != WINDOWS
                           or record['Samples'] != WINDOWS * WINDOW_SCANS + 1):
        raise ValueError('incomplete task-window result')
    return record


def assess(record):
    """Keep zero-seed and sentinel-seed results separate, including failures."""
    if not record['Done']:
        raise ValueError('task-window experiment is not complete')
    rows = []
    for index in range(WINDOWS):
        row = dict(index=index, scans=WINDOW_SCANS,
                   minSeed=0 if index % 2 == 0 else SENTINEL,
                   resetMax=record[f'ResetMax{index}'], resetMin=record[f'ResetMin{index}'],
                   maximum=record[f'WindowMax{index}'], minimum=record[f'WindowMin{index}'])
        row['resetReadbackMatches'] = row['resetMax'] == 0 and row['resetMin'] == row['minSeed']
        row['positiveOrderedInterval'] = 0 < row['minimum'] <= row['maximum']
        rows.append(row)
    return dict(windows=rows, faultsObserved=bool(record['FaultSeen']),
                overlapChanged=record['OverlapCount'] != record['InitialOverlapCount'],
                WindowResetObserved=all(row['resetReadbackMatches'] for row in rows),
                ProductionReplacementAccepted=False, ClockAdjustmentQualified=False,
                MissedScansQualified=False, EchoScalingChangesQualified=False,
                TaskWideStatisticsOwnershipRequired=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('seed', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(argv)
    try:
        report = generate(args.seed, args.output)
    except (OSError, ValueError, AssertionError) as exc:
        parser.exit(2, str(exc) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
