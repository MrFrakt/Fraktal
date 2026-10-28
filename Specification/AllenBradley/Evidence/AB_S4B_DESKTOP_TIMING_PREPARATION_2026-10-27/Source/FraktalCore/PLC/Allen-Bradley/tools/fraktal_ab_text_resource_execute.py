"""Exact local Echo text-resource acceptance using the shared restored matrix."""
import argparse
import json
from pathlib import Path

import fraktal_ab_resource_execute as numeric
import fraktal_ab_station as station
import fraktal_ab_text_resource_demo as text
import fraktal_ab_tower_execute as tower


class TextResourceRun(numeric.ResourceRun):
    def expected_resources(self, case):
        expected = super().expected_resources(case)
        # The fixture's handled-NOK branch exits before confirmation MARK230.
        if case != 'handled_NOK':
            expected.append((8,text.SUBJECT,text.VALUE))
        return expected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-fixture',action='store_true')
    parser.add_argument('--expect-serial',required=True)
    parser.add_argument('--credential-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    if (not args.execute_fixture or args.expect_serial.upper() != '601FC87B'
            or station.module_name() != 'fraktal_ab_text_resource_demo'):
        parser.error('explicit arm, exact text-resource declaration and local serial 601FC87B required')
    if args.output.exists():
        parser.error('refusing existing evidence output')
    app = station.application()
    account = next(a for a in json.loads(args.credential_file.read_text())['users'] if a['level']==4)
    if account['user'] not in {user.name for user in app.access_users}:
        parser.error('credential file does not name a fixture account')
    args.core_regressions = True
    return tower.execute_fixture(args,app,account,run_type=TextResourceRun,
                                  schema='fraktal.ab.text-resource-live-fixture')


if __name__=='__main__': raise SystemExit(main())
