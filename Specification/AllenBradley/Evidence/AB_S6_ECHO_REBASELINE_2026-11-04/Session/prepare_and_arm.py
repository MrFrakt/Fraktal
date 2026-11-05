"""Bind every session input by SHA-256, then arm the standing O3 record (no controller access)."""
from pathlib import Path
import datetime, hashlib, json, subprocess

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
PIN = 'D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


assert not (D / 'session_started.json').exists() and not (D / 'authorization.json').exists()
(D / 'canonical.sha256').open('x', encoding='utf-8').write(PIN + '\n')
inputs = sorted([*D.glob('*.py'), *D.glob('scripts/*.py'), D / 'authorization.template.json', D / 'canonical.sha256',
                 D / 'session/Program.cs', D / 'session/RebaselineSession.csproj',
                 D / 'session/bin/Debug/net8.0/win-x86/RebaselineSession.exe',
                 Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD'),
                 Path('C:/work/fraktal-ab-s5-20261029/session_19/preflight.json'),
                 Path('C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe')])
head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
bindings = dict(repositoryHead=head, sha256={str(p).replace('\\', '/'): digest(p) for p in inputs})
assert bindings['sha256']['C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD'] == PIN
with (D / 'source_bindings.json').open('x', encoding='utf-8') as stream:
    json.dump(bindings, stream, indent=2)
value = json.loads((D / 'authorization.template.json').read_bytes())
assert value['CurrentOwnerApproved'] is False and value['Serial'] == '601FC87B' and value['CanonicalSha256'] == PIN
value.update(CurrentOwnerApproved=True,
             OwnerInstruction=('Standing owner decision O3 (AGENTS.md 3a; plan 4 and 6.3): the dedicated Echo 601FC87B '
                               'exists exclusively for repository agents, and guarded sessions need no per-session '
                               'approval. Owner, 2026-11-04: "go on, echo is available". Echo was factory-reset that day, '
                               'so the plan 4 rollback baseline is re-established before any S6 native session.'),
             RestoreGenealogyAuthorized=True, BaselineRegressionWritesAuthorized=True,
             ManualNormalizationAuthorized=True, MailboxOrTagWritesAuthorized=True,
             ArmedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D / 'authorization_armed_record.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(standingDecision='O3', sourceBindingsSha256=digest(D / 'source_bindings.json'), authorization=value),
              stream, indent=2)
with (D / 'authorization.json').open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(armed=True, inputs=len(inputs), repositoryHead=head)))
