"""Disposable bounded ALMD/tag-alarm comparison on the existing tower fixture.

Generate offline. Download requires separate current authorization. Only private
native alarm inputs/controls are exercised; Core, HAL and mailbox are untouched.
The PLC retains phase observations so host polling cannot lose the short pulse.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import tempfile
import xml.etree.ElementTree as ET

import fraktal_ab_native_alarm_probe as alarms
import fraktal_ab_native_observer as timing
import fraktal_ab_observer_fixture as fixture
from fraktal_ab_phase0_fixture import sha256
import fraktal_ab_tower_demo as tower

SCHEMA = 'fraktal.ab.alarm-observer'
TAG, TYPE, ROUTINE = 'FRK_AlarmObserver', 'FRK_T_AlarmObserverV1', 'FRK_AlarmObserve'
SIGNATURE = 18003802
PHASES = (('baseline', 3), ('short_pulse', 3), ('sustained', 3), ('gone', 3),
          ('latched_active', 3), ('ack_live', 3), ('reset_live', 3), ('latched_gone', 3), ('reset_gone', 3),
          ('suppressed', 3), ('unsuppressed', 3), ('operator_shelve', 3),
          ('shelf_expiry', 65), ('cleanup', 3))
HEADER = ('SchemaVersion', 'Signature', 'Revision', 'Scans', 'Phase', 'Done',
          'ProbeFault', 'Started', 'InputBits', 'CommandBits', 'ShelveBits', 'ControlBits',
          'PhaseElapsedUs', 'ScratchIndex', 'TbaFlags', 'AlmdFlags',
          'TbaCount', 'AlmdCount', 'TbaStatus', 'AlmdStatus')
ROW = ('Samples', 'ElapsedUs', 'InputBits', 'TbaFlags', 'AlmdFlags',
       'TbaSeenFlags', 'AlmdSeenFlags', 'TbaCount', 'AlmdCount',
       'TbaStatus', 'AlmdStatus', 'TbaSeenStatus', 'AlmdSeenStatus', 'Complete')
LINTS = ('RunStartCst', 'PhaseStartCst')
CELLS = len(PHASES) * len(ROW)
FORMAT = '<' + 'i' * (len(HEADER) + CELLS) + 'q' * len(LINTS)
BYTES = struct.calcsize(FORMAT)
FLAGS = ('InAlarm', 'Acked', 'Suppressed', 'Shelved', 'Disabled', 'InAlarmUnack')
INDEX = {name:index for index,(name,_) in enumerate(PHASES)}


def logic():
    p, a, b, clock = TAG, alarms.TAG_ALARM, alarms.ALMD, timing.TAG + '.Cst'
    stride, last = len(ROW), len(PHASES) - 1
    cell = lambda name: f'{p}.Rows[{p}.ScratchIndex + {ROW.index(name)}]'
    active = ','.join(str(INDEX[name]) for name in ('sustained','latched_active','ack_live',
                     'reset_live','suppressed','unsuppressed','operator_shelve','shelf_expiry'))
    shelf = INDEX['operator_shelve'], INDEX['shelf_expiry']
    suppress = INDEX['suppressed']
    body = [f'IF {p}.Revision >= 2000000000 THEN {p}.Revision := 0; END_IF;',
            f'{p}.Revision := {p}.Revision + 1;', f'{p}.SchemaVersion := 1;',
            f'{p}.Signature := {SIGNATURE};', f'IF S:FS OR ({p}.Started = 0) THEN',
            f'FOR {p}.ScratchIndex := 0 TO {CELLS-1} DO',
            f'{p}.Rows[{p}.ScratchIndex] := 0;', 'END_FOR;',
            f'{p}.RunStartCst := {clock};', f'{p}.PhaseStartCst := {clock};',
            f'{p}.Phase := 0;', f'{p}.Done := 0;', f'{p}.ProbeFault := 0;',
            f'{p}.Scans := 0;', f'{p}.Started := 1;', 'END_IF;',
            f'IF ({p}.Phase < 0) OR ({p}.Phase > {last}) OR ({clock} < {p}.PhaseStartCst)',
            f'OR ({clock} - {p}.PhaseStartCst > 1000000000)',
            f'OR ({timing.TAG}.Signature <> {timing.SIGNATURE}) THEN',
            f'{p}.ProbeFault := 1;', f'{p}.Done := 1;', f'{p}.Phase := {last};', 'END_IF;',
            f'{p}.PhaseElapsedUs := 0;', f'IF {p}.Done = 0 THEN',
            f'{p}.PhaseElapsedUs := {clock} - {p}.PhaseStartCst;', 'END_IF;',
            f'{p}.ScratchIndex := {p}.Phase * {stride};', f'{p}.InputBits := 0;',
            f'{p}.CommandBits := 0;', f'{p}.ShelveBits := 0;', f'{p}.ControlBits := 0;',
            f'IF {p}.Done = 0 THEN', f'CASE {p}.Phase OF',
            f'{INDEX["short_pulse"]}: IF {cell("Samples")} = 0 THEN {p}.InputBits := 1; END_IF;',
            f'{active}: {p}.InputBits := 1;', 'END_CASE;',
            f'IF ({p}.Phase >= {INDEX["latched_active"]}) AND ({p}.Phase <= {INDEX["reset_gone"]}) THEN {p}.ControlBits := 1; END_IF;',
            f'IF ({p}.Phase = {INDEX["reset_live"]}) OR ({p}.Phase = {INDEX["reset_gone"]}) THEN {p}.CommandBits := 1; END_IF;',
            f'IF {p}.Phase = {INDEX["ack_live"]} THEN {p}.CommandBits := 2; END_IF;',
            f'IF ({p}.Phase = {shelf[0]}) AND ({p}.PhaseElapsedUs < 1000000) THEN {p}.ShelveBits := 1; END_IF;',
            'END_IF;', f'{alarms.INPUT} := {p}.InputBits;',
            f'{a}.Latched := {p}.ControlBits.0;', f'{b}.Latched := {p}.ControlBits.0;',
            f'{a}.AckRequired := {p}.ControlBits.0;', f'{a}.ProgAck := {p}.CommandBits.1;',
            f'{a}.ProgReset := {p}.CommandBits.0;', f'{a}.ProgEnable := 1;',
            f'{p}.ControlBits.1 := ({p}.Phase = {suppress}) AND ({p}.Done = 0);',
            f'{p}.ControlBits.2 := ({p}.Phase <> {suppress}) OR ({p}.Done = 1);',
            f'{p}.ControlBits.3 := (({p}.Phase <> {shelf[0]}) AND ({p}.Phase <> {shelf[1]})) OR ({p}.Done = 1);',
            f'{a}.ProgSuppress := {p}.ControlBits.1;',
            f'{a}.ProgUnsuppress := {p}.ControlBits.2;',
            f'{a}.ProgUnshelve := {p}.ControlBits.3;',
            f'{a}.ShelveDuration := 1;', f'{a}.OperShelve := {p}.ShelveBits.0;',
            f'{b}.ProgSuppress := {p}.ControlBits.1;',
            f'{b}.ProgUnsuppress := {p}.ControlBits.2;',
            f'{b}.ProgUnshelve := {p}.ControlBits.3;',
            f'{b}.OperShelve := {p}.ShelveBits.0;', f'{b}.ShelveDuration := 1;',
            f'{b}.MaxShelveDuration := 1;', f'{b}.Condition := 1;',
            f'{b}.AckRequired := {p}.ControlBits.0;', f'{b}.Severity := 700;', f'{b}.MinDurationPRE := 0;',
            f'ALMD({b},{alarms.INPUT}.0,{p}.CommandBits.1,{p}.CommandBits.0,0,1);',
            f'{p}.TbaFlags := 0;', f'{p}.AlmdFlags := 0;']
    for index, flag in enumerate(FLAGS):
        for native, field in ((a, 'TbaFlags'), (b, 'AlmdFlags')):
            body += [f'IF {native}.{flag} THEN {p}.{field} := {p}.{field} OR {1<<index}; END_IF;']
    for native,prefix in ((a,'Tba'),(b,'Almd')):
        body += [f'{p}.{prefix}Count := {native}.AlarmCount;',
                 f'{p}.{prefix}Status := {native}.Status;']
    body += [f'IF {p}.Scans < 2000000000 THEN {p}.Scans := {p}.Scans + 1; END_IF;',
             f'IF {p}.Done = 0 THEN', f'{cell("Samples")} := {cell("Samples")} + 1;',
             f'{cell("ElapsedUs")} := {p}.PhaseElapsedUs;']
    for field in ('InputBits', 'TbaFlags', 'AlmdFlags'):
        body.append(f'{cell(field)} := {p}.{field};')
    for native, prefix in ((a, 'Tba'), (b, 'Almd')):
        body += [f'{cell(prefix+"SeenFlags")} := {cell(prefix+"SeenFlags")} OR {p}.{prefix}Flags;',
                 f'{cell(prefix+"Count")} := {p}.{prefix}Count;',
                 f'{cell(prefix+"Status")} := {p}.{prefix}Status;',
                 f'{cell(prefix+"SeenStatus")} := {cell(prefix+"SeenStatus")} OR {p}.{prefix}Status;']
    body.append(f'CASE {p}.Phase OF')
    for index, (_, seconds) in enumerate(PHASES):
        body += [f'{index}: IF {p}.PhaseElapsedUs >= {seconds*1000000} THEN',
                 f'{cell("Complete")} := 1;']
        body += ([f'{p}.Done := 1;'] if index == last else
                 [f'{p}.Phase := {index+1};', f'{p}.PhaseStartCst := {clock};'])
        body += ['END_IF;']
    return body + ['END_CASE;', 'END_IF;', f'{p}.Revision := {p}.Revision + 1;']


def augment(text, app):
    root = ET.fromstring(text)
    if root.find(f"Controller/Tags/Tag[@Name='{timing.TAG}']") is None:
        raise ValueError('native timing observer is required')
    members = ''.join(f'<Member Name="{name}" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>' for name in HEADER)
    members += f'<Member Name="Rows" DataType="DINT" Dimension="{CELLS}" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>'
    members += ''.join(f'<Member Name="{name}" DataType="LINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>' for name in LINTS)
    record = f'<DataType Name="{TYPE}" Family="NoFamily" Class="User"><Members>{members}</Members></DataType>'
    tags = [f'<Tag Name="{TAG}" TagType="Base" DataType="{TYPE}" Constant="false" ExternalAccess="Read Only"/>',
            *alarms.tag_alarm_tags(), f'<Tag Name="{alarms.ALMD}" TagType="Base" DataType="ALARM_DIGITAL" Constant="false" ExternalAccess="Read/Write"/>']
    return fixture.augment(text, app, record=record, tags=tags, routine=ROUTINE, body=logic())


def generate(seed: Path, output: Path):
    if output.exists():
        raise ValueError('refusing to overwrite alarm observer output')
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory)/'timing.L5X'
        base = timing.generate(seed, source)
        text = augment(source.read_text(encoding='utf-8'), tower.application())
    output.write_text(text, encoding='utf-8', newline='\n')
    return dict(Schema=SCHEMA, SchemaVersion=1, SeedSha256=sha256(seed),
                BaseFixtureSha256=base['OutputSha256'], Output=str(output.resolve()),
                OutputSha256=sha256(output), Manifest=base['Manifest'], RecordBytes=BYTES,
                Signature=SIGNATURE, Phases=PHASES, DurationPlcSeconds=sum(s for _,s in PHASES),
                RuntimeAccepted=False, OriginalCodeAndInitialValuesPreserved=True,
                ProductionAlarmOwnerChanged=False)


def decode(raw):
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != BYTES:
        raise ValueError('invalid alarm observer record length/type')
    values = struct.unpack(FORMAT, raw)
    result = dict(zip(HEADER, values))
    if result['SchemaVersion'] != 1 or result['Signature'] != SIGNATURE:
        raise ValueError('alarm observer schema/signature mismatch')
    if result['Revision'] <= 0 or result['Revision'] % 2:
        raise ValueError('observer publication incomplete')
    if not 0 <= result['Phase'] < len(PHASES) or result['Done'] not in (0,1):
        raise ValueError('invalid alarm observer phase')
    result.update(zip(LINTS,values[-len(LINTS):]))
    cells = values[len(HEADER):len(HEADER)+CELLS]
    result['Rows'] = [dict(Name=name, **dict(zip(ROW,cells[n*len(ROW):(n+1)*len(ROW)])))
                      for n,(name,_) in enumerate(PHASES)]
    return result


def sample(comm, attempts=20):
    return fixture.sample(comm, TAG, decode, attempts)


def assess(record):
    if len(record['Rows']) != len(PHASES):
        raise ValueError('incomplete alarm observer row set')
    complete = (record['Done'] == 1 and not record['ProbeFault']
                and all(row['Complete'] == 1 and row['Samples'] > 0
                        and row['ElapsedUs'] >= seconds*1000000
                        for row,(_,seconds) in zip(record['Rows'],PHASES)))
    rows = {row['Name']:row for row in record['Rows']}
    checks = {}
    for prefix in ('Tba', 'Almd'):
        flags = lambda name: rows[name][prefix+'Flags']
        checks[prefix+'SustainedDetected'] = bool(flags('sustained') & 1)
        checks[prefix+'UnlatchedGone'] = not flags('gone') & 1
        checks[prefix+'LatchedAwaitsAck'] = bool(flags('latched_active') & 32)
        checks[prefix+'AckKeepsLatch'] = (flags('ack_live') & 3) == 3 and not flags('ack_live') & 32
        checks[prefix+'ResetLiveRefused'] = bool(flags('reset_live') & 1)
        checks[prefix+'LatchSurvivesGone'] = bool(flags('latched_gone') & 1)
        checks[prefix+'ResetGoneClears'] = not flags('reset_gone') & 1
        checks[prefix+'Suppressed'] = bool(flags('suppressed') & 4)
        checks[prefix+'Unsuppressed'] = not flags('unsuppressed') & 4
        checks[prefix+'CleanupClear'] = not flags('cleanup') & (1|4|8|16)
        checks[prefix+'NoNativeStatusFault'] = all(not row[prefix+'SeenStatus'] for row in record['Rows'])
    return dict(Completed=complete, Checks=checks,
                CoreRegressionsRequired=True, RuntimeProjectionAccepted=False,
                OperatorIsolationQualified=False,
                ShortPulseCountDelta={p:rows['short_pulse'][p+'Count']-rows['baseline'][p+'Count'] for p in ('Tba','Almd')},
                OperatorShelveObserved={p:bool(rows['operator_shelve'][p+'SeenFlags'] & 8) for p in ('Tba','Almd')},
                ShelfExpiryObserved={p:bool(rows['shelf_expiry'][p+'SeenFlags'] & 8) and not rows['shelf_expiry'][p+'Flags'] & 8 for p in ('Tba','Almd')})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('seed', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(argv)
    try:
        report = generate(args.seed,args.output)
    except (ValueError, OSError, AssertionError) as exc:
        parser.exit(2,str(exc)+'\n')
    print(json.dumps(report,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
