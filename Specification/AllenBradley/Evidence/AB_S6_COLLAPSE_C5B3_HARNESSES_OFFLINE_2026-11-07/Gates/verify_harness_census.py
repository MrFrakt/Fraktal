"""Verify zero direct legacy reads and legacy imports in the 6 migrated harnesses."""
import sys
from pathlib import Path
sys.path.insert(0, 'FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_legacy_consumers as census

root = Path('.')
inv = census.inventory(root)
target_harnesses = {
    'fraktal_ab_press_parity',
    'fraktal_ab_phase1_execute',
    'fraktal_ab_phase2_execute',
    'fraktal_ab_phase3_execute',
    'fraktal_ab_phase4_execute',
    'fraktal_ab_s3_execute',
}

found = {c['module']: c for c in inv['consumers'] if c['module'] in target_harnesses}
print(f"Target harnesses scanned: {len(found)} of {len(target_harnesses)}")
failed = []
for name in sorted(target_harnesses):
    entry = found.get(name)
    if not entry:
        print(f"OK: {name} not in consumers (completely unaffected)")
        continue
    direct = entry.get('directLegacyReads')
    imports = entry.get('legacyImports', [])
    print(f"{name}: direct={direct}, legacyImports={imports}")
    if direct is not None:
        failed.append(f"{name} has directLegacyReads: {direct}")
    if imports:
        failed.append(f"{name} has legacyImports: {imports}")

if failed:
    print("FAILURES:")
    for f in failed:
        print("  -", f)
    sys.exit(1)

print("ALL TARGET HARNESSES CLEAR OF DIRECT LEGACY CALLS AND IMPORTS.")
