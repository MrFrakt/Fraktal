"""Update living C5 docs only after the full discovery rerun passes."""
from pathlib import Path
import json

R=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
assert json.loads((W/'ab_suite_05_exit.json').read_bytes())['exitCode']==0
assert json.loads((W/'prepare_c5a_04.json').read_bytes())['passed']
assert json.loads((W/'qualification_04.json').read_bytes())['passed']
p=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md'
s=p.read_text(encoding='utf-8')
s=s.replace('## C5a in the working tree','## C5a complete offline')
old='''checks and the exact executable-token delta proof pass. The final full AB
suite, remaining v38/Capacity checks and evidence sealing are in progress.
All 44 gateway tests, locked dependencies, analyzer and executable build pass;
all 85 root tests and the three root gates pass before the final doc update.'''
new='''checks and the exact executable-token delta proof pass. The final discovery
rerun passes all 2,612 AB tests; the old storage test is corrected to treat
Mailbox as a scalar record owner, with all 10 storage tests passing. Both
profiles build/read back on both v38 targets, with access/default audits,
byte-identical regeneration and legacy-output checks. Capacity is 60% for
genealogy (1,915,620 used / 1,230,108 available / 3,145,728 Blocks) and 46% for
press (1,447,072 / 1,698,656 / 3,145,728). All 44 gateway tests, locked
dependencies, analyzer and executable build pass, as do the 85 root tests and
three root gates. The sealed scope is recorded in
[C5a evidence](Evidence/AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06.md).'''
assert s.count(old)==1
p.write_bytes(s.replace(old,new).encode('utf-8'))
p=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
s=p.read_text(encoding='utf-8')
anchor='''remaining HX/O11 migrations and integrated native S6-Q stay open.

**WP6.7'''
addition='''remaining HX/O11 migrations and integrated native S6-Q stay open.

**C5a done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06.md),
[working notes](AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md)). Collapsed press
commands use O11 writeBatch through an owned, package/serial/root-pinned Dart
gateway; their ACK and numeric refusal key are independently read over CIP.
O10 V2 permits native member selection under the unchanged strict scan proof.
The press gains the approved V6.7 counter bindings: its frozen S3 parent is
V6.6, and C4b's earlier replay supplied those bindings synthetically. This
closes a metadata prerequisite, not a native acceptance gate. All 2,612 AB and
85 root tests pass, both profiles build/read back on both v38 targets, and the
schema/token/default/access proofs pass. Capacity is 60% genealogy
(1,915,620/3,145,728 Blocks), 46% press (1,447,072/3,145,728). No controller
operations were performed; the legacy declarations remain byte-identical.

C5 continues in two dependent increments without changing its exit gate:
remaining HX fact/read/command migrations and the public host-adapter/set
lifecycle first, then Frame/staged endpoint removal and V6.12 readers. The
press's configuration/set clients need the already approved read-view,
owner-revision and host-service publications before they join. A shared
command facade alone does not qualify a whole legacy harness. C6/C7 and
integrated native S6-Q remain after C5.

**WP6.7'''
assert s.count(anchor)==1
p.write_bytes(s.replace(anchor,addition).encode('utf-8'))
print('Living C5 notes and plan updated; C5 exit remains open.')
