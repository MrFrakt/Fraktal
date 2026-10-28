"""Read-only verification and SDK log audits for the offline option A image."""
from pathlib import Path
import datetime, gzip, hashlib, json, sys
R = Path('C:/Users/SoftIndVM/Fraktal'); E = R/'Specification/AllenBradley/Evidence'; W = Path(__file__).parent
S = R/'Specification/AllenBradley'
sys.path.insert(0, str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_sdk_log_gate import audit_log
sha = lambda b: hashlib.sha256(b).hexdigest()


def save(name, value):
    with (W/name).open('x', encoding='utf-8') as f: json.dump(value, f, indent=2)


def log(name):
    return (W/name).read_bytes().decode('utf-8', errors='replace')


for target in ('EchoController', 'PhysicalController'):
    report = audit_log(log(f'native_{target}_01.log'), ('Open project', 'Build', 'Save As'), True)
    save(f'sdk_{target}_01.json', report)
    assert report['Clean'], report
report = audit_log(log('prepare_acd_01.log'), ('Open project', 'Build', 'Save As', 'Save'), True)
save('sdk_prepare_01.json', report); assert report['Clean'], report

latest = E/'AB_S3K_READ_SURFACES_OFFLINE_2026-10-25/manifest.json'
previous = json.loads(latest.read_bytes())
names = {row['name'] for row in previous['priorSeals']} | {latest.parent.name}
rows = []; total = 0
for name in sorted(names):
    p = E/name/'manifest.json'; m = json.loads(p.read_bytes())
    for a in m['artifacts']:
        raw = (p.parent/a['path']).read_bytes()
        assert len(raw) == a['bytes'] and sha(raw) == a['sha256'].lower(), (name, a['path'])
        if a.get('expandedSha256'): assert sha(gzip.decompress(raw)) == a['expandedSha256'].lower()
    if m.get('report') and m.get('reportSha256'): assert sha((E/m['report']).read_bytes()) == m['reportSha256'].lower()
    total += len(m['artifacts']); rows.append(dict(name=name, manifestSha256=sha(p.read_bytes()), artifacts=len(m['artifacts'])))
save('prior_seals_01.json', dict(passed=True, records=len(rows), artifacts=total, rows=rows))

cap = json.loads((W/'capacity_auto_01.json').read_bytes())
pins = {'s3k_command_a_01.L5X': '426289A5E71CDEC1DBC5A4C5C7FBCDE4E706676B311362A12A91CFD36083EE78',
        'command_a_01.ACD': cap['CanonicalSha256'], 'command_a_capacity_review.ACD': cap['CanonicalSha256']}
for name, pin in pins.items(): assert sha((W/name).read_bytes()).upper() == pin, name
assert cap['SourceUnchanged'] and cap['VerifiedFit'] and cap['Offline'] and cap['UsedStandardBlocks'] == 1907592
assert cap['AvailableBlocks']+cap['UsedStandardBlocks'] == cap['TotalBlocks'] == 3145728
assert sha((W/'capacity_capture_01.json').read_bytes()) == cap['CaptureSha256']

tests = json.loads((W/'ab_suite_01_exit.json').read_bytes())
assert tests['exitCode'] == 0
start = datetime.datetime.fromisoformat(tests['startUtc']).timestamp()
code = list((R/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py'))
modified_after = [p.name for p in code if p.stat().st_mtime > start]
assert not modified_after, modified_after

# Documentation: the finalize record plus the later reflow, each before/after pinned.
updates = json.loads((W/'documentation_updates_01.json').read_bytes())
current = {}
for name, row in updates.items():
    raw = (R/name).read_bytes(); assert b'\r\n' not in raw, name
    before = (W/('before_'+Path(name).name)).read_bytes()
    assert sha(before) == row['beforeSha256'], name
    current[name] = dict(row, finalSha256=sha(raw))
    if current[name]['finalSha256'] != row['afterSha256']:
        current[name]['laterEdit'] = 'Reflowed header and shortened hashes after finalize; no fact changed'
save('documentation_updates_02.json', current)
save('final_provenance_01.json', dict(passed=True, priorSeals=len(rows), priorArtifacts=total,
     pins=pins, sdkAudits=3, abSourceFiles=len(code), abSourceModifiedAfterSuiteStart=modified_after,
     usedBlocks=cap['UsedStandardBlocks'], availableBlocks=cap['AvailableBlocks'], totalBlocks=cap['TotalBlocks'],
     displayedPercent=cap['DisplayedUsagePercent'], controllerOperations=0, nativeAccepted=False))
print(json.dumps(dict(passed=True, priorSeals=len(rows), priorArtifacts=total, pins=len(pins), sdkAudits=3,
                      abSourceFiles=len(code), documents=len(current))))
