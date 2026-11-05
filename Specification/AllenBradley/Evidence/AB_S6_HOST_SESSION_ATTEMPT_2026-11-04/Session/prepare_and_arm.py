"""Bind every session input by SHA-256, then arm the standing O3 record (no controller access).

Run only after the candidate's source is committed and HEAD regenerates the
pinned candidate L5X byte for byte (regeneration_check.json).
"""
from pathlib import Path
import datetime, hashlib, json, subprocess

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
CANDIDATE, SOURCE = ('A4B4FC7811DCE769EFAE14B175C1A9E51373A40310588EC92B164F81753417D3',
                     '847C428935E2BFBA3A131E90F0DAC7BC15072B4158B83D5C804206BFB0352059')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


assert not (D / 'session_started.json').exists() and not (D / 'authorization.json').exists()
regeneration = json.loads((D / 'regeneration_check.json').read_bytes())
head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
assert regeneration['identical'] is True and regeneration['repositoryHead'] == head
assert digest(D / 's6_host_04.ACD') == CANDIDATE and digest(D / 's6_host_04.L5X') == SOURCE
(D / 'canonical.sha256').open('x', encoding='utf-8').write(CANDIDATE + '\n')
inputs = sorted([*D.glob('*.py'), *D.glob('scripts/*.py'), D / 'authorization.template.json', D / 'canonical.sha256',
                 D / 'capacity_review.json', D / 's6_host_04.ACD', D / 's6_host_04.L5X', D / 'regeneration_check.json',
                 D / 'session/Program.cs', D / 'session/HostSession.csproj',
                 D / 'session/bin/Debug/net8.0/win-x86/HostSession.exe', D / 'bin/fraktal_host_adapter.exe',
                 Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD'),
                 Path('C:/work/fraktal-ab-s5-20261029/session_19/preflight.json'),
                 Path('C:/work/fraktal-ab-s6-rebaseline-20261104/session_01/preflight.json'),
                 Path('C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe')])
bindings = dict(repositoryHead=head, sha256={str(p).replace('\\', '/'): digest(p) for p in inputs})
with (D / 'source_bindings.json').open('x', encoding='utf-8') as stream:
    json.dump(bindings, stream, indent=2)
value = json.loads((D / 'authorization.template.json').read_bytes())
assert value['CurrentOwnerApproved'] is False and value['CanonicalSha256'] == CANDIDATE and value['SourceSha256'] == SOURCE
value.update(CurrentOwnerApproved=True,
             OwnerInstruction=('Standing owner decision O3 (AGENTS.md 3a; plan 4 and 6.3): the dedicated Echo 601FC87B '
                               'exists exclusively for repository agents, and guarded sessions need no per-session '
                               'approval. Owner, 2026-11-04: "go on, echo is available". WP6.5 needs the canonical '
                               'HostEvents ring proven against the legacy one on a native capture before WP6.6 '
                               'removes the legacy ring.'),
             **{k: True for k in ('BackupUploadAuthorized', 'DownloadAuthorized', 'MailboxOrTagWritesAuthorized',
                                  'ManualNormalizationAuthorized', 'RestoreGenealogyAuthorized',
                                  'BaselineRegressionWritesAuthorized', 'HostAdapterWritesAuthorized')},
             ArmedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D / 'authorization_armed_record.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(standingDecision='O3', sourceBindingsSha256=digest(D / 'source_bindings.json'), authorization=value),
              stream, indent=2)
with (D / 'authorization.json').open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(armed=True, inputs=len(inputs), repositoryHead=head)))
