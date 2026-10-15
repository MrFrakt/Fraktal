"""Restore the test-only values changed before the transport rejection in trial13."""
import importlib.util
from pathlib import Path
import sys

path = Path('C:/Projects/Fraktal/FraktalCore/PLC/Siemens/Tests/Config/probe_web.py')
spec = importlib.util.spec_from_file_location('config_acceptance', path)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
# Reuse the native acceptance writer with a small guarded preparation routine.
import os, json, time
api = module.WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin', False)
with Path(sys.argv[1]).open('x', encoding='ascii', newline='\n') as stream:
    def write(values):
        stream.write(json.dumps({'guard': module.UNIT.guard(), 'targets': list(values)})+'\n'); stream.flush()
        rows = api.bulk([('PlcProgram.Write', {'var': module.leaf_var(p.split('.')), 'value': v}) for p,v in values.items()])
        assert not any(error for value,error in rows)
    def read(field, root='StationA'): return api.call('PlcProgram.Read', {'var': module.leaf_var((root+'.'+field).split('.'))})
    def request(kind, root='StationA', **fields):
        sequence = (read('HmiRequest.Sequence', root)+1)&0xffffffff or 1
        values = dict(Kind=module.Catalog.read().enums['E_HmiRequestKind'][kind], TargetPath='', NameValue='', TextValue='', IntValue=0, DurationMs=0, User='', Secret='')
        values.update(fields)
        write({root+'.HmiRequest.'+k:v for k,v in values.items()}); write({root+'.HmiRequest.Sequence':sequence})
        deadline = time.monotonic()+8
        while read('HmiResponse.AckSequence',root) != sequence and time.monotonic()<deadline: time.sleep(.02)
        assert read('HmiResponse.Accepted',root)
        return sequence
    try:
        api.login('fraktal')
        seq=request('LOGIN',User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
        deadline=time.monotonic()+8
        while (read('Access.LoginBusy') or read('Access.LoginResultSequence') != seq) and time.monotonic()<deadline: time.sleep(.02)
        assert read('Access.CurrentLevel')==4
        for key, value, revision in (('preset','10',2), ('siteLabel','bench',1), ('enabled','true',1)):
            request('WRITE_CONFIG', TargetPath='StationA', NameValue=key, TextValue=value, IntValue=revision)
        request('LOGOUT')
        request('LOGOUT',root='StationB')
        stream.write(json.dumps({'defaults_restored': True})+'\n')
    finally: api.conn.close()
