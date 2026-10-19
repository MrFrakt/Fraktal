"""Exact local Echo resource fixture acceptance, sharing tower/Part cleanup.

Only the declared simulation inputs and validated mailbox/configuration path
are writable. No resource/ring/provider state, clock or electrical I/O writes.
"""
import argparse
import json
from pathlib import Path

import fraktal_ab_part_execute as part_fixture
import fraktal_ab_station as station
import fraktal_ab_tower_execute as tower_fixture


class ResourceRun(part_fixture.Run):
    def record(self, language, case, before, counters, **extra):
        row = super().record(language, case, before, counters, **extra)
        resources = [event for event in row['events'] if event['Kind'] in (7,8)]
        # The receive confirmation is earlier than start; abort/fault before
        # either boundary may legitimately retain only the earlier event.
        kinds = [event['Kind'] for event in resources]
        self.check(kinds in ([], [8], [8,7]), 'resource order or duplicate confirmation')
        for event in resources:
            wanted = {7:('Fixture.UpperDie','314'), 8:('Fixture.BlankLot','20261018')}[event['Kind']]
            self.check((event['Subject'], event['Value']) == wanted,
                       'captured resource subject/value mismatch')
            self.check(not event['PartUid'] and event['Verdict'] == event['ReasonCode'] == 0,
                       'resource event leaked part identity or fault semantics')
        if case in ('OK','handled_NOK','HELD_resume'):
            self.check(kinds == [8,7], 'completed cycle did not confirm both resources')
        row['resourceChecksPassed'] = True
        row['resourceCount'] = len(resources)
        return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-fixture',action='store_true')
    parser.add_argument('--expect-serial',required=True)
    parser.add_argument('--credential-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    if (not args.execute_fixture or args.expect_serial.upper() != '601FC87B'
            or station.module_name() != 'fraktal_ab_resource_demo'):
        parser.error('explicit arm, exact resource declaration and local serial 601FC87B required')
    if args.output.exists():
        parser.error('refusing existing evidence output')
    app = station.application()
    account = next(a for a in json.loads(args.credential_file.read_text())['users'] if a['level']==4)
    if account['user'] not in {u.name for u in app.access_users}:
        parser.error('credential file does not name a fixture account')
    args.core_regressions = True
    return tower_fixture.execute_fixture(args,app,account,run_type=ResourceRun,
                                         schema='fraktal.ab.resource-live-fixture')


if __name__ == '__main__':
    raise SystemExit(main())
