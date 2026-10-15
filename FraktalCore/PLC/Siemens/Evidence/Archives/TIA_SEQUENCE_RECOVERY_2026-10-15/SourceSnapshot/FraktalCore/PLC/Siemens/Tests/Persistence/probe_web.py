"""Native LOAD_DB consumer acceptance on the guarded owner simulator."""
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
from tia_target_guard import guard
from tia_mailbox import Mailbox
from fraktal_tia_binding import Catalog


def probe(out):
    checks = []
    complete = False
    pin = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin'
    api = WebApi('169.254.212.49', pin, False)
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row) + '\n'); stream.flush()

        def check(label, actual, expected=True):
            passed = type(actual) is type(expected) and actual == expected
            checks.append((label, passed))
            emit(dict(event='check', label=label, actual=actual, expected=expected, passed=passed))
            assert passed, label

        def until(predicate, label, seconds=60):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                if predicate(): return
                time.sleep(.1)
            raise AssertionError(label)

        def writes(values):
            emit(dict(event='fixture-mutation-guard', targets=list(values), status=guard()))
            replies = api.bulk([('PlcProgram.Write', dict(var=leaf_var(p.split('.')), value=v)) for p, v in values.items()])
            assert not any(error for _, error in replies), 'fixture write refused'

        def read(path): return box.read(path)
        def request(kind, root='StationA', **fields): return box.request(kind, root, **fields)

        def ready(durable=True):
            until(lambda: not read('FRK_PersistStatus.Restoring'), 'restore barrier')
            if durable:
                until(lambda: all(not read(r+'.ConfigPersist.Pending') and not read(r+'.ConfigPersist.Failed') for r in ('StationA', 'StationB')), 'verified durability')
            check('storage restore complete', read('FRK_PersistStatus.Restoring'), False)
            for root in ('StationA', 'StationB'):
                check('root identity '+root, read(root+'.Status.Name'), root)

        def login(root='StationA', user='admin', level=4, failed=False):
            check('login request '+root+' '+user, request('LOGIN', root, User=user, Secret=os.environ['FRAKTAL_TIA_'+user.upper()+'_PIN']))
            until(lambda: not read(root+'.Access.LoginBusy'), 'login result', 8)
            check('login failure '+root+' '+user, read(root+'.Access.LoginFailed'), failed)
            check('login level '+root+' '+user, read(root+'.Access.CurrentLevel'), level)
            check('login secret cleared '+root, read(root+'.HmiRequest.Secret'), '')

        def edit(root, key, text, revision=1, model=0):
            return request('WRITE_CONFIG', root, TargetPath=root, NameValue=key, TextValue=text, IntValue=revision, DurationMs=model)

        def restart(power=False, wait=True):
            nonlocal api, box
            api.conn.close()
            scripts = [(HERE.parent/'Config/cycle_simulator.ps1', None)] if power else [(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1', action) for action in ('halt', 'run')]
            for script, action in scripts:
                emit(dict(event='restart-guard', power=power, action=action, status=guard()))
                cmd = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)]
                if action: cmd += ['-Action', action]
                result = subprocess.run(cmd, capture_output=True)
                emit(dict(event='restart-result', exit_code=result.returncode, output=result.stdout.decode('utf-8-sig').strip()))
                assert result.returncode == 0
            api = WebApi('169.254.212.49', pin, False); api.login('fraktal')
            box = Mailbox(api, guard, emit)
            if wait: ready(False)
            for root in ('StationA', 'StationB'):
                check('session withdrawn '+root, read(root+'.Access.CurrentLevel'), 0)
                check('run withdrawn '+root, read(root+'.RunningPublished'), False)
                check('command withdrawn '+root, read(root+'.Busy'), False)

        def stimulus(operation, slot=1, bank=1, offset=0, value=0):
            writes({'GDB_PersistenceTest.Slot':slot, 'GDB_PersistenceTest.Bank':bank, 'GDB_PersistenceTest.Offset':offset, 'GDB_PersistenceTest.ByteValue':value})
            writes({'GDB_PersistenceTest.Operation':operation})
            until(lambda: read('GDB_PersistenceTest.Operation') == 0, 'fixture operation', 8)
            check('deliberate fixture mutation applied', read('GDB_PersistenceTest.Applied'))

        def user_repair():
            writes({'GDB_AccessPersistTest.Operation':7})
            until(lambda: read('GDB_AccessPersistTest.Operation') == 0, 'trusted user provisioning', 8)
            check('trusted user repair applied', read('GDB_AccessPersistTest.Applied'))

        def generation(slot): return read('GDB_PersistenceTest.Generation[%d]' % slot)

        try:
            api.login('fraktal'); box = Mailbox(api, guard, emit)
            emit(dict(event='connection', status=guard(), pin=api.fingerprint))
            ready()
            check('selected medium identity', read('FRK_PersistStatus.Medium'), 'LOAD_DB')
            check('consumed document count', read('FRK_PersistStatus.DocumentCount'), 17)
            check('bounded declared write window', read('StationA.ConfigPersist.WindowMs'), 23000)
            for slot in range(1, 18): check('confirmed initial generation '+str(slot), generation(slot) > 0)
            login(); login('StationB')
            check('station config accepted', edit('StationA', 'siteLabel', 'load-db-A'))
            check('peer station config accepted', edit('StationB', 'siteLabel', 'load-db-B'))
            check('active model config accepted', edit('StationA', 'preset', '21', 2))
            check('inactive model config accepted', edit('StationA', 'preset', '29', 2, 2))
            check('named station config saved', request('SAVE_CONFIG_SET', TextValue='medium-station', IntValue=1))
            check('named model config saved', request('SAVE_CONFIG_SET', TextValue='medium-model', IntValue=0))
            check('root access policy accepted', request('SET_ACCESS_LEVEL', IntValue=2, TextValue='3'))
            ready()
            before = generation(1)
            check('unchanged config write accepted', edit('StationA', 'siteLabel', 'load-db-A'))
            time.sleep(1.2)
            check('unchanged value avoids load-memory write', generation(1), before)
            stimulus(3)
            restart()
            check('medium replaces poisoned station cache', read('StationA.StationCfg.SiteLabel'), 'load-db-A')
            check('peer medium replaces poisoned cache', read('StationB.StationCfg.SiteLabel'), 'load-db-B')
            check('active model restored', read('StationA.ParCfg.Preset'), 21)
            check('root policy restored', read('StationA.Access.Policy.Required[2]'), 3)
            check('user table restored without cache checksum', read('GDB_AccessPersistTest.UsersReady'))
            check('station has no unacknowledged loss', read('StationA.ConfigPersist.RestoreLost') and not read('StationA.ConfigPersist.RestoreAcknowledged'), False)
            login()
            check('inactive model selected', request('SET_MODEL', TextValue='MODEL_B'))
            check('inactive model value restored', read('StationA.ParCfg.Preset'), 29)
            check('original model selected', request('SET_MODEL', TextValue='MODEL_A'))
            check('changed station config accepted', edit('StationA', 'siteLabel', 'after-set'))
            check('saved station config loaded', request('LOAD_CONFIG_SET', TextValue='medium-station'))
            check('set payload restored from medium', read('StationA.StationCfg.SiteLabel'), 'load-db-A')
            ready(); restart(True)
            check('power cycle restores station config', read('StationA.StationCfg.SiteLabel'), 'load-db-A')
            check('power cycle restores active model', read('StationA.ParCfg.Preset'), 21)
            login()
            writes({'GDB_PersistenceTest.Unavailable':True})
            before = generation(1)
            check('live config remains editable during write outage', edit('StationA', 'siteLabel', 'after-retry'))
            until(lambda: read('StationA.ConfigPersist.Failed'), 'failed durability announced', 8)
            check('outage leaves pending durability', read('StationA.ConfigPersist.Pending'))
            check('failed write never confirms generation', generation(1), before)
            writes({'GDB_PersistenceTest.Unavailable':False}); ready()
            check('retry confirms newer generation', generation(1) > before)
            restart()
            check('retried live edit survives restart', read('StationA.StationCfg.SiteLabel'), 'after-retry')
            login()
            check('AUTO mode accepted', request('SET_MODE', IntValue=Catalog.read().enums['E_Mode']['AUTO']))
            check('test run accepted', request('START'))
            until(lambda: read('StationA.RunningPublished'), 'test run busy', 8)
            writes({'GDB_PersistenceTest.Unavailable':True})
            restart(wait=False)
            until(lambda: read('FRK_PersistStatus.Failed'), 'boot outage announced', 8)
            check('unreadable boot keeps restore barrier', read('FRK_PersistStatus.Restoring'))
            check('child command withdrawn during restore', read('StationA.Cell.Gate.Busy'), False)
            check('derived device output withdrawn during restore', read('StationA.Cell.Gate.OutImm.Output'), False)
            writes({'GDB_PersistenceTest.Unavailable':False}); ready()
            check('boot retry preserves confirmed document', read('StationA.StationCfg.SiteLabel'), 'after-retry')
            # Damage the newest slot: the confirmed marker forbids a silent older restore.
            current = read('GDB_PersistenceTest.CurrentBank[1]')
            stimulus(1, bank=current)
            restart()
            check('newest document damage announced', read('StationA.ConfigPersist.RestoreLost'))
            check('damaged station uses defaults', read('StationA.StationCfg.SiteLabel'), 'bench')
            check('peer root unaffected by damage', read('StationB.StationCfg.SiteLabel'), 'load-db-B')
            login(user='operator', level=1)
            check('operator cannot acknowledge restore loss', request('ACK_CONFIG_RESTORE'), False)
            login()
            check('engineer-level restore acknowledgement', request('ACK_CONFIG_RESTORE'))
            ready(); restart()
            check('acknowledged fallback durable', read('StationA.StationCfg.SiteLabel'), 'bench')
            check('replacement has no new unacknowledged loss', read('StationA.ConfigPersist.RestoreLost') and not read('StationA.ConfigPersist.RestoreAcknowledged'), False)
            # Both slots invalid, and then a corrupt anchor, require explicit repair.
            for bank in (1, 2): stimulus(1, bank=bank)
            restart(); check('two damaged slots announced', read('StationA.ConfigPersist.RestoreLost'))
            login(); check('both-slot loss acknowledged', request('ACK_CONFIG_RESTORE'))
            ready(); stimulus(2); restart()
            check('corrupt anchor announced', read('StationA.ConfigPersist.RestoreLost'))
            login(); check('anchor loss acknowledged', request('ACK_CONFIG_RESTORE'))
            ready(); restart()
            check('repaired anchor has no new unacknowledged loss', read('StationA.ConfigPersist.RestoreLost') and not read('StationA.ConfigPersist.RestoreAcknowledged'), False)
            # Confidential users fail closed; repair uses the trusted provider seam.
            stimulus(2, slot=17); restart()
            check('user-anchor corruption disables provider', read('GDB_AccessPersistTest.UsersReady'), False)
            login(user='admin', level=0, failed=True)
            user_repair(); ready(); restart()
            login(); check('repaired user document survives restart', read('GDB_AccessPersistTest.UsersReady'))
            ready()
            for bank in (1, 2): stimulus(1, slot=4, bank=bank)
            restart()
            check('damaged policy uses restrictive fallback', read('StationA.Access.Policy.Required[2]'), 4)
            check('policy loss announced', read('StationA.ConfigPersist.RestoreLost'))
            check('policy loss blocks anonymous start', request('START'), False)
            login(); check('policy loss acknowledged by engineer', request('ACK_CONFIG_RESTORE'))
            ready(); restart()
            check('restrictive fallback persists after acknowledgement', read('StationA.Access.Policy.Required[2]'), 4)
            check('acknowledged policy has no new unacknowledged loss', read('StationA.ConfigPersist.RestoreLost') and not read('StationA.ConfigPersist.RestoreAcknowledged'), False)
            login()
            for path in ('FRK_PersistRuntime.Stage', 'FRK_PersistAnchors.RowsA[1].Generation', 'FRK_PersistBuffers.D001Data[0]', 'FRK_PersistImages.D017.Count', 'FRK_Load_D017A.Bytes[0]'):
                replies = api.bulk([('PlcProgram.Read', dict(var=leaf_var(path.split('.'))))])
                check('private persistence symbol '+path, replies[0][1]['code'], 200)
            emit(dict(event='readonly-write-guard', status=guard()))
            replies = api.bulk([('PlcProgram.Write', dict(var=leaf_var(['FRK_PersistStatus', 'Medium']), value='RETAIN'))])
            check('medium metadata readonly', replies[0][1]['code'], 205)
            # Restore only the test bench's intended policy and config.
            for root in ('StationA', 'StationB'):
                login(root)
                check('normalize station config '+root, edit(root, 'siteLabel', 'bench'))
                check('normalize active model '+root, request('SET_MODEL', root, TextValue='MODEL_A'))
                check('normalize active config '+root, edit(root, 'preset', '10', 2))
                check('normalize inactive config '+root, edit(root, 'preset', '10', 2, 2))
                check('normalize MANUAL '+root, request('SET_MODE', root, IntValue=Catalog.read().enums['E_Mode']['MANUAL']))
                levels={2:1,4:1,5:1,8:4,11:3}
                for gate in Catalog.read().enums['E_GatedAction'].values():
                    check('normalize policy '+root+' '+str(gate), request('SET_ACCESS_LEVEL', root, IntValue=gate, TextValue=str(levels.get(gate,0))))
                check('normalize session timeout '+root, request('SET_SESSION_TIMEOUT', root, DurationMs=0))
            for name in ('medium-station', 'medium-model'): check('remove test set '+name, request('DELETE_CONFIG_SET', TextValue=name))
            ready()
            for root in ('StationA', 'StationB'): check('logout '+root, request('LOGOUT', root))
            check('owner left in RUN', guard()['state'], 'Run')
            complete = True
        finally:
            api.conn.close()
            suite = ET.Element('testsuite', name='TIA.LoadDbConsumers', tests=str(len(checks)+(not complete)), failures=str(sum(not ok for _, ok in checks)+(not complete)))
            for label, passed in checks:
                case = ET.SubElement(suite, 'testcase', name=label)
                if not passed: ET.SubElement(case, 'failure', message='native assertion failed')
            if not complete: ET.SubElement(ET.SubElement(suite, 'testcase', name='completed native acceptance'), 'failure', message='acceptance interrupted')
            out.with_suffix('.xml').write_bytes(ET.tostring(suite, encoding='utf-8', xml_declaration=True))
            emit(dict(event='summary', assertions=len(checks), completed=complete, failures=sum(not ok for _, ok in checks)))


if __name__ == '__main__': probe(Path(sys.argv[1]))
