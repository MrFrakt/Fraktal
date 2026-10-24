from pathlib import Path
import datetime
import gzip
import hashlib
import json
import re

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
WORK = Path(__file__).parent
BASE = ROOT / 'Specification/AllenBradley'
NAME = 'AB_S3F_CANONICAL_INVENTORY_2026-10-22'
REPORT = BASE / 'Evidence' / (NAME + '.md')
DEST = BASE / 'Evidence' / NAME
sha = lambda raw: hashlib.sha256(raw).hexdigest()

inventory = json.loads((WORK / 'inventory_01.json').read_text())
assert inventory['status'] == 'review-required-not-a-passed-preparation'
assert inventory['addedLegacyPaths'] == 801 and inventory['proposedTypeChanges'] == 110
assert not inventory['controllerAccess'] and not inventory['acceptanceRulesChanged']
for name, binding in inventory['sourceBindings'].items():
    raw = (ROOT / name).read_bytes()
    assert len(raw) == binding['bytes'] and sha(raw) == binding['sha256'], name
source = json.loads((WORK / 'source_verification_01.json').read_text())
assert source['passed'] and source['unchangedS3ePreparedRootSources'] == 76
for name, pin in source['sha256'].items():
    assert sha((ROOT / name).read_bytes()) == pin, name
required = ('configuration_tests_01', 'root_tests_01', 'spec_gate_01', 'contracts_gate_01',
            'consistency_gate_01', 'whitespace_gate_01', 'prior_seals_01')
for name in required:
    assert json.loads((WORK / (name + '_exit.json')).read_text())['exitCode'] == 0, name
for name, count in (('configuration_tests_01', 135), ('root_tests_01', 74)):
    assert re.search(r'Ran ' + str(count) + r' tests in [\d.]+s\s+OK', (WORK / (name + '.log')).read_text()), name
prior = json.loads((WORK / 'prior_seals_verification_01.json').read_text())
assert prior['passed'] and prior['records'] == 17 and prior['artifacts'] == 3161
documents = ('AB_CANONICAL_PUBLICATION_S3F_CONTRACT_REVIEW_2026-10-22.md',
             'AB_CANONICAL_PUBLICATION_S3F_INVENTORY_2026-10-22.json',
             'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
             'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md',
             'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
             'AB_FROZEN_CONTRACTS_V2.json')
for name in documents:
    assert (BASE / name).is_file(), name
assert json.loads((BASE / 'AB_FROZEN_CONTRACTS_V2.json').read_text())['active'] is False
assert REPORT.is_file() and not DEST.exists()
DEST.mkdir()


def put(name, raw):
    target = DEST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as f:
        f.write(raw)


for p in sorted(WORK.iterdir()):
    if not p.is_file() or p.name.startswith(('package_01', 'seal_verification_')):
        continue
    assert '.acd' not in p.name.lower() and 'credential' not in p.name.lower(), p.name
    put('Analysis/' + p.name, p.read_bytes())
for name in inventory['sourceBindings']:
    put('Source/' + name, (ROOT / name).read_bytes())
for name in documents:
    put('Target/' + name, (BASE / name).read_bytes())

artifacts = []
for p in sorted(DEST.rglob('*')):
    if not p.is_file():
        continue
    raw = p.read_bytes()
    artifacts.append(dict(path=p.relative_to(DEST).as_posix(), bytes=len(raw), sha256=sha(raw)))
manifest = dict(schema='fraktal.ab.s3f-canonical-inventory-evidence', schemaVersion=1,
    date='2026-10-22', timeZone='America/Mexico_City',
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=REPORT.name, reportSha256=sha(REPORT.read_bytes()),
    status='contract-review-pending', preparationPassed=False, runtimeAccepted=False,
    priorS3eRuntimeAccepted=True, productCodeChanged=False, controllerAccess=False,
    tagWrites=0, controllerChanges=0, commitOrPush=False,
    currentControllerAuthorization=False, acceptanceRulesChanged=False,
    previousPaths=2154, addedLegacyPaths=801, cumulativeLegacyPaths=2955,
    proposedTypeChanges=110, proposedTypeChangeCounts=inventory['proposedTypeChangeCounts'],
    proposedMissingCoreFields=inventory['coreFieldsAbsentFromFrozenOracle'],
    proposedPageEntryCounts=[16, 14], v2Active=False,
    existingConfigurationTests=dict(tests=135, seconds=38.636, passed=True),
    rootTests=dict(tests=74, seconds=2.175, passed=True),
    reusedAbSuite=source['priorAbSuite'], unchangedS3eRootSources=76,
    nativeBuilds='Prior S3e builds unchanged; no S3f image exists',
    skipped=['S3f native build/Capacity/scan/runtime: no generated image',
             'Flutter: no HMI change'], failedValidationRuns=[],
    nativeAcdFilesArchived=False, credentialFilesArchived=False,
    artifacts=artifacts, artifactCount=len(artifacts), totalBytes=sum(a['bytes'] for a in artifacts),
    priorSeals=prior['rows'])
put('manifest.json', json.dumps(manifest, indent=2).encode())
for a in artifacts:
    raw = (DEST / a['path']).read_bytes()
    assert sha(raw) == a['sha256'] and len(raw) == a['bytes'], a['path']
assert sha(REPORT.read_bytes()) == manifest['reportSha256']
result = dict(passed=True, reportSha256=manifest['reportSha256'],
    manifestSha256=sha((DEST / 'manifest.json').read_bytes()), artifacts=len(artifacts),
    bytes=manifest['totalBytes'], predecessorRecords=17, predecessorArtifacts=3161,
    contractDecisionPending=True, controllerAccess=False, acceptanceRulesChanged=False)
with (WORK / 'seal_verification_01.json').open('x') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result))
