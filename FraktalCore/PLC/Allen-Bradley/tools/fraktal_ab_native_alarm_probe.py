"""Generate offline L81E/v38 native-alarm feasibility cases, never deploy.

ALMD is a provider comparison, not the Fraktal lifecycle owner. Its object tag
requires Read/Write access on this target; that is not an approved command
surface. Stimulus tags are inert/read-only and the S12 task disables outputs.
Tag-based projection import remains a separate, unaccepted experiment.
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


@dataclass(frozen=True)
class Case:
    key: str
    expected: str
    statements: tuple[str, ...]


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
)


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
            extra = [scalar_tag(INPUT,'DINT','Decimal','0','Read Only'),
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
