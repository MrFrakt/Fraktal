"""Native config capability, atomic model change and local-retain acceptance."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from tia_webapi import WebApi, leaf_var
from fraktal_tia_binding import Catalog
spec = importlib.util.spec_from_file_location('unit_guard', HERE.parent / 'Unit/probe_web.py')
UNIT = importlib.util.module_from_spec(spec); spec.loader.exec_module(UNIT)


def probe(out):
    catalog = Catalog.read(); kinds = catalog.enums['E_HmiRequestKind']; modes = catalog.enums['E_Mode']
    checks = []; complete = False
    pin = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin'
    api = WebApi('169.254.212.49', pin, False)
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row, ensure_ascii=True) + '\n'); stream.flush()

        def read(path):
            return api.call('PlcProgram.Read', {'var': leaf_var(path.split('.'))})

        def check(label, actual, expected):
            ok = type(actual) is type(expected) and actual == expected
            checks.append((label, ok)); emit({'event': 'check', 'label': label, 'actual': actual, 'expected': expected, 'passed': ok})
            if not ok:
                raise AssertionError(label)

        def wait(predicate, label):
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if predicate(): return
                time.sleep(.02)
            raise AssertionError(label)

        def write(values):
            emit({'event': 'mutation-guard', 'status': UNIT.guard(), 'targets': list(values)})
            replies = api.bulk([('PlcProgram.Write', {'var': leaf_var(p.split('.')), 'value': v}) for p, v in values.items()])
            if any(error for value, error in replies):
                emit({'event': 'write-errors', 'errors': [{'path': path, 'code': error['code']} for path, (value, error) in zip(values, replies) if error]})
                raise AssertionError('native write refused')

        def request(kind, root='StationA', **fields):
            seq = (int(read(root + '.HmiRequest.Sequence')) + 1) & 0xffffffff or 1
            values = dict(Kind=kinds[kind], TargetPath='', NameValue='', TextValue='', IntValue=0,
                          BoolValue=False, DurationMs=0, User='', Secret='')
            values.update(fields)
            write({root + '.HmiRequest.' + n: v for n, v in values.items()})
            write({root + '.HmiRequest.Sequence': seq})
            wait(lambda: read(root + '.HmiResponse.AckSequence') == seq, 'mailbox ack')
            return seq, read(root + '.HmiResponse.Accepted')

        def login(user='admin'):
            seq, ok = request('LOGIN', User=user, Secret=os.environ['FRAKTAL_TIA_' + user.upper() + '_PIN'])
            check(user + ' login consumed', ok, True)
            wait(lambda: read('StationA.Access.LoginResultSequence') == seq and not read('StationA.Access.LoginBusy'), 'login result')
            check(user + ' authenticated', read('StationA.Access.CurrentLevel'), 4 if user == 'admin' else 1)

        def edit(scope, key, value, revision=2, model=0):
            return request('WRITE_CONFIG', TargetPath=scope, NameValue=key, TextValue=value, IntValue=revision, DurationMs=model)[1]

        def query(model=0):
            entries = []; index = 0
            names = ('Scope', 'Item', 'ValueText', 'WriteKey', 'WriteRevision', 'ConfigKind', 'Writable',
                     'RequiresReady', 'Readable', 'ReadLevel', 'WriteLevel', 'ModelScoped')
            while True:
                assert request('QUERY_CONFIG', IntValue=index, DurationMs=model)[1]
                base = 'StationA.HmiResponse.ConfigPage'
                count = read(base + '.EntryCount'); pages = read(base + '.PageCount')
                paths = [base + '.Entries[%d].%s' % (slot, field) for slot in range(1, count + 1) for field in names]
                replies = api.bulk([('PlcProgram.Read', {'var': leaf_var(p.split('.'))}) for p in paths])
                assert not any(error for value, error in replies)
                values = [value for value, error in replies]
                entries += [dict(zip(names, values[i:i + len(names)])) for i in range(0, len(values), len(names))]
                if index + 1 >= pages: return entries
                index += 1

        def corrupt(scope, key, model, value, schema=4):
            fields = dict(CorruptScope=scope, CorruptKey=key, CorruptModel=model,
                          CorruptText=value, CorruptSchema=schema, CorruptPulse=True)
            write({'GDB_ConfigTest.' + k: v for k, v in fields.items()})
            wait(lambda: not read('GDB_ConfigTest.CorruptPulse'), 'corruption consumed')
            check('retained test record exists', read('GDB_ConfigTest.CorruptSlot') > 0, True)

        def restart(power=False):
            nonlocal api
            api.conn.close()
            if power:
                result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(HERE / 'cycle_simulator.ps1')], capture_output=True)
                emit({'event': 'power-cycle', 'output': result.stdout.decode('utf-8-sig'), 'exit_code': result.returncode})
                assert result.returncode == 0
            else:
                for action in ('halt', 'run'):
                    emit({'event': 'mode-guard', 'action': action, 'status': UNIT.guard()})
                    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(HERE.parents[1] / 'Spikes/S12_TypeMap/simulator.ps1'), '-Action', action], capture_output=True)
                    emit({'event': 'mode-result', 'output': result.stdout.decode('utf-8-sig'), 'exit_code': result.returncode})
                    assert result.returncode == 0
            api = WebApi('169.254.212.49', pin, False); api.login('fraktal')

        try:
            api.login('fraktal'); emit({'event': 'connection', 'pin': api.fingerprint, 'status': UNIT.guard()})
            check('model config schema', read('StationA.ParCfg.SchemaVersion'), 4)
            check('station config schema', read('StationA.StationCfg.SchemaVersion'), 1)
            check('initial model identity', read('StationA.ModelId.ModelCode'), 'MODEL_A')
            check('model catalog count', read('StationA.AvailableModelCount'), 2)
            check('local retain window derives from Core', read('StationA.ConfigPersist.WindowMs'), catalog.defaults['CONFIG_PERSIST_WINDOW_MS'])
            check('no named-set store advertised', read('StationA.ConfigPersist.StorePresent'), False)
            check('no unacknowledged restore loss initially', read('StationA.ConfigPersist.RestoreLost') and not read('StationA.ConfigPersist.RestoreAcknowledged'), False)
            check('initial model config', read('StationA.ParCfg.Preset'), 10)
            check('initial station config', read('StationA.StationCfg.SiteLabel'), 'bench')
            check('unregistered write denied', edit('StationA', 'SchemaVersion', '8'), False)
            check('per-value minimum denies anonymous', edit('StationA', 'preset', '90'), False)
            login()
            entries = query(); editable = [e for e in entries if e['WriteKey']]
            emit({'event': 'manifest', 'entries': len(entries), 'editable': editable})
            check('one declaration per scoped key', len({(e['Scope'], e['WriteKey']) for e in editable}) == len(editable), True)
            root_preset = next(e for e in editable if e['Scope'] == 'StationA' and e['WriteKey'] == 'preset')
            leaf_preset = next(e for e in editable if e['Scope'] == 'StationA.Cell.Gate' and e['WriteKey'] == 'preset')
            check('root model config is model scoped', root_preset['ModelScoped'], True)
            check('child model config follows active model', leaf_preset['ModelScoped'], False)
            check('revision derives from write definition', root_preset['WriteRevision'], 2)
            check('effective minimum access published', root_preset['WriteLevel'], 1)
            check('live model config requires readiness', root_preset['RequiresReady'], True)
            revision = read('StationA.ConfigRev')
            check('registered model config write accepted', edit('StationA', 'preset', '99'), True)
            check('own active value updated', read('StationA.ParCfg.Preset'), 99)
            check('config revision changes', read('StationA.ConfigRev') != revision, True)
            check('peer config isolated', read('StationB.ParCfg.Preset'), 10)
            check('child config not overwritten', read('StationA.Cell.Gate.ParCfg.Preset'), 10)
            check('stale definition revision denied', edit('StationA', 'preset', '55', revision=1), False)
            for text in ('12.5', '12tail', '++12', '-', '4294967296', 'NaN', '-1', '1001'):
                check('invalid integer/range denied ' + text, edit('StationA', 'preset', text), False)
            check('rejections preserve active value', read('StationA.ParCfg.Preset'), 99)
            check('foreign root denied', edit('StationB', 'preset', '33'), False)
            check('prefix alias denied', edit('StationAOther', 'preset', '33'), False)
            check('unknown model index denied', edit('StationA', 'preset', '33', model=3), False)
            check('inactive child write denied', edit('StationA.Cell.Gate', 'preset', '33', model=2), False)
            check('station config rejects model index', edit('StationA', 'siteLabel', 'wrong', revision=1, model=2), False)
            check('Boolean station config accepted', edit('StationA', 'enabled', 'false', revision=1), True)
            check('Boolean stored with native type', read('StationA.StationCfg.Enabled'), False)
            text80 = 'retained-' + 'x' * 71
            check('full width station config accepted', edit('StationA', 'siteLabel', text80, revision=1), True)
            check('full width text preserved', read('StationA.StationCfg.SiteLabel'), text80)
            check('oversize text denied', edit('StationA', 'siteLabel', text80 + 'x', revision=1), False)
            # The current JSON/simple Web API path rejects escaped Unicode before
            # mailbox commit. Record that transport scope instead of attributing
            # the refusal to a PLC handler the value never reached.
            before_ack = read('StationA.HmiResponse.AckSequence')
            emit({'event': 'mutation-guard', 'status': UNIT.guard(), 'targets': ['StationA.HmiRequest.TextValue']})
            replies = api.bulk([('PlcProgram.Write', {'var': leaf_var(['StationA', 'HmiRequest', 'TextValue']), 'value': '\u4e2d'})])
            check('escaped Unicode refused by simple transport', replies[0][1]['code'], -32602)
            check('transport rejection does not commit mailbox', read('StationA.HmiResponse.AckSequence'), before_ack)
            check('text rejection preserves value', read('StationA.StationCfg.SiteLabel'), text80)
            check('inactive root model config edit accepted', edit('StationA', 'preset', '17', model=2), True)
            check('inactive edit preserves active model config', read('StationA.ParCfg.Preset'), 99)
            inactive = query(2)
            check('inactive query is root model config only', all(e['Scope'] == 'StationA' and e['ConfigKind'] == 0 and e['ModelScoped'] for e in inactive), True)
            check('inactive query returns stored value', int(next(e['ValueText'] for e in inactive if e['WriteKey'] == 'preset')), 17)
            check('inactive model config needs no readiness', all(not e['RequiresReady'] for e in inactive), True)
            check('model release query accepted', request('RELEASE_ACTION', IntValue=catalog.enums['E_GatedAction']['CHANGEOVER'])[1], True)
            check('READY model release allowed', read('StationA.HmiResponse.Report.Released'), True)
            check('AUTO mode accepted', request('SET_MODE', IntValue=modes['AUTO'])[1], True)
            wait(lambda: read('StationA.ModeActivePublished') == modes['AUTO'], 'AUTO mode')
            check('run starts for readiness check', request('START')[1], True)
            wait(lambda: read('StationA.RunningPublished'), 'BUSY')
            check('active config write refused while BUSY', edit('StationA', 'preset', '44'), False)
            check('active catalog index cannot bypass readiness', edit('StationA', 'preset', '44', model=1), False)
            check('inactive model edit remains allowed while BUSY', edit('StationA', 'preset', '17', model=2), True)
            check('model release query stays pure while BUSY', request('RELEASE_ACTION', IntValue=catalog.enums['E_GatedAction']['CHANGEOVER'])[1], True)
            check('BUSY model release withheld', read('StationA.HmiResponse.Report.Released'), False)
            check('BUSY model change refused', request('SET_MODEL', TextValue='MODEL_B')[1], False)
            check('reset cancels test run', request('OPERATOR_RESET')[1], True)
            wait(lambda: read('StationA.Status.State') == 0 and not read('StationA.RunningPublished'), 'run reset')
            check('MANUAL restored', request('SET_MODE', IntValue=modes['MANUAL'])[1], True)
            wait(lambda: read('StationA.ModeActivePublished') == modes['MANUAL'], 'MANUAL mode')
            check('model change accepted', request('SET_MODEL', TextValue='MODEL_B')[1], True)
            check('model identity publishes after commit', read('StationA.ModelId.ModelCode'), 'MODEL_B')
            check('model config resolved from provider', read('StationA.ParCfg.Preset'), 17)
            check('station config excluded from model change', read('StationA.StationCfg.SiteLabel'), text80)
            check('peer model remains independent', read('StationB.ModelId.ModelCode'), 'MODEL_A')
            check('change back accepted', request('SET_MODEL', TextValue='MODEL_A')[1], True)
            check('active edit was saved to its model', read('StationA.ParCfg.Preset'), 99)
            # A late child rejection must leave every earlier staged field untouched.
            corrupt('StationA.Satellite.Inner.Cell.Gate', 'preset', 'MODEL_B', '99999')
            check('invalid child recipe refused', request('SET_MODEL', TextValue='MODEL_B')[1], False)
            check('failed prepare leaves root identity', read('StationA.ModelId.ModelCode'), 'MODEL_A')
            check('failed prepare leaves root config', read('StationA.ParCfg.Preset'), 99)
            check('failed prepare leaves earlier child config', read('StationA.Cell.Gate.ParCfg.Preset'), 10)
            check('failed prepare names offending owner', read('StationA.ConfigPersist.LastRejectScope'), 'StationA.Satellite.Inner.Cell.Gate')
            check('failed prepare names offending key', read('StationA.ConfigPersist.LastRejectKey'), 'preset')
            check('recipe failure has canonical reason', read('StationA.Status.Diagnostic.ReasonCode'), catalog.enums['E_Reason']['RECIPE_INVALID'])
            check('recipe fault points to rejected owner', read('StationA.Status.Diagnostic.SourcePath'), 'StationA.Satellite.Inner.Cell.Gate')
            check('reset after failed recipe accepted', request('OPERATOR_RESET')[1], True)
            wait(lambda: read('StationA.Status.State') == 0 and not read('StationA.AlarmLog.Blocking'), 'recipe reset')
            corrupt('StationA.Satellite.Inner.Cell.Gate', 'preset', 'MODEL_B', '10')
            write({'GDB_ConfigTest.Unavailable': True})
            check('failed store prevents live mutation', edit('StationA', 'preset', '88'), False)
            check('store failure is visible', read('StationA.ConfigPersist.Failed'), True)
            check('store failure preserves active value', read('StationA.ParCfg.Preset'), 99)
            write({'GDB_ConfigTest.Unavailable': False})
            check('retry after store recovery accepted', edit('StationA', 'preset', '99'), True)
            check('store recovered status', read('StationA.ConfigPersist.Failed'), False)
            for path in ('FRK_ConfigStore.Rows[1].Record.ValueText', 'StationA.ConfigStageParCfg.Preset'):
                replies = api.bulk([('PlcProgram.Read', {'var': leaf_var(path.split('.'))})])
                check('private config storage hidden ' + path, replies[0][1]['code'], 200)
            for path in ('StationA.ParCfg.Preset', 'StationA.StationCfg.SiteLabel', 'StationA.ConfigPersist.Failed'):
                emit({'event': 'mutation-guard', 'status': UNIT.guard(), 'targets': [path]})
                replies = api.bulk([('PlcProgram.Write', {'var': leaf_var(path.split('.')), 'value': 3 if path.endswith('Preset') else ('bad' if path.endswith('SiteLabel') else False)})])
                check('direct authority write denied ' + path, replies[0][1]['code'], 205)
            restart()
            check('STOP-RUN restores model config', read('StationA.ParCfg.Preset'), 99)
            check('STOP-RUN restores station config', read('StationA.StationCfg.SiteLabel'), text80)
            check('STOP-RUN restores native Boolean', read('StationA.StationCfg.Enabled'), False)
            check('restart clears application session', read('StationA.Access.CurrentLevel'), 0)
            restart(power=True)
            check('power cycle restores model config', read('StationA.ParCfg.Preset'), 99)
            check('power cycle restores station config', read('StationA.StationCfg.SiteLabel'), text80)
            check('power cycle restores identity', read('StationA.ModelId.ModelCode'), 'MODEL_A')
            check('valid restore has no new loss', read('StationA.ConfigPersist.RestoreLost') and not read('StationA.ConfigPersist.RestoreAcknowledged'), False)
            login()
            corrupt('StationA', 'preset', 'MODEL_A', '12', schema=999)
            restart()
            check('schema-rejected model config defaults', read('StationA.ParCfg.Preset'), 10)
            check('model restore failure preserves station config', read('StationA.StationCfg.SiteLabel'), text80)
            check('model restore failure preserves station Boolean', read('StationA.StationCfg.Enabled'), False)
            check('restore loss is published', read('StationA.ConfigPersist.RestoreLost'), True)
            check('restore loss owner is canonical', read('StationA.ConfigPersist.LostPath'), 'StationA')
            check('default restore policy does not block as an alarm', read('StationA.AlarmLog.Blocking'), False)
            check('anonymous cannot acknowledge lost config', request('ACK_CONFIG_RESTORE')[1], False)
            login(); check('Engineer-or-higher acknowledges loss', request('ACK_CONFIG_RESTORE')[1], True)
            check('loss acknowledgment published', read('StationA.ConfigPersist.RestoreAcknowledged'), True)
            check('defaults are usable after one acknowledgment', edit('StationA', 'preset', '10'), True)
            check('station config defaults restored for next gate', edit('StationA', 'siteLabel', 'bench', revision=1), True)
            check('station Boolean defaults restored for next gate', edit('StationA', 'enabled', 'true', revision=1), True)
            check('logout consumed', request('LOGOUT')[1], True)
            check('final session cleared', read('StationA.Access.CurrentLevel'), 0)
            check('final secret cleared', read('StationA.HmiRequest.Secret'), '')
            complete = True
        finally:
            api.conn.close()
            if not complete: checks.append(('probe completed', False))
            emit({'event': 'summary', 'checks': len(checks), 'failures': sum(not ok for _, ok in checks), 'completed': complete})
            suite = ET.Element('testsuite', name='Fraktal.TIA.Config', tests=str(len(checks)), failures=str(sum(not ok for _, ok in checks)))
            for label, ok in checks:
                case = ET.SubElement(suite, 'testcase', name=label)
                if not ok: ET.SubElement(case, 'failure', message=label)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'), encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    probe(Path(sys.argv[1]))
