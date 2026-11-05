"""Bind this checkpoint's sources by SHA-256 and check each keeps its line endings.

A file tracked at HEAD must keep HEAD's convention (all-LF, all-CRLF or mixed);
a new file must be LF. Writes the binding to the path given; exits 1 on any
defect. Deleted files are listed with their HEAD hash.
"""
from pathlib import Path
import hashlib, json, subprocess, sys

R = Path('C:/Users/SoftIndVM/Fraktal')
TOOLS = 'FraktalCore/PLC/Allen-Bradley/tools/'
HMI = 'FraktalCore/HMI/'
SPEC = 'Specification/AllenBradley/'
FILES = [HMI + n for n in (
    'packages/fraktal_opcua_client/lib/src/cip_host_service.dart',
    'packages/fraktal_opcua_client/lib/cip_host_service.dart',
    'gateway/lib/host_adapter.dart', 'gateway/lib/src/host_adapter/set_documents.dart',
    'gateway/lib/src/host_adapter/live_medium.dart', 'gateway/lib/src/host_adapter/root_service.dart',
    'gateway/bin/fraktal_host_adapter.dart', 'gateway/test/host_adapter_bench_test.dart',
    'gateway/windows_tray/fraktal_gateway_tray.cpp', 'gateway/tool/build_gateway.dart',
    'gateway/tool/build_windows_installer.dart', 'gateway/deploy/windows/install_gateway.ps1',
    'gateway/deploy/windows/host_adapter.args.example', 'gateway/DEPLOYMENT.md')] + [
    TOOLS + 'fraktal_ab_host_bench_server.py', TOOLS + 'test_fraktal_ab_host_service_binding.py',
    SPEC + 'AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md',
    SPEC + 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    SPEC + 'AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_2026-11-02.md']
RETIRED = [TOOLS + n for n in ('fraktal_ab_host_adapter.py', 'fraktal_ab_host_cip.py',
                               'test_fraktal_ab_host_adapter.py', 'test_fraktal_ab_host_cip.py')]


def convention(data):
    crlf, lf = data.count(b'\r\n'), data.count(b'\n')
    return 'CRLF' if crlf and crlf == lf else 'LF' if not crlf else 'MIXED'


def head(name):
    return subprocess.run(['git', 'show', 'HEAD:' + name], cwd=R, capture_output=True)


rows, defects, retired = [], [], []
for name in FILES:
    data = (R / name).read_bytes()
    at_head = head(name)
    expected = convention(at_head.stdout) if at_head.returncode == 0 else 'LF'
    actual = convention(data)
    if actual != expected or b'\r' in data.replace(b'\r\n', b''):
        defects.append(name)
    rows.append(dict(file=name, sha256=hashlib.sha256(data).hexdigest().upper(), lineEndings=actual,
                     expected=expected, trackedAtHead=at_head.returncode == 0))
for name in RETIRED:
    if (R / name).exists():
        defects.append(name)
    at_head = head(name)
    retired.append(dict(file=name, headSha256=hashlib.sha256(at_head.stdout).hexdigest().upper()
                        if at_head.returncode == 0 else None))
with Path(sys.argv[1]).open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(dict(files=rows, retired=retired, defects=defects), stream, indent=2)
print(json.dumps(dict(files=len(rows), retired=len(retired), defects=defects)))
raise SystemExit(1 if defects else 0)
