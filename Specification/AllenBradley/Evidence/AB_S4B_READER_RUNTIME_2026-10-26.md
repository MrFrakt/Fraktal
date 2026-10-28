# S4b canonical reader native qualification — 2026-10-26

**The bounded reader passes its functional Echo qualification: 41 candidate
checks, 87 paired replays, 902 cyclic samples, four oracle-equal
configuration pages, detail reads and idle equivalence. Scan review remains
open: 10,033 us cumulative maximum and one overlap on a 10 ms task. Genealogy
and all 31 baseline/final checks are restored. Desktop rendering remains open.**

The owner answered “Approve guarded S4b reader retry” to
`call_abc4d640a85f42539728d5b6b697dbb4:0`, approving the
[sealed reader package](AB_S4B_READER_RETRY_PREPARATION_2026-10-26.md).
The guarded operation scope completed and its authorization is consumed.
Local date is October 26; UTC timestamps fall on October 27.

## Target, image and safeguards

- Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0.
- Prepared ACD `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`;
  source `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
- Fresh backup SHA256
  `014998F122079367D4FF88FE2F53A580C1004A3651B6833AB48EAAB755403D70`.
- Fresh service/listener, identity, fault/mode, dump, idle/logout/document
  guards, backup, SDK audits, download/Run, read-back and access audits pass.
- Exact-image offline Capacity remains **65%**: 2,066,100 used /1,079,628
  available /3,145,728 total Blocks. Both v38 build/read-back proofs transfer
  through unchanged PLC/source/image hashes. The SDK-saved working ACD is the
  only changed file among 744 bindings; prepared originals remain pinned.

## Native results

- **41/41 fixture checks**: 31 main, two Access and eight configuration/store.
  Every changed value/policy is restored and the isolated set store is empty.
- **87/87 independent raw-record replays**, with exact values and types over
  4799–5407 occupied paths.
- **902 cyclic Dart samples**: 902 all Good and 0 with
  payload-free Uncertain rows, no Bad values or rejected root samples. Uncertain
  rows are retained as unavailable and never counted as Good. Fast age
  median/p95/maximum **684.1535 /
  774.077 /848.974 ms**.
  RPC median/p95/maximum **694355.0 /
  786329 /859384 us**.
  Largest accepted returned row window **9594 us**,
  strictly below the declared 10,000 us interval. Source age includes the
  accepted pre-counter request. No whole-document same-scan claim is made.
- **Four read-only configuration pages**, live and all three occupied model
  banks, match the independent post-fixture legacy/Core oracle in both value
  and JSON runtime type: **1100 scalar comparisons**.
  The checker joins oracle definitions/values using PLC manifest ReadServices;
  it does not obtain its expectations from Dart page values. Targeted sequence
  detail reads return the versioned quality envelope and do not renew station
  liveness. The observer performs **zero writes** and uses no migration frame.
- **Idle equivalence: 5407 canonical values/types, exact**.
  Generic acquisition recovers **5407 values across
  7 modules** from Symbol/Template objects and the
  manifest, without a station declaration in the client.
- Native TASK scan median **966.0 us**, cumulative maximum
  **10033 us**, **1 overlap** on the 10 ms task.
  MaxScan is cumulative through the candidate workload, not a host stopwatch.

The desktop plan's explicit retry effort is 20 attempts within the original
one-second deadline. Equal-even proof, accepted window, odd-counter pacing,
fast Good/expiry 1/3 seconds, slow 7.5/15 seconds and strict fresh-root checks
remain in force. Every previous failed run remains separately sealed.

## Scan finding — review open

The session runner returns success because all requested operations and
functional assertions pass; its timing step records measurements. Post-run
review keeps native acceptance open for the **10,033 us /one-overlap** finding.
This is separate from the reader's passing functional proof. It is not waived
or turned into a zero-overlap claim.

The archived TASK scalars in all 87 paired captures have the same maximum and
overlap count. They were already present at the earliest pair (sample 2,350,
about 23.5 seconds after its probe counter began); no further overlap appears
in that captured timeline. Captured LastScanTime ranges 944–1,144 us, median
973 us. The final 20 timing samples are steady; their maximum is cumulative.
These data do not locate the initial event or distinguish PLC execution from
host scheduling. No counter or fault is cleared. A follow-up should record
TASK scalars from Run through discovery/readiness and the active workload.

## Rollback

The pinned genealogy image was downloaded from a hash-checked copy; its
original remains
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
Exact original five host documents, **31/31 baseline checks**, policy, MANUAL
cleanup, final checks and preflight pass. Baseline scan median/cumulative
maximum **99.0 /1167 us**, no overlaps.

Final verified state: Run, not faulted, scanning, MANUAL/idle, logged out, not
restoring, original policy and all five saved/live documents equal. No dumps,
fault clears, clock changes, power/vendor-state operations or Echo hard kills.

## Scope and remaining work

This establishes passing functional reader/configuration/tier behavior at this
exact Echo scope. Full native scan review remains open. It does not accept the desktop rendering/connection flow, physical
hardware, CIP Security/direct writes or the whole S4–S7 plan. UI acceptance
still needs the real generic shell and its read-only controls/surfaces.
S5 gateway/installer, S6 migration/persistence/event ownership/retirement and
S7 physical/security acceptance remain, including S3 real-I/O proof.

A preliminary pre-S6 syntax census is archived: 373 bound Python files,
54 tools and 53 test modules with direct legacy references. Its transitive
closure is 155 tools/129 test modules. These include oracle, metadata and test
dependencies; they are not all live controller readers. Classification and
runtime-owner review remain before migration or deletion. No S6 acceptance
is claimed by this inventory.

Offline gates remain **647 Flutter tests, 12 skipped**, Flutter 3.47.5 /
Dart 3.13.4, analyzer, enforced lockfile, rebuilt Windows, 74 root tests and
all root gates. The unchanged PLC retains 2,336 AB tests through 373 bindings.
V2/Part III remain inactive. Nothing is committed or pushed; credentials and
ACD binaries are excluded. All native/raw evidence and failed runs are kept.
