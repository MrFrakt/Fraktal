"""Seal the S3h observation-frame preparation: sources, predecessors, payload."""
from datetime import datetime, timezone
from pathlib import Path
import gzip, hashlib, json, shutil

W = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
EV = ROOT/'Specification/AllenBradley/Evidence'
NAME = 'AB_S3H_CANONICAL_OBSERVATION_FRAME_PREPARATION_2026-10-24'
OUT = EV/NAME
PAY = OUT/'Preparation'
SOURCE = 'BF456BCA68745C39D0903D0DE96B9B8AD4EC9DC502E809F38DA82599D2EFB1F2'
ACD = 'E07C419651A2C6A785D150CAA0BB1894A57CB4453036A0CC2EF2FA8413649745'
OFF = 'E83B9A2CD9593718026528CCDBD83A1EAD6C8A52948FC6616006DAFFB0567315'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert not (OUT/'manifest.json').exists(), 'append-only: already sealed'

# Source closure: the prior 159 bindings, exactly four changed, three added.
T = 'FraktalCore/PLC/Allen-Bradley/tools/'
prior = json.loads((EV/'AB_S3H_CANONICAL_DIAGNOSTIC_PREPARATION_2026-10-23/Preparation/source_bindings_01.json').read_text())['sha256']
changed = {T+n for n in ('fraktal_ab_canonical_publication.py', 'fraktal_ab_declaration.py',
                         'fraktal_ab_genealogy_s3h_demo.py', 'fraktal_ab_s2_equivalence.py')}
added = {T+n for n in ('fraktal_ab_canonical_observation.py', 'fraktal_ab_paired_observation.py',
                       'test_fraktal_ab_canonical_observation.py')}
bindings = {}
for name, pin in prior.items():
    now = sha(ROOT/name)
    assert (now != pin) == (name in changed), ('unexpected source state', name)
    bindings[name] = now
for name in added:
    assert name not in prior
    bindings[name] = sha(ROOT/name)
assert len(bindings) == 162

# Every canonical predecessor record re-hashes unchanged (the verify_seals.py rule).
diagnostic = json.loads((EV/'AB_S3H_CANONICAL_DIAGNOSTIC_RUNTIME_2026-10-24/manifest.json').read_text())
names = [s['name'] for s in diagnostic['priorSeals']] + ['AB_S3H_CANONICAL_DIAGNOSTIC_RUNTIME_2026-10-24']
seals, total = [], 0
for name in names:
    manifest = json.loads((EV/name/'manifest.json').read_text())
    for artifact in manifest['artifacts']:
        raw = (EV/name/artifact['path']).read_bytes()
        assert len(raw) == artifact['bytes'] and hashlib.sha256(raw).hexdigest() == artifact['sha256'].lower(), \
            (name, artifact['path'])
        if artifact.get('expandedSha256'):
            assert hashlib.sha256(gzip.decompress(raw)).hexdigest() == artifact['expandedSha256'].lower()
    if manifest.get('report') and manifest.get('reportSha256'):
        assert sha(EV/manifest['report']) == manifest['reportSha256'].lower(), (name, manifest['report'])
    seals.append(dict(name=name, artifacts=len(manifest['artifacts']), manifestSha256=sha(EV/name/'manifest.json')))
    total += len(manifest['artifacts'])
assert len(seals) == 39

assert (W/'frame_canonical.sha256').read_text().strip() == sha(W/'s3h_frame_canonical.ACD').upper() \
    == sha(W/'capacity_review.ACD').upper() == ACD
assert sha(W/'s3h_frame_candidate_01.L5X').upper() == sha(W/'s3h_frame_regenerated_01.L5X').upper() == SOURCE
assert sha(W/'s3h_frame_disabled_check.L5X').upper() == sha(W/'compatibility_s3h_frame_off.L5X').upper() == OFF

