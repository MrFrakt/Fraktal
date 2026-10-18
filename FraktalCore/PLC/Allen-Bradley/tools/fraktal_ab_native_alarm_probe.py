"""Generate offline L81E/v38 native-alarm feasibility cases, never deploy.

ALMD is a provider comparison, not the Fraktal lifecycle owner. Its object tag
requires Read/Write access on this target; that is not an approved command
surface. Stimulus tags are inert/read-only and the S12 task disables outputs.
Tag-based cases use the v38 native export spelling, not the incompatible
RM014 XML example. These are offline probes; runtime projection and operator
command isolation remain separate gates.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, scalar_tag, sha256
import fraktal_ab_s12_type_probe as s12

SCHEMA = 'fraktal.ab.v38-native-alarm-probe'
PROFILE = s12.ProbeProfile('v38-5580-native-alarm-exploratory', '1756-L81E', '38',
                          'offline-not-runtime-accepted', ())
INPUT = 'FRK_NativeAlarmInput'
ALMD = 'FRK_NativeAlmd'
REASON = 'FRK_NativeAlarmReason'
SOURCE = 'FRK_NativeAlarmSource'
ALARM_NAME = 'Projected'
TAG_ALARM = INPUT + '.@Alarms.' + ALARM_NAME


@dataclass(frozen=True)
class Case:
    key: str
    expected: str
    statements: tuple[str, ...]
    tag_based: bool = False


CASES = (
    Case('almd_st', 'pass', (
        f'{ALMD}.EnableIn := 1;', f'{ALMD}.Condition := 1;',
        f'{ALMD}.Latched := 1;', f'{ALMD}.AckRequired := 0;',
        f'{ALMD}.Severity := 700;', f'{ALMD}.MinDurationPRE := 0;',
        f'ALMD({ALMD},{INPUT}.0,0,0,0,0);',
        f'{s12.TAG} := 0;', f'IF {ALMD}.InAlarm THEN {s12.TAG} := 1; END_IF;',
    )),
    Case('invalid_alarm_attribute', 'fail', (
        f'IF {ALMD}.FRK_NotAnAttribute THEN {s12.TAG} := 1; END_IF;',
    )),
    Case('tag_alarm_st', 'pass', (
        f'{TAG_ALARM}.ProgSuppress := 0;',
        f'{TAG_ALARM}.ProgUnsuppress := 1;',
        f'{TAG_ALARM}.ProgUnshelve := 1;',
        f'{TAG_ALARM}.ProgEnable := 1;',
        f'{s12.TAG} := 0;',
        f'IF {TAG_ALARM}.InAlarm THEN {s12.TAG} := {s12.TAG} + 1; END_IF;',
        f'IF {TAG_ALARM}.Acked THEN {s12.TAG} := {s12.TAG} + 2; END_IF;',
        f'IF {TAG_ALARM}.Suppressed THEN {s12.TAG} := {s12.TAG} + 4; END_IF;',
        f'IF {TAG_ALARM}.Shelved THEN {s12.TAG} := {s12.TAG} + 8; END_IF;',
        f'IF {TAG_ALARM}.Disabled THEN {s12.TAG} := {s12.TAG} + 16; END_IF;',
    ), tag_based=True),
    Case('invalid_tag_alarm_attribute', 'fail', (
        f'IF {TAG_ALARM}.FRK_NotAnAttribute THEN {s12.TAG} := 1; END_IF;',
    ), tag_based=True),
    Case('invalid_tag_alarm_status_write', 'fail', (
        f'{TAG_ALARM}.InAlarm := 1;',
    ), tag_based=True),
    # v38 help calls OperShelve programmatically read-only, but the tested
    # compiler accepts this assignment. Observe the discrepancy explicitly;
    # neither compiler outcome establishes runtime effect or authorization.
    Case('tag_alarm_operator_write_discriminator', 'observe', (
        f'{TAG_ALARM}.OperShelve := 1;',
    ), tag_based=True),
)


def tag_alarm_tags():
    """Disposable condition derived from a native L81E/v38 export.

    '= 1' is an enum value; 'Input = 1' is rejected. The native exporter also
    spells OnDelay/OffDelay, AlarmSet*Included and EvaluationPeriod differently
    from RM014's XML example. Keep all requested metadata in read-back checks.
    """
    alarm = f'''<AlarmConditions>
<AlarmCondition Name="{ALARM_NAME}" Input=".0" ConditionType="TRIP" Limit="0.0"
Severity="700" OnDelay="0" OffDelay="0" ShelveDuration="0" MaxShelveDuration="1"
Deadband="0.0" Used="true" InFault="false" AckRequired="false" Latched="false"
AlarmSetOperIncluded="false" AlarmSetRollupIncluded="true"
EvaluationPeriod="500 millisecond" Expression="= 1"
AssocTag1="{REASON}" AssocTag2="{SOURCE}">
<AlarmConfig><Messages><Message Type="CAM"><Text Lang="en-US"><![CDATA[Fraktal native projection probe]]></Text></Message></Messages>
<AlarmClass><![CDATA[FraktalProbe]]></AlarmClass></AlarmConfig>
</AlarmCondition></AlarmConditions>'''
    owner = scalar_tag(INPUT, 'DINT', 'Decimal', '0', 'Read Only')
    owner = replace_once(owner, '<Data Format="L5K">', alarm + '\n<Data Format="L5K">')
    return [owner, scalar_tag(REASON, 'DINT', 'Decimal', '10101', 'Read Only'),
            scalar_tag(SOURCE, 'DINT', 'Decimal', '0', 'Read Only')]


def generate_all(seed: Path, directory: Path):
    if directory.exists():
        raise ValueError('native alarm probe directory must be new')
    source_hash = sha256(seed)
    # Validate the seed through the shared guarded emitter before leaving outputs.
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        for case in CASES:
            candidate = s12.Candidate(case.key, 'native alarm feasibility', 'DINT',
                                      None, 0, '\n'.join(case.statements))
            path = Path(temporary)/(case.key + '.L5X')
            s12.generate_case(seed, path, candidate, 'use', profile=PROFILE)
            text = path.read_text(encoding='utf-8')
            text = replace_once(text, 'ExternalAccess="Read/Write"', 'ExternalAccess="Read Only"')
            extra = tag_alarm_tags() if case.tag_based else [
                scalar_tag(INPUT,'DINT','Decimal','0','Read Only'),
                f'<Tag Name="{ALMD}" TagType="Base" DataType="ALARM_DIGITAL" Constant="false" ExternalAccess="Read/Write"/>']
            # First closing Tags belongs to the controller, before the Program.
            index = text.index('</Tags>')
            text = text[:index] + '\n'.join(extra) + '\n' + text[index:]
            path.write_text(text,encoding='utf-8',newline='\n')
        if sha256(seed) != source_hash:
            raise ValueError('seed changed during alarm probe generation')
        directory.mkdir(parents=True, exist_ok=False)
        rows = []
        for case in CASES:
            output = directory/(case.key + '.L5X')
            output.write_bytes((Path(temporary)/output.name).read_bytes())
            rows.append(dict(Case=case.key, ExpectedBuild=case.expected,
                             Output=str(output.resolve()), OutputSha256=sha256(output)))
    result = dict(Schema=SCHEMA,SchemaVersion=1,Profile=PROFILE.key,
                  Controller=PROFILE.controller,MajorRevision=PROFILE.revision,
                  SourceSha256=source_hash,InputUnchanged=True,RuntimeAccepted=False,
                  ProductionAlarmOwnerChanged=False,Cases=rows)
    (directory/'generation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('seed',type=Path)
    parser.add_argument('directory',type=Path)
    args = parser.parse_args(argv)
    try:
        report = generate_all(args.seed,args.directory)
    except (OSError,ValueError) as exc:
        parser.exit(2,str(exc)+'\n')
    print(json.dumps(report,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
