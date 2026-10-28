"""Read native-observer evidence from exact local Echo; performs no writes.

Set FRAKTAL_AB_DECLARATION=fraktal_ab_tower_demo before invocation. The
instrumented fixture must have been independently prepared and authorized.
Clock setting, mode changes and Echo time scaling are outside this collector.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

import fraktal_ab_native_observer as observer


def collect(comm, seconds, *, monotonic=time.monotonic, sleep=time.sleep):
    if not 5 <= seconds <= 180:
        raise ValueError('observation must last 5..180 host seconds')
    rows = []
    start = monotonic()
    while True:
        comm.guard()
        before = monotonic()
        value = observer.sample(comm)
        after = monotonic()
        rows.append(dict(hostMidpoint=(before + after) / 2 - start,
                         readSeconds=after - before, values=value))
        if after - start >= seconds:
            break
        sleep(min(.5, seconds - (after - start)))
    result = observer.assess(rows[0]['values'], rows[-1]['values'],
                             rows[-1]['hostMidpoint'] - rows[0]['hostMidpoint'])
    result['FaultFree'] = all(not (row['values']['MajorFaultBits'] or row['values']['MinorFaultBits'])
                              for row in rows)
    result['ObservedWallMinuteTransitions'] = sum(
        second['values']['Wall'] // 60_000_000 > first['values']['Wall'] // 60_000_000
        for first, second in zip(rows, rows[1:]))
    result['LegacyIntervalRangeUs'] = [min(row['values']['LegacyIntervalUs'] for row in rows),
                                      max(row['values']['LegacyIntervalUs'] for row in rows)]
    result['NativeTaskIntervalExtremaUs'] = dict(
        minimum=rows[-1]['values']['MinIntervalUs'], maximum=rows[-1]['values']['MaxIntervalUs'])
    result['ObservedCstIntervalExtremaUs'] = dict(
        minimum=rows[-1]['values']['MinCst'], maximum=rows[-1]['values']['MaxCst'])
    return dict(Schema=observer.SCHEMA + '-observation', SchemaVersion=1,
                ControllerWrites=0, rows=rows, observations=result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expect-serial', required=True)
    parser.add_argument('--seconds', type=float, default=75)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if os.environ.get('FRAKTAL_AB_DECLARATION') != 'fraktal_ab_tower_demo':
        parser.exit(2, 'exact tower declaration must be selected before import\n')
    if args.output.exists() or not 5 <= args.seconds <= 180:
        parser.exit(2, 'new output and duration 5..180 seconds required\n')
    try:
        serial = int(args.expect_serial, 16)
    except ValueError:
        parser.exit(2, 'invalid expected serial\n')
    if serial != 0x601FC87B:
        parser.exit(2, 'only the local 601FC87B Echo fixture is supported\n')
    # Imports depend on the selected declaration. No command capability is
    # invoked: Guarded is reused for identity and manifest validation only.
    from pylogix import PLC
    from fraktal_ab_part_execute import Guarded
    import fraktal_ab_tower_demo as tower
    report = dict(Schema=observer.SCHEMA + '-observation', SchemaVersion=1,
                  ControllerWrites=0, serial=args.expect_serial, Completed=False)
    try:
        with PLC('127.0.0.1') as native:
            native.ProcessorSlot = 0
            native.ConnectionSize = 4000
            guarded = Guarded(native, serial, tower.application())
            report.update(collect(guarded, args.seconds))
            report['Completed'] = True
    except Exception as exc:
        report['Error'] = type(exc).__name__ + ': ' + str(exc)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))
    return 0 if report['Completed'] and report['observations']['FaultFree'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
