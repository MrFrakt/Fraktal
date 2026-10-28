"""Read private native-alarm phase results from exact local Echo; never write.

The prepared fixture must be independently authorized and downloaded. The host
does not trigger phases or commands, restart the probe, or alter native alarms.
"""
import argparse
import json
import os
from pathlib import Path
import time

import fraktal_ab_alarm_observer as observer
import fraktal_ab_native_observer as timing


def collect(comm, timeout, *, monotonic=time.monotonic, sleep=time.sleep):
    if not 5 <= timeout <= 180:
        raise ValueError('observation timeout must be 5..180 host seconds')
    start, rows, first_run, fault_free = monotonic(), [], None, True
    while True:
        comm.guard()
        native = timing.sample(comm)
        record = observer.sample(comm)
        if first_run is None:
            first_run = record['RunStartCst']
        elif record['RunStartCst'] != first_run:
            raise ValueError('alarm observer restarted during observation')
        fault_free &= not (native['MajorFaultBits'] or native['MinorFaultBits'])
        elapsed = monotonic() - start
        rows.append(dict(HostSeconds=elapsed, Phase=record['Phase'], Done=record['Done'],
                         ProbeFault=record['ProbeFault'], Scans=record['Scans'],
                         MajorFaultBits=native['MajorFaultBits'], MinorFaultBits=native['MinorFaultBits']))
        if record['Done'] or elapsed >= timeout:
            break
        sleep(min(.5,timeout-elapsed))
    result = observer.assess(record)
    return dict(Schema=observer.SCHEMA+'-observation', SchemaVersion=1,
                ControllerWrites=0, FaultFree=fault_free, Observation=result,
                Record=record, Samples=rows,
                BaseComparisonPassed=fault_free and result['Completed'] and all(result['Checks'].values()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expect-serial',required=True)
    parser.add_argument('--timeout',type=float,default=150)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    if os.environ.get('FRAKTAL_AB_DECLARATION') != 'fraktal_ab_tower_demo':
        parser.error('exact tower declaration must be selected before import')
    if args.expect_serial.upper() != '601FC87B' or args.output.exists() or not 5 <= args.timeout <= 180:
        parser.error('exact local serial, new output and timeout 5..180 seconds required')
    from pylogix import PLC
    from fraktal_ab_part_execute import Guarded
    import fraktal_ab_tower_demo as tower
    report = dict(Schema=observer.SCHEMA+'-observation', SchemaVersion=1,
                  ControllerWrites=0, BaseComparisonPassed=False)
    try:
        with PLC('127.0.0.1') as native:
            native.ProcessorSlot, native.ConnectionSize = 0, 4000
            report.update(collect(Guarded(native,0x601FC87B,tower.application()),args.timeout))
    except Exception as exc:
        report['Error'] = type(exc).__name__+': '+str(exc)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('Record','Samples')},indent=2))
    return 0 if report['BaseComparisonPassed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
