"""Bind this checkpoint's sources: hashes now, and agreement with the gated tools.

Writes create-only Gates/source_bindings_01.json. Fails if any tools module
changed since gate run 01 hashed it before the full suite.
"""
from pathlib import Path
import hashlib, json

I = Path(__file__).resolve().parent
G = I.parent / 'Gates'
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
FILES = [
    'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_host_service_binding.py',
    'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_host_services.py',
    'FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_host_service_binding.py',
    'FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_host_services.py',
    'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_manifest.py',
    'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_reader.py',
    'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_owner_read_bindings.py',
    'FraktalCore/HMI/packages/fraktal_opcua_client/lib/src/cip_manifest.dart',
    'FraktalCore/HMI/test/cip_host_services_manifest_test.dart',
    'FraktalCore/HMI/test/fixtures/cip_host_services_v611.json',
    'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


gated = json.loads((G / 'full_ab_source_bindings_before_01.json').read_text(encoding='utf-8'))['sources']
now = {p.name: digest(p) for p in sorted(T.glob('*.py'))}
result = dict(files={f: digest(R / f) for f in FILES}, toolsUnchangedSinceGates=now == gated,
              toolsModules=len(now))
with (G / 'source_bindings_01.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['toolsUnchangedSinceGates'] else 1)
