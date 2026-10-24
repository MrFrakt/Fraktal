"""Package this completed S0 run without credentials or native ACD files."""
import hashlib
import json
from pathlib import Path

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
WORK = Path('C:/work/fraktal-ab-s0-20261020/readiness_20edac489b6c46e2b6229c76d400e9e7')
RUN = Path(__file__).resolve().parent
ARCHIVE = ROOT/'Specification/AllenBradley/Evidence/AB_S0_CANONICAL_TYPES_2026-10-20'
ARCHIVE.mkdir(exist_ok=False)

def digest(path):
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest().upper())

def copy(source, relative):
    destination = ARCHIVE/relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(source.read_bytes())

# Explicit folders and suffixes: no credential path, ACD, binaries or dependency cache.
for source in sorted(RUN.iterdir()):
    if source.is_file() and source.suffix in ('.json', '.log', '.py', '.L5X'):
        copy(source, Path('Run')/source.name)
for name in ('preflight.json', 'probe.sha256', 'backup.sha256', 'measurement_02.json',
             'corrected_combined/combined.json', 'corrected_combined/s0_combined.L5X',
             'probe_prepared_compare.json', 'probe_prepared_readback.L5X',
             'probe_downloaded.L5X', 'session/Program.cs', 'session/S0Session.csproj',
             'scripts/guard_echo.py', 'scripts/preflight.py', 'scripts/probe_loaded.py'):
    copy(WORK/name, Path('Work')/name)
for name in ('fraktal_ab_s0_canonical_probe.py', 'fraktal_ab_s0_canonical_measure.py',
             'test_fraktal_ab_s0_canonical_probe.py'):
    copy(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'/name, Path('Sources')/name)
for name in ('AB_FROZEN_CONTRACTS_V2.json',
             'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'):
    copy(ROOT/'Specification/AllenBradley'/name, Path('ReviewDrafts')/name)

native = []
for label, path in (
    ('current backup', WORK/'echo_before_s0.ACD'),
    ('probe after SDK download/save', WORK/'s0_probe.ACD'),
    ('restoration copy after SDK download/save', WORK/'genealogy_restore.ACD'),
    ('unchanged original genealogy ACD', Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')),
    ('restored genealogy export', WORK/'genealogy_restored.L5X'),
    ('original genealogy source', Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.L5X'))):
    native.append(dict(label=label, **digest(path)))

artifacts = []
for path in sorted(ARCHIVE.rglob('*')):
    if path.is_file():
        row = digest(path)
        row['path'] = path.relative_to(ARCHIVE).as_posix()
        artifacts.append(row)

manifest = dict(
    schema='fraktal.ab.s0-canonical-types-evidence', schemaVersion=1,
    date='2026-10-20', timeZone='America/Mexico_City',
    sourceCommit='a1163c7c7bec21988167bc971145b1366206e9ce',
    authorization=json.loads((RUN/'authorization.json').read_text(encoding='utf-8')),
    firstRuntimeMeasurementCompleted=True, supplementaryProbeCompleted=False,
    ownerV2ApprovalPending=True, stageS1Started=False,
    preparedProbeSha256=(WORK/'probe.sha256').read_text().strip(),
    nativeAcdFilesArchived=False, nativeArtifactReferences=native,
    validation=dict(abTests=1901, rootGateTests=74, compilerTargets=2,
                    liveRegressions=31, genealogyRows=21,
                    strictConsistencyErrors=0, strictConsistencyWarnings=0,
                    replayComparisons=47, replayEqual=45, replayFindings=2,
                    originalGenealogyAcdUnchanged=True,
                    finalChecks=json.loads((RUN/'final_checks_03.json').read_text(encoding='utf-8')),
                    capacityEstimateMeasured=False, nativeMaxScanTimeMeasured=False),
    artifacts=artifacts)
with (ARCHIVE/'manifest.json').open('x', encoding='utf-8') as stream:
    json.dump(manifest, stream, indent=2)
    stream.write('\n')
for row in artifacts:
    assert digest(ARCHIVE/row['path'])['sha256'] == row['sha256']
print(json.dumps(dict(archive=str(ARCHIVE), artifacts=len(artifacts),
                      bytes=sum(row['bytes'] for row in artifacts), hashesVerified=True)))
