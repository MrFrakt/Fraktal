"""Record WP4b.5 implementation and its unmet rehearsal gate, without acceptance."""
from pathlib import Path
import json,re
R=Path('C:/Users/SoftIndVM/Fraktal');D=R/'Specification/AllenBradley';W=Path(__file__).parent
assert json.loads((W/'flutter_01_exit.json').read_bytes())['exitCode']==0
match=re.search(r'\+(\d+) ~(\d+): All tests passed!',(W/'flutter_01.log').read_text(encoding='utf-8'))
assert match and int(match[1])>=692 and int(match[2])==12
tests=int(match[1]);evidence='Evidence/AB_WP4B5_REHEARSAL_2026-10-28.md'
text=f'''### 2.3 Offline continuation, 2026-10-28 — WP4b.5 gate remains open

The [rehearsal record]({evidence}) implements the loopback peer and tests wire
discovery against both golden and hash-pinned sealed bytes. Seven peer tests
pass. The peer serves symbolic/fragmented reads and read-only MSPs, refuses
the Echo port, echoes the transport identity/context, preserves native type
codes and handles, and shuts down explicitly. Synthetic counters retain the
10 ms/equal-even model. Latency is piecewise interpolation of the recorded
minimum/median/p95/maximum, not an invented empirical sample set.

The profile target has an explicit rehearsal flag and separate native/result
labels. Its in-memory acceptance panel is configured for public read visibility
through the existing content API; live mode remains logged out and read-only,
without changing PLC policy, data or session identity. Every original view,
refusal and freshness condition stays required. Trace-only successful mapped
ages and worker operation boundaries supplement the existing phase traces.

**The prerequisite does not pass:** the final-source profile model run takes
3,397.686 ms awaiting its first snapshot and refuses at effective age
1,001.601 ms; debug takes 4,135.311 ms and refuses at 1,027.650 ms. Neither
accepts a view. UI reply waits are 1.076/0.679 ms; this does not isolate a host
or controller cause. These are synthetic-server results, never native E7.

A separately labelled zero-injected-delay diagnostic maps seven snapshots
(maximum age 261.606 ms) and captures Overview plus three root tabs, then
becomes STALE after Statistics demand. That demand promotes 2,280 leaves into
slow snapshots (excluded count 3,660 → 1,380); a snapshot starts but does not
finish before the fast window expires. The secondary finder exception is kept;
later test guards diagnose loss of LIVE before further tab lookups. This run
is apparatus-only and cannot satisfy the latency-model gate.

All launches verify the genealogy preflight before and after, make no controller
changes and stop only their local peer. The three-consecutive-profile/700 ms
prerequisite remains **0 passing runs**. No new native session is prepared.
The O7 fallback is not triggered: no native E7/host-CPU threshold is claimed.

Current unit gates: **{tests} HMI passed /12 skipped**, analyzer, locked
dependencies and Windows profile build. All 373 PLC/gate bindings remain
unchanged, transferring 2,339 AB tests, both v38 builds and 65% Capacity.
Root spec/contracts/strict consistency/74 tests/whitespace are checked after
this status edit. No stage exit or commit/push is claimed.

Next: measure requested versus realized rehearsal delay at the socket boundary
and implement/test bounded slow-detail scheduling that preserves cyclic
freshness, row proofs, source ages and every demanded value/type. Address the
initial fast acquisition cost as its own constraint. Then require all three
profile rehearsals at ≤700 ms before WP4b.6/S4b-Q. S5/S6 remain; S7 physical
gates stay deferred/excluded as O2 states. The owner decisions in §6.3 stand.

'''
p=D/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';s=p.read_text(encoding='utf-8')
assert '### 2.3 Offline continuation, 2026-10-28' not in s
at=s.index('## 3. Invariants') if '## 3. Invariants' in s else s.index('\n## 3.')
s=s[:at]+text+s[at:]
needle='  - production factory and repository;'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n  - an in-memory public-read acceptance-panel policy, using existing content\n    configuration, while live mode stays logged out and PLC access is unchanged;')
needle='  - a per-request delay drawn from the Flutter distribution in the'
assert s.count(needle)==1
s=s.replace(needle,'  - per-request delay interpolated between measured Flutter quantiles in the')
p.write_text(s,encoding='utf-8',newline='')
p=D/'AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md'
with p.open('a',encoding='utf-8',newline='') as f:
    f.write(f'''\n\n## 2026-10-28 — WP4b.5 implemented; rehearsal prerequisite fails\n\nSeven peer tests pass on golden/sealed bytes; full HMI {tests} passed/12 skipped.\nThe [offline record]({evidence}) preserves the profile/debug startup refusals\nand the zero-delay Statistics/navigation failure. The 3-pass/700 ms gate has\nzero qualifying passes. Echo remains on genealogy with before/after preflights\nand zero controller changes. Current source adds explicit rehearsal labels, a\npublic-read test-panel configuration and trace-only operation/age diagnostics;\nno freshness, retry, row-proof or PLC policy changes. No native preparation,\nstage exit or commit/push. Next is latency calibration plus bounded slow-detail\nscheduling, then the original rehearsal gate. O1–O7 remain settled.\n''')
print(json.dumps(dict(updated=True,hmiTests=tests,skipped=12,rehearsalPassed=False,controllerChanges=0)))
