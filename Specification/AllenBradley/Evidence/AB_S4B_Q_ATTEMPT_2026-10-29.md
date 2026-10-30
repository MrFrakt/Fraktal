# S4b-Q native attempt — 2026-10-29

**The candidate fixture passes; S4b remains open. Echo is restored to genealogy.**

This is the first native session using the approved O8 source qualified in
[the three-profile rehearsal record](AB_S4B_O8_CONFIGURATION_HEARTBEAT_2026-10-28.md).
[Preparation](AB_S4B_Q_PREPARATION_2026-10-29.md) seals 700 inputs and the false
authorization template before applying the existing Echo-only standing O3 grant.
Target: `601FC87B`, 127.0.0.1 slot 0, 1756-L81E v38.011. Candidate ACD
`30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`,
source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
Capacity is the unchanged-image measurement: 65%, 2,066,212 used / 1,079,516
available / 3,145,728 Blocks. Flutter 3.47.5 / Dart 3.13.4.

| Gate | Result |
|---|---|
| Guard, backup, download, SDK audits, read-back, access | Passed |
| E1 candidate fixture | 41/41: 31 inherited, 2 Access, 8 configuration; fixture and policy restored |
| E2 raw-read replay | 87/87 exact values/types, replayed after rollback without controller I/O |
| E3 concurrent read-only Dart observer | Failed after 43 samples; zero writes |
| E4 configuration | Skipped; observer failure exits inherited runner |
| E5 idle equivalence | Skipped for the same reason |
| E6 generic acquisition | Skipped for the same reason |
| E7 LIVE profile desktop | Skipped for the same reason |
| E8 TASK/scan | Incomplete: 6,416 post-download observations, cumulative maximum 8,994 µs, zero overlaps; final 20-sample stage skipped |
| E9 rollback | Passed: genealogy, five exact original documents, 31/31 baseline cases, final checks and preflight |

The observer retains the rejected snapshot, not merely its exception. Fifty-six
Status leaves have `read-expired`, age **3,310.162 ms** against the unchanged
1,000/3,000 ms fast Good/expiry profile. Their last accepted window is 7,807 µs.
The final refresh has 20 attempts in 216,300 µs; the raw before/after values
change on body reads, with odd-before observations also retained. Windows range
from 319 to 15,805 µs; acceptance still requires equal even revisions within
the published 10,000 µs mutation period. This is an acquisition failure, not
evidence of a changed PLC value or a faulty coherence rule. The trace also
records large coalesced groups; whether tier selection, grouping or native
service cost causes their repeated misses needs offline reproduction.

Two harness defects are recorded without treating their missing outcomes as
passes. First, `candidate_regressions_v2.py` combines the successful writer
fixture with the failed observer exit, and the parent enters rollback before
its read-only stage loop. Consequently P5 is not met in this attempt. The next
runner must preserve a writer/observer failure and still collect independent
read-only results on the healthy candidate. Second, the one-second host CPU
sampler stops when Windows returns an invalid wildcard process counter. Its
short offline probe passed, but the native run exposes process churn. There is
insufficient CPU coverage and no desktop attempt, so O7 is not triggered.

The candidate TASK monitor completes normally. Its host marker is after download
and before Run; no counters are cleared. The baseline timing and final checks
are separate from candidate acceptance. The post-run native gate summary was
written before the independent replay and accurately retains missing gate
files; `runtime_analysis_01.json` incorporates the subsequent successful replay
without editing that earlier result.

Rollback uses a verified copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
The original is never opened. The five host documents regain their exact
original revisions and values; saved/live documents and original policy agree.
Final state: Run, not faulted, scanning, MANUAL, idle, logged out, not restoring.
No dumps, fault/TASK-counter clears, clock changes, power operations, vendor-state
edits or Echo hard kills occur.

The payload is append-only and excludes credentials, binaries and ACD/BAK.
Its input manifest preserves the exact tested source. Existing offline results
remain scoped: 740 HMI tests passed/12 skipped, 74 root tests and unchanged
2,339 AB/both-v38/Capacity gates; no new PLC compilation is claimed here.
S4b exit requires E1–E9 together, so no stage exit, commit or push follows.

Next: reproduce E3 offline, correct the acquisition owner and P5/CPU helpers,
qualify the final source and repeat the guarded session. Then S5 gateway/Web/
installer and S6 retirement/persistence/events remain. Physical S7 is deferred
under O2.
