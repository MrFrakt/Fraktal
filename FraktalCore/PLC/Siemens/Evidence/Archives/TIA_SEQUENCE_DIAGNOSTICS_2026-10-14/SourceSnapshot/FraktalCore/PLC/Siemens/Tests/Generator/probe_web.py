"""Read the generated forest through pinned native Web API; no writes."""
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
import fraktal_tia_declaration as DECL
from tia_webapi import WebApi


def variable(path):
    return '.'.join('"' + part + '"' for part in path.split('.'))


def probe(out):
    model = DECL.read(HERE.parent / 'Declaration/two_root_forest.json')
    types = {t.name:t for t in model.types}
    expected = {}
    for item in model.instances:
        t = types[item.type_name]
        expected[item.path + '.Status.Name'] = item.path
        expected[item.path + '.Status.TypeKey'] = t.type_key
        expected[item.path + '.Status.ModuleType'] = model.core.tiers[t.tier]
        expected[item.path + '.ParCfg.SchemaVersion'] = 1
        for name in ('Busy', 'Done', 'Error', 'Aborted', 'Held'):
            expected[item.path + '.' + name] = False
    for name, sample in [('StationA.Cell.Clamp',42),('StationA.Cell.Gate',43),('StationB.Cell.Clamp',84),('StationB.Cell.Gate',85)]:
        expected[name + '.OutImm.Sample'] = sample
    expected.update({'GDB_FrameProbe.Passed':True,'GDB_FrameProbe.Checks':103,
                     'GDB_FrameProbe.FailedChecks':0,'GDB_FrameProbe.OverflowPassed':True,
                     'GDB_FrameProbe.BadParentPassed':True})
    private = ['StationA.Core.RegIndex', 'StationB.Cell.Core.RegIndex',
               'StationA.Hal.Cell.Clamp.Sample', 'FRK_Registry.Count', 'GDB_RegistryFaultProbe.Status.Name']
    pin = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin'
    failed = []
    with out.open('x',encoding='ascii',newline='\n') as stream:
        def emit(value): stream.write(json.dumps(value,ensure_ascii=True)+'\n');stream.flush()
        api = WebApi('169.254.212.49',pin,False)
        try:
            api.login('fraktal')
            emit({'event':'connection','certificate_sha256':api.fingerprint,
                  'version':api.call('Api.Version'),'permissions':api.call('Api.GetPermissions')})
            for root in model.roots:
                children=api.call('PlcProgram.Browse',{'var':variable(root.name),'mode':'children'})
                emit({'event':'root-browse','root':root.name,'children':children})
            names=list(expected)
            for offset in range(0,len(names),20):
                batch=names[offset:offset+20]
                replies=api.bulk([('PlcProgram.Read',{'var':variable(name)}) for name in batch])
                for name,(value,error) in zip(batch,replies):
                    passed=error is None and type(value) is type(expected[name]) and value==expected[name]
                    emit({'event':'witness','name':name,'value':value,'expected':expected[name],'error':error,'passed':passed})
                    if not passed:failed.append(name)
            replies=api.bulk([('PlcProgram.Read',{'var':variable(name)}) for name in private])
            for name,(value,error) in zip(private,replies):
                passed=error is not None and error.get('code')==200
                emit({'event':'private-read','name':name,'value':value,'error':error,'passed':passed})
                if not passed:failed.append(name)
            emit({'event':'summary','public':len(expected),'private':len(private),'failed':failed,'passed':not failed})
        finally:
            if api.token: api.call('Api.Logout')
            api.conn.close()
    return not failed


if __name__ == '__main__':
    raise SystemExit(0 if probe(Path(sys.argv[1])) else 1)