PAY.mkdir(parents=True, exist_ok=True)
plain = ['generation_01.log', 'disabled_check.log', 'native_echo_01.log', 'native_physical_01.log',
         'echo_readback_01.log', 'physical_readback_01.log', 'echo_access_01.json', 'echo_access_01.log',
         'physical_access_01.json', 'physical_access_01.log', 'helper_build_01.log', 'prepare_acd_01.log',
         'prepared_readback_01.log', 'prepared_access_01.json', 'prepared_access_02.json', 'prepared_access_02.log', 'capacity_auto_01.json',
         'capacity_auto_01.log', 'capacity_capture_01.json', 'compatibility_verification_01.json',
         'ab_suite_01.log', 'focused_01.log', 'read_set_01.log', 'root_tests_01.log', 'root_tests_02.log',
         'ab_spec_01.log', 'ab_spec_02.log', 'ab_contracts_01.log', 'ab_contracts_02.log', 'consistency_01.log',
         'consistency_02.log', 'whitespace_01.log', 'frame_canonical.sha256', 'audit_access.py',
         'verify_compatibility.py', 'verify_read_set.py', 'varying_bytes.py', 's3h_frame_disabled_check.py',
         'package_preparation.py', 'prepare/Program.cs', 'prepare/FramePrepare.csproj', 'prepare/NuGet.Config',
         *sorted(p.name for p in W.glob('compatibility_*.log'))]
for name in dict.fromkeys(plain):
    target = PAY/name
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists(), name
    shutil.copyfile(W/name, target)
for name in ['s3h_frame_candidate_01.L5X', 's3h_frame_regenerated_01.L5X', 's3h_frame_disabled_check.L5X',
             'native_echo_01.L5X', 'native_physical_01.L5X', 'frame_prepared_readback.L5X',
             *sorted(p.name for p in W.glob('compatibility_*.L5X'))]:
    target = PAY/(name + '.gz')
    assert not target.exists(), name
    with open(W/name, 'rb') as source, open(target, 'wb') as raw, \
            gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as packed:
        shutil.copyfileobj(source, packed)

