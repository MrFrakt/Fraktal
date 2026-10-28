"""Offline replica of the helper's deploy-canonical file gates, so a refusal is found before approval.

Runtime-only conditions (the backup taken in-session and the live preflight)
are excluded; every file-bound comparison is checked exactly as the C# does,
including upper-case hexadecimal hashes and exact string equality.
"""
from pathlib import Path
import hashlib, json, sys

W = Path(__file__).parent
Hash = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
pin = (W/'canonical.sha256').read_text().strip()
reference = json.loads((W/'baseline_reference.json').read_text())
prior = json.loads((W/'baseline_capacity.json').read_text())
estimate = json.loads((W/'capacity_review.json').read_text())
compare = json.loads((W/'canonical_prepared_compare.json').read_text())
checks = dict(
    baselineCapacityHash=Hash(W/'baseline_capacity.json') == reference['capacitySha256'],
    verifiedFit=estimate['VerifiedFit'] is True, measured=estimate['Measured'] is True,
    provider=estimate['Provider'] in ('OwnerStudio', 'StudioUIAutomation'),
    canonicalBinding=estimate['CanonicalSha256'] == pin, unit=estimate['CapacityUnit'] == 'Blocks',
    arithmetic=0 <= estimate['UsedStandardBlocks'] <= estimate['TotalBlocks'] and estimate['AvailableBlocks'] >= 0
               and estimate['AvailableBlocks'] == estimate['TotalBlocks'] - estimate['UsedStandardBlocks'],
    baselineBinding=estimate['BaselineSha256'] == prior['CanonicalSha256']
                    and estimate['BaselineUsedStandardBlocks'] == prior['UsedStandardBlocks']
                    and estimate['BaselineAvailableBlocks'] == prior['AvailableBlocks']
                    and estimate['BaselineTotalBlocks'] == prior['TotalBlocks'] == estimate['TotalBlocks']
                    and estimate['BaselineUsedStandardBlocks'] >= 0
                    and estimate['BaselineAvailableBlocks'] == estimate['BaselineTotalBlocks'] - estimate['BaselineUsedStandardBlocks'],
    probePin=Hash(W/'s3j_canonical.ACD') == pin,
    preparedCompareEquivalent=compare['Equivalent'] is True)
output = Path(sys.argv[1])
with output.open('x') as out:
    json.dump(dict(passed=all(checks.values()), checks=checks, runtimeOnlyExcluded=['backup.sha256', 'preflight --verify-only']), out, indent=2)
print(json.dumps(dict(passed=all(checks.values()), failed=[k for k, v in checks.items() if not v])))
raise SystemExit(0 if all(checks.values()) else 1)
