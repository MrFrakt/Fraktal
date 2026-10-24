"""Record the owner's current approval against the sealed observation-frame preparation."""
from pathlib import Path
import datetime, hashlib, json

R = Path(__file__).parent
W = Path('C:/work/fraktal-ab-s3h-20261024/frame_b7a501a104b448438e1e3566840fa12f')
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
E = ROOT/'Specification/AllenBradley/Evidence'
NAME = 'AB_S3H_CANONICAL_OBSERVATION_FRAME_PREPARATION_2026-10-24'
ACD = 'E07C419651A2C6A785D150CAA0BB1894A57CB4453036A0CC2EF2FA8413649745'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


manifest = json.loads((E/NAME/'manifest.json').read_text())
assert sha(E/NAME/'manifest.json') == '50d1d658b7c032f4e107873340b66455ee5c775d59a094d9141a96746164be60'
assert sha(E/manifest['report']) == manifest['reportSha256']
for row in manifest['artifacts']:
    assert sha(E/NAME/row['path']) == row['sha256'], row['path']
bindings = json.loads((E/NAME/'Preparation/source_bindings_01.json').read_text())['sha256']
assert len(bindings) == 162
for name, pin in bindings.items():
    assert sha(ROOT/name) == pin, name
assert manifest['preparedAcdSha256'] == ACD == sha(W/'s3h_frame_canonical.ACD').upper() \
    == (W/'canonical.sha256').read_text().strip()
assert sha(W/'s3h_frame_candidate_01.L5X').upper() == manifest['sourceSha256']
for name in ('authorization.json', 'preflight.json', 'deploy_attempt.json', 'backup.sha256', 'echo_before_s3h.ACD',
             'canonical_downloaded.L5X', 'genealogy_restored.L5X'):
    assert not (W/name).exists(), name

template = json.loads((E/NAME/'Preparation/authorization.template.json').read_text())
approval = dict(
    Serial='601FC87B', CanonicalSha256=ACD, SourceSha256=manifest['sourceSha256'],
    CurrentOwnerApproved=True, ManualNormalizationAuthorized=True, AccessVectorsAuthorized=True,
    ConfigurationVectorsAuthorized=True, FaultClearAuthorized=False, ClockSetAuthorized=False,
    CandidateRows=41, BaselineRows=31, Scope=template['Scope'], Excluded=template['Excluded'],
    NoAddedDirectTraceabilityWrites=True, ObservationFrameAcquisition=True,
    ApprovalSource=('Owner chat reply 2026-10-24 "yes i approve" to: approve the native session on Echo '
                    '601FC87B for ACD E07C4196...649745 - back up, download, run the 41 candidate checks '
                    'reading the frame, roll back to genealogy and run the 31 baseline checks; fault '
                    'clears and clock changes excluded'),
    ApprovedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(), RuntimeDirectory=R.as_posix(),
    PreparationManifestSha256=sha(E/NAME/'manifest.json'), PreparationReportSha256=manifest['reportSha256'],
    SessionExecutableSha256=sha(W/'session/bin/Debug/net8.0/win-x86/FrameSession.exe'),
    SessionSourceSha256=sha(W/'session/Program.cs'))
for path in (W/'authorization.json', R/'owner_session_approval.json'):
    with path.open('x') as out:
        json.dump(approval, out, indent=2)
with (R/'initial_source_verification.json').open('x') as out:
    json.dump(dict(passed=True, sourceBindings=len(bindings), sha256=bindings, preparedAcdSha256=ACD,
                   sourceSha256=manifest['sourceSha256'], sessionExecutableSha256=approval['SessionExecutableSha256']),
              out, indent=2)
print(json.dumps(dict(passed=True, sourceBindings=len(bindings), acd=ACD, controllerChanges=0)))
