"""Compile generated ALMD cases through the shared offline native probe gate."""
import argparse
import json
from pathlib import Path

import fraktal_ab_native_alarm_probe as probe
from fraktal_ab_v38_native_gate import compile_cases


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('generation',type=Path)
    parser.add_argument('directory',type=Path)
    args = parser.parse_args(argv)
    report = compile_cases(json.loads(args.generation.read_text(encoding='utf-8')),
                           args.directory.resolve(),tuple(case.key for case in probe.CASES),
                           expected_schema=probe.SCHEMA,expected_profile=probe.PROFILE.key)
    print(json.dumps(report,indent=2))
    return 0 if report['ConformsToExpectations'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
