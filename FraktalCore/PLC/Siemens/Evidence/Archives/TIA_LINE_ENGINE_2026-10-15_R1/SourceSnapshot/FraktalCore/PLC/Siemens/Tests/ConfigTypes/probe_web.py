"""Native typed transactions, atomic sets and connection-scoped current exports."""
from decimal import Decimal, localcontext
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'tools'))
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_target_guard import guard
from tia_webapi import WebApi


def real_reference(text):
    """Independent nearest/even binary32 oracle, avoiding double rounding."""
    source = Decimal(text)
    negative = source < 0
    source = abs(source)
    bits = struct.unpack('I', struct.pack('f', float(source)))[0]
    with localcontext() as context:
        context.prec = 200
        candidates = [(struct.unpack('f', struct.pack('I', b))[0], b)
                      for b in (max(0, bits-1), bits, bits+1)]
        value, _ = min(candidates, key=lambda item: (abs(source-Decimal.from_float(item[0])), item[1] & 1))
    return -value if negative else value


def probe(out):
    checks, complete = [], False
    pin = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    api = WebApi('169.254.212.49', pin, False)
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row)+'\n'); stream.flush()

        def check(label, actual, expected=True):
            passed = type(actual) is type(expected) and actual == expected
            checks.append((label, passed))
            emit(dict(event='check', label=label, actual=actual, expected=expected, passed=passed))
            assert passed, label

        def until(predicate, label, seconds=60):
            deadline = time.monotonic()+seconds
            while time.monotonic() < deadline:
                if predicate(): return
                time.sleep(.05)
            raise AssertionError(label)

        def ready():
            until(lambda: not box.read('FRK_PersistStatus.Restoring'), 'restore barrier')
            until(lambda: all(not box.read(r+'.ConfigPersist.Pending') and not box.read(r+'.ConfigPersist.Failed')
                              for r in ('StationA', 'StationB')), 'verified document writes')

        def login(root='StationA'):
            check('login accepted '+root, box.request('LOGIN', root, User='admin', Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN']))
            until(lambda: not box.read(root+'.Access.LoginBusy'), 'authentication')
            check('admin authenticated '+root, box.read(root+'.Access.CurrentLevel'), 4)

        def edit(key, text, root='StationA', model=0, revision=1):
            return box.request('WRITE_CONFIG', root, TargetPath=root, NameValue=key, TextValue=text, IntValue=revision, DurationMs=model)

        pages = {}
        def config_entry(key):
            page = pages.get(key, 0)
            while True:
                assert box.request('QUERY_CONFIG', IntValue=page)
                base = 'StationA.HmiResponse.ConfigPage'
                for slot in range(1, box.read(base+'.EntryCount')+1):
                    entry = base+'.Entries[%d]'%slot
                    if box.read(entry+'.Scope') == 'StationA' and box.read(entry+'.WriteKey') == key:
                        pages[key] = page
                        return dict(value=box.read(entry+'.ValueText'), domain=box.read(entry+'.EnumDomain'))
                page += 1
                assert page < box.read(base+'.PageCount'), 'capability missing '+key

        def listing():
            assert box.request('LIST_CONFIG_SETS')
            return [box.read('StationA.ConfigSets[%d].SetName'%i) for i in range(1, box.read('StationA.ConfigSetCount')+1)]

        def header(token='0123456789abcdef0123456789abcdef', kind=1, model=0, name='current'):
            return box.request('EXPORT_CURRENT_CONFIG', TextValue=name, NameValue=token, IntValue=kind, DurationMs=model)

        def export(kind=1, model=0, name='current'):
            token = '0123456789abcdef0123456789abcdef'
            assert header(token, kind, model, name)
            count = box.read('StationA.ConfigSetDocumentLines')
            lines = [box.read('StationA.ConfigSetDocument')]
            for ordinal in range(1, count+1):
                assert box.request('EXPORT_CONFIG_SET', TextValue=name, NameValue=token, IntValue=ordinal)
                assert box.read('StationA.ConfigSetDocumentLine') == ordinal
                lines.append(box.read('StationA.ConfigSetDocument'))
            document = [json.loads(line) for line in lines]
            emit(dict(event='document', document=document))
            return document

        def importing(document):
            for ordinal, row in enumerate(document):
                line = json.dumps(row, separators=(',', ':'))
                pieces = [line[i:i+255] for i in range(0, len(line), 255)]
                for index, piece in enumerate(pieces):
                    final = index == len(pieces)-1
                    if not box.request('IMPORT_CONFIG_SET', TextValue=piece, IntValue=0 if final else 1,
                                       BoolValue=final and ordinal == len(document)-1): return False
            return True

        try:
            api.login('fraktal'); emit(dict(event='connection', status=guard(), pin=api.fingerprint))
            box = Mailbox(api, guard, emit)
            ready(); login(); login('StationB')
            for root in ('StationA', 'StationB'):
                check('config restore acknowledged '+root, box.request('ACK_CONFIG_RESTORE', root))
            for name in listing(): assert box.request('DELETE_CONFIG_SET', TextValue=name)
            # Scalar/enum/array edits use only registered, readonly owner fields.
            for key, text, member, expected in [
                ('ratio', '-1.2345e2', 'Ratio', -123.45), ('gain', '+2.5E-1', 'Gain', .25),
                ('grade', '2', 'Grade', 2), ('offset.-1', '-32768', 'Offsets[-1]', -32768),
                ('offset.0', '17', 'Offsets[0]', 17), ('offset.1', '32767', 'Offsets[1]', 32767),
                ('small', '255', 'Small', 255),
            ]:
                check('typed edit '+key, edit(key, text))
                value = box.read('StationA.StationCfg.'+member)
                check('typed value '+key, math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12))
            for key, texts in {
                'ratio': ['', '.', '+', '1e', '1e+', '1.2.3', '1e2junk', 'NaN', 'INF', ' 1', '1 ', '0x10', '1e309', '1e-400', '1e999999', '1000001'],
                'gain': ['1e39', '1e-50', '1001'], 'grade': ['7', '-1', '1.5'],
                'small': ['-1', '256', '1.0'], 'offset.0': ['32768', '-32769', '2.2'],
            }.items():
                for text in texts: check('malformed/out-of-range '+key+' '+text, edit(key, text), False)
            check('rejected number preserves value', math.isclose(box.read('StationA.StationCfg.Ratio'), -123.45))
            check('array lower preserved', box.read('StationA.StationCfg.Offsets[-1]'), -32768)
            check('peer config unchanged', box.read('StationB.StationCfg.Ratio'), 1.25)
            check('unknown array capability refused', edit('offset.2', '1'), False)
            check('stale capability revision refused', edit('ratio', '1', revision=2), False)
            # Native formatting must preserve every IEEE bit, including values
            # that the default Siemens string conversion rounds to 14 digits.
            for key, member, text in [
                ('ratio', 'Ratio', '1.2345678901234567'),
                ('ratio', 'Ratio', '-999999.9999999999'),
                ('ratio', 'Ratio', '1.0000000000000002e-100'),
                ('gain', 'Gain', '0.10000000149011612'),
                ('gain', 'Gain', '1.1754943508222875e-38'),
                ('gain', 'Gain', '1.000000059604644775390625'),
                ('gain', 'Gain', '1.000000059604644775390626'),
                ('gain', 'Gain', '0.9999999701976776123046875'),
            ]:
                check('precision edit '+text, edit(key, text))
                expected = float(text)
                if key == 'gain': expected = real_reference(text)
                actual = box.read('StationA.StationCfg.'+member)
                # The measured REAL RPC leaf has only seven significant
                # decimal digits. The readonly typed text below proves its
                # exact stored bits, independently of this display precision.
                if key == 'gain':
                    emit(dict(event='real-webapi-value', input=text, wire_value=actual, exact_expected=expected))
                    check('REAL Web API display value '+text, math.isclose(actual, expected, rel_tol=5e-7, abs_tol=0.0))
                else:
                    check('native IEEE rounding '+text, actual, expected)
                check('lossless manifest text '+text, float(config_entry(key)['value']), expected)
                if text in ('-999999.9999999999', '1.000000059604644775390626'):
                    precision_document = export(name='precision')
                    actual = next(r['value'] for r in precision_document[1:] if r['scope']=='StationA' and r['key']==key)
                    check('lossless decimal snapshot '+text, float(actual), expected)
            check('restore ratio before restart', edit('ratio', '-123.45'))
            check('restore gain before restart', edit('gain', '.25'))
            grade = config_entry('grade')
            check('enum capability discovered', bool(grade['domain']))
            check('enum current value is a declared choice', grade['value'] in grade['domain'].split('|'))
            # A complete immutable document needs no saved slot.
            check('initial saved-set list empty', listing(), [])
            document = export()
            values = {r['key']: r['value'] for r in document[1:] if r['scope'] == 'StationA'}
            check('snapshot contains all explicit array elements', all('offset.%d'%i in values for i in range(-1, 2)))
            check('snapshot native LREAL value', math.isclose(float(values['ratio']), -123.45))
            check('snapshot has no saved slot', listing(), [])
            for token in ('', '0'*31, 'g'*32, '0'*33): check('invalid token '+str(len(token)), header(token), False)
            check('line profile absent', header(kind=2), False)
            check('station model index refused', header(model=1), False)
            check('unknown model index refused', header(kind=0, model=3), False)
            for case in ('foreign', 'order', 'operation', 'logout', 'missing'):
                assert header()
                if case == 'operation': assert box.request('QUERY_CONFIG')
                if case == 'logout': assert box.request('LOGOUT'); login()
                check('cursor invalidated '+case, box.request('EXPORT_CONFIG_SET', TextValue='current',
                      NameValue=('f'*32 if case == 'foreign' else '' if case == 'missing' else '0123456789abcdef0123456789abcdef'),
                      IntValue=2 if case == 'order' else 1), False)
                check('cursor cannot resume '+case, box.request('EXPORT_CONFIG_SET', TextValue='current',
                      NameValue='0123456789abcdef0123456789abcdef', IntValue=1), False)
            # Full store does not prevent current-value export; import is atomic.
            for i in range(4): check('fill slot '+str(i), box.request('SAVE_CONFIG_SET', TextValue='slot'+str(i), IntValue=1))
            check('full saved-set store', len(listing()), 4)
            document = export(name='full-store-export')
            check('full store export complete', len(document), document[0]['records']+1)
            check('export did not replace a saved slot', listing(), ['slot0', 'slot1', 'slot2', 'slot3'])
            document[0]['set'] = 'slot0'
            next(r for r in document[1:] if r['key'] == 'ratio')['value'] = 'NaN'
            check('nonfinite imported document refused', importing(document), False)
            check('failed import leaves live config intact', math.isclose(box.read('StationA.StationCfg.Ratio'), -123.45))
            # Provider model lookups and changeover use the same typed paths.
            check('edit inactive model', edit('preset', '83', model=2, revision=2))
            model = export(kind=0, model=2, name='inactive-model')
            check('inactive model snapshot identity', model[0]['model'], 'MODEL_B')
            check('inactive model snapshot value', next(r['value'] for r in model[1:] if r['scope']=='StationA' and r['key']=='preset'), '83')
            check('inactive export does not change active identity', box.read('StationA.Model.ModelCode'), 'MODEL_A')
            ready()
            api.conn.close()
            for action in ('halt', 'run'):
                emit(dict(event='restart-guard', action=action, status=guard()))
                result = subprocess.run(['powershell.exe', '-NoProfile', '-File', str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'), '-Action', action], capture_output=True)
                emit(dict(event='restart-result', action=action, exit_code=result.returncode, output=result.stdout.decode('utf-8-sig')))
                assert result.returncode == 0
            api = WebApi('169.254.212.49', pin, False); api.login('fraktal'); box = Mailbox(api, guard, emit)
            ready()
            check('restart withdrew session', box.read('StationA.Access.CurrentLevel'), 0)
            check('LOAD_DB restores LREAL', math.isclose(box.read('StationA.StationCfg.Ratio'), -123.45))
            check('LOAD_DB restores REAL', box.read('StationA.StationCfg.Gain'), .25)
            check('LOAD_DB restores array element', box.read('StationA.StationCfg.Offsets[-1]'), -32768)
            check('LOAD_DB restores enum', box.read('StationA.StationCfg.Grade'), 2)
            login()
            check('LOAD_DB restores all saved sets', len(listing()), 4)
            # End with test values/defaults normalized and durable, no session.
            for key, value in {'ratio':'1.25', 'gain':'2.5', 'grade':'1', 'offset.-1':'0', 'offset.0':'0', 'offset.1':'0', 'small':'7'}.items():
                check('normalize '+key, edit(key, value))
            check('normalize inactive model', edit('preset', '10', model=2, revision=2))
            for name in listing(): assert box.request('DELETE_CONFIG_SET', TextValue=name)
            ready()
            for root in ('StationA', 'StationB'): check('final logout '+root, box.request('LOGOUT', root))
            check('simulator remains RUN', guard()['state'], 'Run')
            complete = True
        finally:
            api.conn.close()
            suite = ET.Element('testsuite', name='TIA.ConfigTypes', tests=str(len(checks)+(not complete)), failures=str(sum(not p for _, p in checks)+(not complete)))
            for label, passed in checks:
                case = ET.SubElement(suite, 'testcase', name=label)
                if not passed: ET.SubElement(case, 'failure', message='native assertion failed')
            if not complete: ET.SubElement(ET.SubElement(suite, 'testcase', name='completed'), 'failure', message='acceptance interrupted')
            out.with_suffix('.xml').write_bytes(ET.tostring(suite, encoding='utf-8', xml_declaration=True))
            emit(dict(event='summary', assertions=len(checks), completed=complete, failures=sum(not p for _, p in checks)))


if __name__ == '__main__':
    probe(Path(sys.argv[1]))
