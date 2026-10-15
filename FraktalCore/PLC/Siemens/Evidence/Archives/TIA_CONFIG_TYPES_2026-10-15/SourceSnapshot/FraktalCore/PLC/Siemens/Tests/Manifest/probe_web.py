"""Guarded live manifest paging, isolation, access and restart checks."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi, leaf_var
from fraktal_tia_binding import Catalog
spec = importlib.util.spec_from_file_location('unit_probe', HERE.parent/'Unit/probe_web.py')
UNIT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(UNIT)


def probe(out):
    catalog = Catalog.read()
    capacity = catalog.capacities['MAX_CONFIG_PAGE']
    fields = [f['member'] for f in catalog.resolve(['ST_ConfigEntry'])['ST_ConfigEntry']]
    kinds = catalog.enums['E_HmiRequestKind']
    pin = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    checks = []
    completed = False
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row, ensure_ascii=True)+'\n')
            stream.flush()

        def check(label, actual, expected):
            ok = type(actual) is type(expected) and actual == expected
            checks.append((label, ok))
            emit({'event':'check', 'label':label, 'actual':actual, 'expected':expected, 'passed':ok})
            if not ok:
                raise AssertionError(label)

        api = WebApi('169.254.212.49', pin, False)

        def read(path):
            return api.call('PlcProgram.Read', {'var':leaf_var(path.split('.'))})

        def writes(values):
            emit({'event':'mutation-guard', 'status':UNIT.guard(), 'targets':list(values)})
            results = api.bulk([('PlcProgram.Write', {'var':leaf_var(p.split('.')), 'value':v}) for p,v in values.items()])
            if any(error for value,error in results):
                raise AssertionError(str(results))

        def query(root, page, model=0):
            seq = (int(read(root+'.HmiRequest.Sequence'))+1) & 0xffffffff
            if seq == 0:
                seq = 1
            writes({root+'.HmiRequest.Kind':kinds['QUERY_CONFIG'], root+'.HmiRequest.IntValue':page, root+'.HmiRequest.DurationMs':model})
            writes({root+'.HmiRequest.Sequence':seq})
            deadline = time.monotonic()+10
            while time.monotonic() < deadline:
                if read(root+'.HmiResponse.AckSequence') == seq:
                    break
                time.sleep(.02)
            else:
                raise AssertionError('manifest acknowledgement timeout')
            base = root+'.HmiResponse.ConfigPage'
            names = ['Revision', 'PageIndex', 'PageCount', 'EntryCount']
            paths = [base+'.'+n for n in names] + [base+'.Entries[%d].%s'%(i,f) for i in range(1,capacity+1) for f in fields]
            values = []
            # Keep every native batch within the measured CPU's request limit.
            for start in range(0, len(paths), 64):
                results = api.bulk([('PlcProgram.Read', {'var':leaf_var(p.split('.'))}) for p in paths[start:start+64]])
                if any(error for value,error in results):
                    raise AssertionError(str(results))
                values.extend(value for value,error in results)
            page_values = dict(zip(paths, values))
            document = {n:page_values[base+'.'+n] for n in names}
            document['Entries'] = [{f:page_values[base+'.Entries[%d].%s'%(i,f)] for f in fields} for i in range(1,capacity+1)]
            document['Accepted'] = read(root+'.HmiResponse.Accepted')
            document['Diagnostic'] = read(root+'.HmiResponse.Diagnostic')
            emit({'event':'manifest-page', 'root':root, 'requested':page, 'model':model, 'page':document})
            return document

        def manifest(root):
            entries = []
            page = 0
            pages = 1
            revision = read(root+'.ConfigRev')
            while page < pages:
                document = query(root, page)
                check(root+' page %d accepted'%page, document['Accepted'], True)
                check(root+' page %d index'%page, document['PageIndex'], page)
                check(root+' page %d revision'%page, document['Revision'], revision)
                pages = document['PageCount']
                count = document['EntryCount']
                check(root+' page %d bounded'%page, 0 < count <= capacity, True)
                if page < pages-1:
                    check(root+' full page %d'%page, count, capacity)
                entries.extend(document['Entries'][:count])
                check(root+' page %d unused slots cleared'%page,
                      all(e['Scope']==e['Item']==e['ValueText']==e['WriteKey']=='' and e['WriteRevision']==0 and not e['Writable'] for e in document['Entries'][count:]), True)
                page += 1
            return entries

        try:
            api.login('fraktal')
            emit({'event':'connection', 'pin':api.fingerprint, 'version':api.call('Api.Version'), 'permissions':api.call('Api.GetPermissions')})
            out.with_suffix('.certificate.der').write_bytes(api.conn.sock.getpeercert(binary_form=True))
            writes({'GDB_ManifestTest.ReadLock':False})
            before = {p:read(p) for p in ['StationA.HistoryHead','StationA.OutImm.Cycles','GDB_RoutingTest.ManStarts','GDB_UnitTest.CarrierWrites','StationB.HistoryHead']}
            captured = {}
            for root in ('StationA','StationB'):
                entries = manifest(root)
                captured[root] = entries
                check(root+' unique items', len({(e['Scope'],e['Item']) for e in entries}), len(entries))
                check(root+' subtree isolation', all(e['Scope']==root or e['Scope'].startswith(root+'.') for e in entries), True)
                check(root+' all twelve module scopes', len({e['Scope'] for e in entries}), 12)
                check(root+' no write capabilities', all(not e['Writable'] and not e['WriteKey'] and e['WriteRevision']==0 for e in entries), True)
                check(root+' all metadata readable', all(e['Readable'] for e in entries), True)
                values = {(e['Scope'],e['Item']):e['ValueText'] for e in entries}
                check(root+' catalog count', int(values[(root+'.Cell.Gate','CatalogCount')]), 7)
                check(root+' catalog value', int(values[(root+'.Cell.Gate','Catalog/Catalog[6]/Value')]), 6)
                check(root+' catalog label', values[(root+'.Cell.Gate','Catalog/Catalog[6]/Label')], 'Instant')
                check(root+' catalog style', int(values[(root+'.Cell.Gate','Catalog/Catalog[6]/Style')]), catalog.enums['E_CommandStyle']['ONESHOT'])
                check(root+' nested catalog label', values[(root+'.Satellite.Inner.Cell.Gate','Catalog/Catalog[6]/Label')], 'Instant')
                auto = catalog.enums['E_Mode']['AUTO']
                check(root+' AUTO mode policy', int(values[(root,'ModePolicy/ModePolicy[%d]/Style'%auto)]), catalog.enums['E_ModeSwitchStyle']['GRACEFUL'])
                document = query(root, 32767)
                check(root+' beyond-last page accepted', document['Accepted'], True)
                check(root+' beyond-last empty', document['EntryCount'], 0)
                check(root+' previous rows cleared', all(e['Scope']==e['Item']==e['ValueText']=='' for e in document['Entries']), True)
            for path,value in before.items():
                check('query mutation purity '+path, read(path), value)
            for path in ['StationA.Cell.Gate.CatalogCount','StationA.Cell.Gate.Catalog[6].Label','StationA.ConfigCursor.Position','FRK_UnitScratch.EmptyConfigEntry.Item']:
                result = api.bulk([('PlcProgram.Read', {'var':leaf_var(path.split('.'))})])[0]
                check('private read refused '+path, result[1]['code'], 200)
            emit({'event':'mutation-guard', 'status':UNIT.guard(), 'targets':['StationA.ConfigRev']})
            result = api.bulk([('PlcProgram.Write', {'var':leaf_var(['StationA','ConfigRev']), 'value':1})])[0]
            check('revision write refused', result[1]['code'], 205)
            writes({'GDB_ManifestTest.ReadLock':True})
            denied = query('StationA', 0)
            check('read gate retains metadata page', denied['Accepted'], True)
            check('read gate hides values', all(e['ReadLevel']==3 and not e['Readable'] and e['ValueText']=='' for e in denied['Entries'][:denied['EntryCount']]), True)
            peer = query('StationB', 0)
            check('peer read gate unaffected', all(e['Readable'] for e in peer['Entries'][:peer['EntryCount']]), True)
            writes({'GDB_ManifestTest.ReadLock':False})
            for index in (-1, 2147483647):
                invalid = query('StationA', index)
                check('invalid index %d rejected'%index, invalid['Accepted'], False)
                check('invalid index %d page cleared'%index, invalid['EntryCount'], 0)
            invalid = query('StationA', 0, 1)
            check('unavailable model rejected', invalid['Accepted'], False)
            check('unavailable model diagnostic', invalid['Diagnostic'], 'std.error.modelNotAvailable')
            first = query('StationA', 0)
            check('deterministic first page', first['Entries'][:first['EntryCount']], captured['StationA'][:capacity])
            previous = read('StationA.ConfigRev')
            for action in ('halt','run'):
                emit({'event':'mode-guard', 'status':UNIT.guard(), 'action':action})
                result = subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action',action],capture_output=True)
                if result.returncode:
                    raise AssertionError(result.stderr.decode('utf-8-sig',errors='replace'))
                emit({'event':'mode-result', 'action':action, 'output':result.stdout.decode('utf-8-sig').strip()})
            check('restart revision changed', read('StationA.ConfigRev') != previous, True)
            restarted = query('StationA', 0)
            check('fresh query after restart', restarted['Accepted'], True)
            check('page follows current revision', restarted['Revision'], read('StationA.ConfigRev'))
            completed = True
            (out.with_suffix('.entries.json')).write_bytes((json.dumps(captured,indent=2)+'\n').encode('ascii'))
        finally:
            api.conn.close()
            if not completed:
                checks.append(('probe completed',False))
            emit({'event':'summary', 'checks':len(checks), 'failures':sum(not ok for label,ok in checks), 'completed':completed})
            suite = ET.Element('testsuite',name='Fraktal.TIA.Manifest',tests=str(len(checks)),failures=str(sum(not ok for label,ok in checks)))
            for label,ok in checks:
                case = ET.SubElement(suite,'testcase',name=label)
                if not ok:
                    ET.SubElement(case,'failure',message=label)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'),encoding='utf-8',xml_declaration=True)


if __name__ == '__main__':
    probe(Path(sys.argv[1]))
