"""Pinned native read-back of the completed command-kernel test image."""
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
import fraktal_tia_declaration as DECL
from tia_webapi import WebApi, leaf_var
from make_fixture import declaration


def variable(path): return leaf_var(path.split('.'))


def probe(out):
    manifest = json.loads(Path(os.environ['FRAKTAL_LIFECYCLE_MANIFEST']).read_text())
    model = DECL.validate(declaration())
    lookup = {t.name: t for t in model.types}
    expected = {}
    for item in model.instances:
        expected[item.path + '.Status.Name'] = item.path
        expected[item.path + '.Status.TypeKey'] = lookup[item.type_name].type_key
        expected[item.path + '.Status.ModuleType'] = model.core.tiers[lookup[item.type_name].tier]
        expected[item.path + '.Status.State'] = 0
        expected[item.path + '.ParCfg.SchemaVersion'] = 2
        expected[item.path + '.OutImm.InitCount'] = 1
        for name in ('Busy', 'Done', 'Error', 'Aborted', 'Held'):
            expected[item.path + '.' + name] = False
    cm = 'StationA.Cell.Clamp'
    expected.update({
        'GDB_Lifecycle.Passed': True, 'GDB_Lifecycle.Checks': manifest['checks'],
        'GDB_Lifecycle.CaseNo': manifest['cases'], 'GDB_Lifecycle.Failed': 0,
        'GDB_Lifecycle.FirstFailedCase': -1, 'GDB_Lifecycle.FirstFailedCheck': -1,
        cm + '.Timing.LastCmdTime': 10, cm + '.Timing.Rows.1.Count': 4,
        cm + '.Timing.Rows.1.Minimum': 0, cm + '.Timing.Rows.1.Maximum': 20,
        cm + '.Timing.Rows.1.Avg': 13, cm + '.OutImm.Output': False,
    })
    # Arrays use native [index] rather than browse segment syntax.
    expected = {name.replace('.Rows.1.', '.Rows[1].'): value for name, value in expected.items()}
    private = [cm + '.Core.Command', cm + '.LatchedParCmd.Value', cm + '.Device.InitCount',
               'StationA.Hal.Cell.Clamp.Permit', 'FRK_Registry.Count',
               'FRK_Clock.NowMs', 'GDB_LifecycleDefaults.Core.Exec']
    pin = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin'
    failed = []
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(value): stream.write(json.dumps(value, ensure_ascii=True) + '\n'); stream.flush()
        api = WebApi('169.254.212.49', pin, False)
        try:
            api.login('fraktal')
            emit({'event': 'connection', 'certificate_sha256': api.fingerprint,
                  'version': api.call('Api.Version'), 'permissions': api.call('Api.GetPermissions')})
            for root in model.roots:
                emit({'event': 'root-browse', 'root': root.name,
                      'children': api.call('PlcProgram.Browse', {'var': variable(root.name), 'mode': 'children'})})
            names = list(expected)
            for offset in range(0, len(names), 20):
                batch = names[offset:offset + 20]
                replies = api.bulk([('PlcProgram.Read', {'var': variable(name)}) for name in batch])
                for name, (value, error) in zip(batch, replies):
                    passed = error is None and type(value) is type(expected[name]) and value == expected[name]
                    emit({'event': 'witness', 'name': name, 'value': value, 'expected': expected[name], 'error': error, 'passed': passed})
                    if not passed: failed.append(name)
            for name, (value, error) in zip(private, api.bulk([('PlcProgram.Read', {'var': variable(name)}) for name in private])):
                passed = error is not None and error.get('code') == 200
                emit({'event': 'private-read', 'name': name, 'value': value, 'error': error, 'passed': passed})
                if not passed: failed.append(name)
            emit({'event': 'summary', 'public': len(expected), 'private': len(private), 'failed': failed, 'passed': not failed})
        finally:
            if api.token: api.call('Api.Logout')
            api.conn.close()
    return not failed


if __name__ == '__main__': raise SystemExit(0 if probe(Path(sys.argv[1])) else 1)
