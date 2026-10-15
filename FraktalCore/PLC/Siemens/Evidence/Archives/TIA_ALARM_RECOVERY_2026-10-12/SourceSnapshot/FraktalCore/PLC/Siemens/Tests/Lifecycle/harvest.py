"""Save raw SDK values and fail unless every PLC assertion completed successfully."""
import argparse
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[1] / 'Spikes/S12_TypeMap/simulator.ps1'


def harvest(manifest_path, output):
    manifest = json.loads(manifest_path.read_text())
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        str(SIM), '-Action', 'read', '-DataBlocks', 'GDB_Lifecycle,StationA,FRK_Clock',
        '-Match', 'GDB_Lifecycle|Clamp.Timing|FRK_Clock'], capture_output=True)
    with output.open('xb') as stream: stream.write(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError('SDK harvest failed; raw output preserved')
    rows = [json.loads(line) for line in result.stdout.decode('utf-8-sig').splitlines() if line.strip()]
    if any(row['event'] == 'tag-failed' for row in rows): raise RuntimeError('SDK tag read failed')
    values = {row['name']: row['value'] for row in rows if row['event'] == 'tag'}
    expected = {'GDB_Lifecycle.CaseNo': manifest['cases'], 'GDB_Lifecycle.Checks': manifest['checks'],
                'GDB_Lifecycle.Failed': 0, 'GDB_Lifecycle.Passed': True,
                'GDB_Lifecycle.FirstFailedCase': -1, 'GDB_Lifecycle.FirstFailedCheck': -1}
    failed = [name for name, value in expected.items() if values.get(name) != value]
    suite = ET.Element('testsuite', name='Fraktal.TIA.SharedCommandKernel', tests=str(manifest['checks']),
                       failures=str(int(bool(failed))))
    for index, expression in enumerate(manifest['assertions'], 1):
        case = ET.SubElement(suite, 'testcase', classname='PLC.lifecycle', name='%03d %s' % (index, expression))
        if failed and index == 1: ET.SubElement(case, 'failure', message='PLC completion counters failed').text = ', '.join(failed)
    ET.ElementTree(suite).write(output.with_suffix('.junit.xml'), encoding='utf-8', xml_declaration=True)
    if failed: raise AssertionError('PLC counters failed: ' + ', '.join(failed))
    print(json.dumps({'cases': manifest['cases'], 'assertions': manifest['checks'], 'passed': True,
                      'production_clock_ms': values['FRK_Clock.NowMs']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); harvest(args.manifest, args.output)
