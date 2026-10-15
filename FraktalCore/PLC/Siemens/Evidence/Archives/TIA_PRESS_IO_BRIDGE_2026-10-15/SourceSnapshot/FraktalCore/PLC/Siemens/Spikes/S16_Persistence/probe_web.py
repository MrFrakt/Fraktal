"""Guarded native READ_DBL/WRIT_DBL semantics, restart and exclusion gate."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from tia_target_guard import guard
from tia_webapi import WebApi, leaf_var


def probe(out, load_only=False):
    checks = []
    complete = False
    pin = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin'
    api = WebApi('169.254.212.49', pin, False)
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row) + '\n')
            stream.flush()

        def check(name, actual, expected=True):
            ok = type(actual) is type(expected) and actual == expected
            checks.append((name, ok))
            emit(dict(event='check', name=name, actual=actual, expected=expected, passed=ok))
            if not ok:
                raise AssertionError(name)

        def read(name):
            return api.call('PlcProgram.Read', dict(var=leaf_var(name.split('.'))))

        def value(field):
            return read('GDB_LoadMemoryTest.' + field)

        def write(values):
            emit(dict(event='mutation-guard', status=guard(), targets=list(values)))
            replies = api.bulk([('PlcProgram.Write', dict(var=leaf_var(k.split('.')), value=v)) for k, v in values.items()])
            assert not any(error for result, error in replies), replies

        def until(test, name):
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if test():
                    return
                time.sleep(.02)
            raise AssertionError(name)

        def request(kind, seed=0, accepted=True):
            sequence = (value('Sequence') + 1) & 0xffffffff
            write({'GDB_LoadMemoryTest.Kind': kind, 'GDB_LoadMemoryTest.Seed': seed})
            write({'GDB_LoadMemoryTest.Sequence': sequence})
            until(lambda: value('AckSequence') == sequence, 'request completion')
            check('request accepted ' + str(kind), value('Accepted'), accepted)
            check('request no longer busy ' + str(kind), value('Busy'), False)
            check('native completion status ' + str(kind), value('NativeStatus'), 0 if accepted else 65535)
            emit(dict(event='native-duration', kind=kind, seed=seed, calls=value('BusyScans')))

        def payload(seed, name):
            check(name + ' first byte', value('FirstByte'), seed)
            check(name + ' last byte', value('LastByte'), (seed + 63) % 256)
            check(name + ' complete native CRC', value('ReadCrc'), zlib.crc32(bytes((seed + i) % 256 for i in range(64))))

        def restart(power=False):
            nonlocal api
            before = value('StartupCount')
            if power:
                api.conn.close()
            steps = [(HERE.parents[1] / 'Tests/Config/cycle_simulator.ps1', None)] if power else [(HERE.parent / 'S12_TypeMap/simulator.ps1', a) for a in ('halt', 'run')]
            for script, action in steps:
                emit(dict(event='restart-guard', status=guard(), power=power, action=action))
                cmd = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)]
                if action:
                    cmd += ['-Action', action]
                result = subprocess.run(cmd, capture_output=True)
                emit(dict(event='restart-result', exit_code=result.returncode, output=result.stdout.decode('utf-8-sig')))
                assert result.returncode == 0
            if power:
                api = WebApi('169.254.212.49', pin, False)
                api.login('fraktal')
            until(lambda: value('StartupCount') > before, 'startup witness')
            check('restart no job replay', value('Busy'), False)
            for root in ('StationA', 'StationB'):
                check('restart output inactive ' + root, read(root + '.RunningPublished'), False)
                check('restart session inactive ' + root, read(root + '.Access.CurrentLevel'), 0)

        try:
            api.login('fraktal')
            check('qualified target RUN', guard()['state'], 'Run')
            request(1)
            check('virgin bank load byte', value('FirstByte'), 0)
            check('virgin full array', value('ReadCrc'), zlib.crc32(bytes(64)))
            request(2, 17)
            if not load_only:
                check('WRIT_DBL leaves target work memory unchanged', value('BankAWorkByte'), 0)
            request(1)
            payload(17, 'bank A')
            request(5, 128)
            if not load_only:
                check('second WRIT_DBL leaves target work memory unchanged', value('BankBWorkByte'), 0)
            request(6)
            payload(128, 'bank B')
            if not load_only:
                request(3, 255)
                check('current bank A deliberately differs', value('BankAWorkByte'), 255)
                check('current bank B deliberately differs', value('BankBWorkByte'), 255)
            request(4, 0)
            check('read destination deliberately cleared', value('FirstByte'), 0)
            request(1)
            payload(17, 'load differs from current A')
            request(6)
            payload(128, 'load differs from current B')
            request(2, 240)
            request(1)
            payload(240, 'replacement A including byte wrap')
            request(6)
            payload(128, 'replacement isolates B')
            for power in (False, True):
                restart(power)
                request(4, 0)
                request(1)
                payload(240, 'restart A ' + str(power))
                request(4, 0)
                request(6)
                payload(128, 'restart B ' + str(power))
            # Arguments without a new commit sequence are inert.
            before = value('ReadCrc')
            sequence = value('AckSequence')
            write({'GDB_LoadMemoryTest.Kind': 2, 'GDB_LoadMemoryTest.Seed': 99})
            time.sleep(.1)
            check('staged request stays idle', value('Busy'), False)
            check('staged request leaves acknowledgement', value('AckSequence'), sequence)
            check('staged request leaves readback', value('ReadCrc'), before)
            request(99, accepted=False)
            request(1)
            payload(240, 'invalid request cannot overwrite A')
            for block in ('GDB_LoadSource', 'GDB_LoadBankA', 'GDB_LoadBankB', 'GDB_LoadRead'):
                reply = api.bulk([('PlcProgram.Read', dict(var=leaf_var([block, 'Payload[0]'])))])[0]
                check('private buffer refused ' + block, reply[1]['code'], 200)
            emit(dict(event='mutation-guard', status=guard(), targets=['GDB_LoadMemoryTest.ReadCrc']))
            reply = api.bulk([('PlcProgram.Write', dict(var=leaf_var(['GDB_LoadMemoryTest', 'ReadCrc']), value=0))])[0]
            check('readback mirror is readonly', reply[1]['code'], 205)
            complete = True
        finally:
            api.conn.close()
            if not complete:
                checks.append(('probe completed', False))
            emit(dict(event='summary', checks=len(checks), failures=sum(not ok for _, ok in checks), complete=complete))
            suite = ET.Element('testsuite', name='Fraktal.TIA.LoadMemory', tests=str(len(checks)), failures=str(sum(not ok for _, ok in checks)))
            for name, ok in checks:
                case = ET.SubElement(suite, 'testcase', name=name)
                if not ok:
                    ET.SubElement(case, 'failure', message=name)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'), encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    probe(Path(sys.argv[1]), load_only='--load-only' in sys.argv[2:])
