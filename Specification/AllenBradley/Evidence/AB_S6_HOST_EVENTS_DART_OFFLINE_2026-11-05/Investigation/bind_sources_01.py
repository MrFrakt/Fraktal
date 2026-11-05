"""Bind this checkpoint's sources by SHA-256 and check each keeps its line endings.

A file tracked at HEAD keeps HEAD's convention; a new file is LF. The two test
fixtures are the sealed session 03 capture's bytes instead (CRLF included), so
each must equal its entry in that evidence's manifest. Exits 1 on any defect.
"""
from pathlib import Path
import hashlib, json, subprocess, sys

R = Path('C:/Users/SoftIndVM/Fraktal')
H = 'FraktalCore/HMI/'
FILES = [H + n for n in (
    'packages/fraktal_opcua_client/lib/src/cip_host_service.dart',
    'packages/fraktal_opcua_client/lib/src/cip_publication.dart',
    'gateway/lib/src/host_adapter/host_events.dart', 'gateway/lib/src/host_adapter/python_json.dart',
    'gateway/lib/src/host_adapter/set_documents.dart', 'gateway/lib/host_adapter.dart',
    'gateway/bin/fraktal_host_adapter.dart', 'gateway/test/host_events_test.dart',
    'gateway/DEPLOYMENT.md', 'gateway/deploy/windows/host_adapter.args.example',
    'test/cip_v611_capture_test.dart')] + ['FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_host_bench_server.py']
SEALED = 'Specification/AllenBradley/Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04/artifact_manifest.json'
FIXTURES = {H + 'gateway/test/fixtures/host_events_session03_canonical.json.gz': 'Session/capture_canonical.json.gz',
            H + 'gateway/test/fixtures/host_events_session03_legacy.json': 'Session/capture_legacy.json'}


def convention(data):
    crlf, lf = data.count(b'\r\n'), data.count(b'\n')
    return 'CRLF' if crlf and crlf == lf else 'LF' if not crlf else 'MIXED'


rows, defects = [], []
for name in FILES:
    data = (R / name).read_bytes()
    at_head = subprocess.run(['git', 'show', 'HEAD:' + name], cwd=R, capture_output=True)
    expected = convention(at_head.stdout) if at_head.returncode == 0 else 'LF'
    actual = convention(data)
    if actual != expected or b'\r' in data.replace(b'\r\n', b''):
        defects.append(name)
    rows.append(dict(file=name, sha256=hashlib.sha256(data).hexdigest().upper(), lineEndings=actual,
                     expected=expected, trackedAtHead=at_head.returncode == 0))
sealed = json.loads((R / SEALED).read_bytes())['files']
for name, entry in FIXTURES.items():
    digest = hashlib.sha256((R / name).read_bytes()).hexdigest().upper()
    if digest != sealed[entry]:
        defects.append(name)
    rows.append(dict(file=name, sha256=digest, sealedAs=entry, sealedSha256=sealed[entry]))
with Path(sys.argv[1]).open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(dict(files=rows, defects=defects), stream, indent=2)
print(json.dumps(dict(files=len(rows), defects=defects)))
raise SystemExit(1 if defects else 0)
