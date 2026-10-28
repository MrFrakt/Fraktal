"""Disposable read-only native timing observer added to the local tower fixture.

The production declaration, manifest and all original routines remain unchanged
except one final JSR. This is evidence tooling, never a selectable health provider.
Generate offline; a controller download requires separate explicit authorization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import tempfile

import fraktal_ab_generate as gen
from fraktal_ab_phase0_fixture import sha256
import fraktal_ab_observer_fixture as fixture
import fraktal_ab_tower_demo as tower

TAG = 'FRK_NativeObserver'
TYPE = 'FRK_T_NativeObserverV1'
ROUTINE = 'FRK_NativeObserve'
SCHEMA = 'fraktal.ab.native-observer'
SIGNATURE = 18003801
# Four-byte fields precede the eight-byte fields, then four native INTs.
# The LINT region starts at an eight-byte boundary. No BOOL packing or padding.
DINTS = ('SchemaVersion', 'Signature', 'Revision', 'Samples', 'TaskRateUs',
         'LastScanUs', 'MaxScanUs', 'OverlapCount', 'TimeSynchronized',
         'LegacyIntervalUs', 'NegativeCst', 'NegativeWall', 'NegativeStart',
         'MajorFaultBits', 'MinorFaultBits', 'FaultInfo',
         'MaxIntervalLow', 'MaxIntervalHigh', 'MinIntervalLow', 'MinIntervalHigh')
LINTS = ('Cst', 'Wall', 'Start', 'PreviousCst', 'PreviousWall', 'PreviousStart',
         'DeltaCst', 'DeltaWall', 'DeltaStart', 'FirstCst', 'FirstWall', 'FirstStart',
         'MinCst', 'MaxCst', 'MinStart', 'MaxStart')
INTS = ('EntryStatus', 'FaultCode', 'ModuleMode', 'ForceStatus')
FORMAT = '<' + 'i' * len(DINTS) + 'q' * len(LINTS) + 'h' * len(INTS)
FIELDS = DINTS + LINTS + INTS
BYTES = struct.calcsize(FORMAT)


def logic(app):
    p = TAG
    body = [
        f'IF {p}.Revision >= 2000000000 THEN {p}.Revision := 0; END_IF;',
        f'{p}.Revision := {p}.Revision + 1;',
        f'{p}.SchemaVersion := 1;', f'{p}.Signature := {SIGNATURE};',
    ]
    reads = (
        ('TASK', app.task_name, 'Rate', 'TaskRateUs'),
        ('TASK', app.task_name, 'LastScanTime', 'LastScanUs'),
        ('TASK', app.task_name, 'MaxScanTime', 'MaxScanUs'),
        ('TASK', app.task_name, 'OverlapCount', 'OverlapCount'),
        ('TASK', app.task_name, 'MaxInterval', 'MaxIntervalWords[0]'),
        ('TASK', app.task_name, 'MinInterval', 'MinIntervalWords[0]'),
        ('TASK', app.task_name, 'StartTime', 'Start'),
        ('CST', '', 'CurrentValue', 'Cst'),
        ('WallClockTime', '', 'CurrentValue', 'Wall'),
        ('TimeSynchronize', '', 'IsSynchronized', 'TimeSynchronized'),
        ('FaultLog', '', 'MajorFaultBits', 'MajorFaultBits'),
        ('FaultLog', '', 'MinorFaultBits', 'MinorFaultBits'),
        ('MODULE', 'Local', 'EntryStatus', 'EntryStatus'),
        ('MODULE', 'Local', 'FaultCode', 'FaultCode'),
        ('MODULE', 'Local', 'FaultInfo', 'FaultInfo'),
        ('MODULE', 'Local', 'Mode', 'ModuleMode'),
        ('MODULE', '', 'ForceStatus', 'ForceStatus'),
    )
    body += [f'GSV({obj},{instance},{attribute},{p}.{field});'
             for obj, instance, attribute, field in reads]
    body += [f'{p}.LegacyIntervalUs := {gen.health_probe_tag(app)}.IntervalUs;',
             f'IF S:FS OR ({p}.Samples = 0) THEN']
    for clock in ('Cst', 'Wall', 'Start'):
        body += [f'{p}.First{clock} := {p}.{clock};',
                 f'{p}.Delta{clock} := 0;', f'{p}.Negative{clock} := 0;']
    body += [f'{p}.MinCst := 0;', f'{p}.MaxCst := 0;',
             f'{p}.MinStart := 0;', f'{p}.MaxStart := 0;',
             f'{p}.Samples := 1;', 'ELSE']
    for clock in ('Cst', 'Wall', 'Start'):
        body += [f'{p}.Delta{clock} := {p}.{clock} - {p}.Previous{clock};',
                 f'IF ({p}.Delta{clock} < 0) AND ({p}.Negative{clock} < 2000000000) THEN',
                 f'{p}.Negative{clock} := {p}.Negative{clock} + 1;', 'END_IF;']
    for clock in ('Cst', 'Start'):
        body += [f'IF ({p}.Samples = 1) OR ({p}.Delta{clock} < {p}.Min{clock}) THEN',
                 f'{p}.Min{clock} := {p}.Delta{clock};', 'END_IF;',
                 f'IF ({p}.Samples = 1) OR ({p}.Delta{clock} > {p}.Max{clock}) THEN',
                 f'{p}.Max{clock} := {p}.Delta{clock};', 'END_IF;']
    body += [f'IF {p}.Samples < 2000000000 THEN {p}.Samples := {p}.Samples + 1; END_IF;', 'END_IF;']
    for clock in ('Cst', 'Wall', 'Start'):
        body.append(f'{p}.Previous{clock} := {p}.{clock};')
    return body + [f'{p}.Revision := {p}.Revision + 1;']


def augment(text, app):
    """Change only the expected generated fixture and assert preservation."""
    members = ''
    for names, datatype in ((DINTS, 'DINT'), (LINTS, 'LINT'), (INTS, 'INT')):
        for name in names:
            if name in ('MaxIntervalHigh', 'MinIntervalHigh'):
                continue
            dimension = 0
            if name in ('MaxIntervalLow', 'MinIntervalLow'):
                name, dimension = name.replace('Low', 'Words'), 2
            members += (f'<Member Name="{name}" DataType="{datatype}" Dimension="{dimension}" '
                        'Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>')
    record = f'<DataType Name="{TYPE}" Family="NoFamily" Class="User"><Members>{members}</Members></DataType>'
    tag = (f'<Tag Name="{TAG}" TagType="Base" DataType="{TYPE}" '
           'Constant="false" ExternalAccess="Read Only"/>')
    return fixture.augment(text, app, record=record, tags=[tag], routine=ROUTINE, body=logic(app))


def generate(seed: Path, output: Path):
    if output.exists():
        raise ValueError('refusing to overwrite observer output')
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'tower.L5X'
        report = gen.generate(tower.application(), seed, path)
        text = augment(path.read_text(encoding='utf-8'), tower.application())
    output.write_text(text, encoding='utf-8', newline='\n')
    return dict(Schema=SCHEMA, SchemaVersion=1, SeedSha256=sha256(seed),
                BaseFixtureSha256=report['OutputSha256'], Output=str(output),
                OutputSha256=sha256(output), Manifest=report['Manifest'],
                RecordBytes=BYTES, Signature=SIGNATURE,
                NativeObserverOnly=True, RuntimeAccepted=False,
                OriginalCodeAndInitialValuesPreserved=True,
                ProductionHealthProviderChanged=False)


def decode(raw):
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != BYTES:
        raise ValueError('invalid observer record length/type')
    record = dict(zip(FIELDS, struct.unpack(FORMAT, raw)))
    if record['SchemaVersion'] != 1 or record['Signature'] != SIGNATURE:
        raise ValueError('observer schema/signature mismatch')
    if record['Revision'] <= 0 or record['Revision'] % 2:
        raise ValueError('observer publication incomplete')
    if record['TaskRateUs'] != 10000 or record['Samples'] < 2:
        raise ValueError('observer not sampling the expected 10 ms task')
    for prefix in ('Max', 'Min'):
        # Unsigned low word, signed high word: preserve the full native value.
        record[prefix + 'IntervalUs'] = ((record[prefix + 'IntervalHigh'] << 32)
                                        | (record[prefix + 'IntervalLow'] & 0xffffffff))
    return record


def sample(comm, attempts=20):
    """Three reads bracket a whole UDT; no torn or odd revision is accepted."""
    return fixture.sample(comm, TAG, decode, attempts)


def assess(first, last, host_seconds):
    """Report observations; a clean run never certifies clock adjustment tests."""
    if host_seconds <= 0 or last['Samples'] <= first['Samples']:
        raise ValueError('observer did not advance')
    if last['Samples'] >= 2000000000 or last['Revision'] < first['Revision']:
        raise ValueError('observer counters saturated or restarted')
    if any(first['First' + name] != last['First' + name] for name in ('Cst', 'Wall', 'Start')):
        raise ValueError('observer restarted during observation')
    scans = last['Samples'] - first['Samples']
    clocks = {name: (last[name] - first[name]) for name in ('Cst', 'Wall', 'Start')}
    return dict(Scans=scans, HostSeconds=host_seconds, ClockDeltaUs=clocks,
                MicrosecondsPerScan={key: value / scans for key, value in clocks.items()},
                SimulatedToHostRatio={key: value / (host_seconds * 1e6) for key, value in clocks.items()},
                FaultFree=not (last['MajorFaultBits'] or last['MinorFaultBits']),
                NegativeDeltas={name: last['Negative' + name] - first['Negative' + name]
                                for name in clocks},
                ClockAdjustmentQualified=False, MissedScansQualified=False,
                EchoScalingChangesQualified=False, ExternalIoQualified=False,
                ProductionReplacementAccepted=False)


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