commands = [
    ('disabled_check', 'PYTHONPATH=<scratch decl> python fraktal_ab_generate.py C:/work/echo38_5580_seed.L5X s3h_frame_disabled_check.L5X --declaration s3h_frame_disabled_check'),
    ('generation_01', 'python fraktal_ab_generate.py C:/work/echo38_5580_seed.L5X s3h_frame_candidate_01.L5X --declaration fraktal_ab_genealogy_s3h_demo'),
    ('native_echo_01', 'Fraktal.Ab.OfflineProbe.exe --build-readback s3h_frame_candidate_01.L5X native_echo_01.L5X EchoController'),
    ('native_physical_01', 'Fraktal.Ab.OfflineProbe.exe --build-readback s3h_frame_candidate_01.L5X native_physical_01.L5X PhysicalController'),
    ('echo_readback_01', 'python fraktal_ab_readback.py s3h_frame_candidate_01.L5X native_echo_01.L5X'),
    ('physical_readback_01', 'python fraktal_ab_readback.py s3h_frame_candidate_01.L5X native_physical_01.L5X'),
    ('echo_access_01', 'python audit_access.py native_echo_01.L5X echo_access_01.json'),
    ('physical_access_01', 'python audit_access.py native_physical_01.L5X physical_access_01.json'),
    ('helper_build_01', 'dotnet build -c Debug (prepare/FramePrepare.csproj)'),
    ('prepare_acd_01', 'prepare/bin/Debug/net8.0/win-x86/FramePrepare.exe'),
    ('prepared_readback_01', 'python fraktal_ab_readback.py s3h_frame_candidate_01.L5X frame_prepared_readback.L5X'),
    ('prepared_access_01', 'python audit_access.py frame_prepared_readback.L5X prepared_access_01.json (console output only)'),
    ('prepared_access_02', 'python audit_access.py frame_prepared_readback.L5X prepared_access_02.json'),
    ('capacity_auto_01', 'python fraktal_ab_studio_capacity.py --acd capacity_review.ACD --expect-sha256 ' + ACD
                         + ' --output capacity_auto_01.json --capture-output capacity_capture_01.json'),
    ('compatibility_01', 'python verify_compatibility.py'),
    ('ab_suite_01', 'python -m unittest discover -s FraktalCore/PLC/Allen-Bradley/tools -t FraktalCore/PLC/Allen-Bradley/tools'),
    ('focused_01', 'python -m unittest -v test_fraktal_ab_canonical_observation'),
    ('read_set_01', 'python -I verify_read_set.py FraktalCore/PLC/Allen-Bradley/tools Specification/AllenBradley/Evidence/AB_S3H_CANONICAL_DIAGNOSTIC_RUNTIME_2026-10-24/Diagnostic'),
    ('root_tests_01/02', 'python -m unittest tools.test_check_consistency tools.test_check_ab_spec tools.test_check_ab_contracts'),
    ('ab_spec_01/02', 'python tools/check_ab_spec.py'),
    ('ab_contracts_01/02', 'python tools/check_ab_contracts.py'),
    ('consistency_01/02', 'python tools/check_consistency.py --strict'),
    ('whitespace_01', 'git -c core.whitespace=cr-at-eol diff --check'),
]
records = {
    'commands.json': dict(schema='fraktal.ab.command-record', schemaVersion=1,
                          note='Run in the work folder or repository root; every listed exit code was observed as 0. '
                               '_01 root gates precede the document edits, _02 follow them.',
                          commands=[dict(name=n, exitCode=0, command=c) for n, c in commands]),
    'source_bindings_01.json': dict(passed=True, projectSourceBindings=162, unchanged=155, changed=sorted(changed),
                                    added=sorted(added), sha256=dict(sorted(bindings.items()))),
    'predecessor_seals_01.json': dict(passed=True, records=len(seals), artifacts=total, seals=seals),
    'authorization.template.json': dict(
        schema='fraktal.ab.s3h-observation-frame-session-authorization', schemaVersion=1,
        CurrentOwnerApproved=False, AccessVectorsAuthorized=False, ConfigurationVectorsAuthorized=False,
        Serial='601FC87B', Route='EmulateEthernet\\127.0.0.1 slot 0', Firmware='v38.011',
        CanonicalSha256=ACD, SourceSha256=SOURCE,
        GenealogySha256='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084',
        Scope=['guarded MANUAL normalization when needed', 'fresh preflight and backup',
               'Program/download/Run of CanonicalSha256 and five-document restore',
               'inherited 41 candidate checks; paired captures read the observation frame; no new write vectors',
               'final generic/idle acquisition, sizes and 20-sample TASK gate',
               'hash-checked genealogy rollback, five-document restore and 31 baseline regressions',
               'MANUAL cleanup and final checks'],
        Excluded=['fault clear', 'clock change', 'hard kill', 'commit', 'push']),
}
for name, value in records.items():
    target = PAY/name
    assert not target.exists()
    target.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

artifacts = [dict(path=p.relative_to(OUT).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(PAY.rglob('*')) if p.is_file()]
assert not any(a['path'].upper().endswith('.ACD') for a in artifacts)
report = NAME + '.md'
manifest = dict(
    schema='fraktal.ab.s3h-canonical-observation-frame-preparation-evidence', schemaVersion=1,
    date='2026-10-24', timeZone='America/Mexico_City', sealedUtc=datetime.now(timezone.utc).isoformat(),
    report=report, reportSha256=sha(EV/report),
    status='observation-frame-offline-gates-passed-native-authorization-pending',
    stageAccepted=False, controllerChanges=0, preparedAcdSha256=ACD, sourceSha256=SOURCE, frameOffSourceSha256=OFF,
    observationPeriodMs=50, observationPeriodScans=5, observationSources=31, recordedReadSetCaptures=64,
    sourceBindings=162, abTests=2158, abSeconds=260.822, focusedTests=9, rootTests=74, priorStageImagesExact=8,
    connections=4, maximumOutstandingPerConnection=1, attemptLimit=100, secondsLimit=5, proofFunctionUnchanged=True,
    capacityBlocks=2680132, availableBlocks=465596, totalBlocks=3145728, capacityPercent=85, capacityDeltaFromC6=178412,
    credentialFilesArchived=False, nativeAcdFilesArchived=False, priorSeals=seals, artifacts=artifacts,
    artifactCount=len(artifacts), totalBytes=sum(a['bytes'] for a in artifacts))
(OUT/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(sealed=True, artifacts=len(artifacts), bytes=manifest['totalBytes'],
                      predecessors=len(seals), predecessorArtifacts=total)))
