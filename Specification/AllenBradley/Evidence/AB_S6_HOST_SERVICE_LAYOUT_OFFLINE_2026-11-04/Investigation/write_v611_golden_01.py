"""Write the cross-language V6.11 manifest golden for the Dart decoder test.

The physical record is the V6.10 owner fixture of the S4b owner demo, plus
its host-service rows and the ring's owner-read row, rehashed exactly as the
Python table test does. Python normalizes it; the Dart test must accept the
result unchanged and agree on its content hash. No native ABI claim.
"""
import json
from pathlib import Path
import sys

TOOLS = Path(sys.argv[1])
sys.path.insert(0, str(TOOLS))
import fraktal_ab_canonical_manifest as wire  # noqa: E402
from test_fraktal_ab_host_service_binding import ManifestTable  # noqa: E402

ManifestTable.setUpClass()
normalized = wire.normalize(ManifestTable().record())
output = Path(sys.argv[2])
with output.open('x', encoding='utf-8', newline='\n') as f:
    json.dump(dict(schema='fraktal.ab.host-service-manifest-fixture', schemaVersion=1, nativeCapture=False,
                   nativeAcceptanceClaim=False, source='fraktal_ab_genealogy_s4b_owner_demo V6.10 owner fixture',
                   normalized=normalized), f, indent=1, sort_keys=True, ensure_ascii=True)
    f.write('\n')
print(json.dumps(dict(output=str(output), contentHash=normalized['contentHash'],
                      hostRows=len(normalized['hostServiceBindings']),
                      ownerRows=len(normalized['ownerReadBindings']))))
