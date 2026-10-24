"""Exact local Echo genealogy acceptance through the restored Part matrix."""
import argparse
import json
from pathlib import Path

import fraktal_ab_genealogy_demo as fixture
import fraktal_ab_station as station
import fraktal_ab_text_resource_execute as text
import fraktal_ab_tower_execute as tower


class GenealogyRun(text.TextResourceRun):
    def record(self, language, case, before, counters, **extra):
        row = super().record(language, case, before, counters, **extra)
        expected = list(fixture.PARENTS) if case in ('OK','HELD_resume','single_reset_restart') else []
        for event in row['events']:
            wanted = expected if event['Kind'] == 3 else []
            self.check(event['Parents'] == wanted, 'captured genealogy mismatch at lifecycle boundary')
        current = row['part']
        self.check(current['Part/ParentCount'] == len(expected), 'live parent count mismatch')
        self.check([current[f'Part/Parents[{index+1}]'] for index in range(2)] ==
                   expected + ['']*(2-len(expected)), 'live genealogy or cleared slot mismatch')
        row['genealogyChecksPassed'] = True
        return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-fixture',action='store_true')
    parser.add_argument('--expect-serial',required=True)
    parser.add_argument('--credential-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    if (not args.execute_fixture or args.expect_serial.upper() != '601FC87B'
            or station.module_name() != 'fraktal_ab_genealogy_demo'):
        parser.error('explicit arm, exact genealogy declaration and local serial 601FC87B required')
    if args.output.exists():
        parser.error('refusing existing evidence output')
    app = station.application()
    account = next(a for a in json.loads(args.credential_file.read_text())['users'] if a['level']==4)
    if account['user'] not in {user.name for user in app.access_users}:
        parser.error('credential file does not name a fixture account')
    args.core_regressions = True
    return tower.execute_fixture(args,app,account,run_type=GenealogyRun,
                                  schema='fraktal.ab.genealogy-live-fixture')


if __name__=='__main__': raise SystemExit(main())
