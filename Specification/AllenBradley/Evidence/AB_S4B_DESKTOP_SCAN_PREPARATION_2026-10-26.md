# S4b desktop and early TASK scan preparation — 2026-10-26

**A fresh unchanged-image session is prepared and is not authorized.** The
[reader run](AB_S4B_READER_RUNTIME_2026-10-26.md) passes 41 cases, 87 replays,
902 entirely Good cyclic samples, four configuration pages/1,100 oracle
comparisons and 5,407-path idle/generic acquisition. Its native cumulative
maximum of 10,033 us and one overlap on a 10 ms task keeps scan review open.
Desktop live acceptance is also pending. Genealogy, original documents and
all 31 baseline/final checks are restored. The earlier grant is consumed.

## Exact target and unchanged PLC

- Echo **601FC87B**, 1756-L81E v38.011, **127.0.0.1 slot 0**.
- ACD `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`; source `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
- Exact-image offline Capacity **65%**: 2,066,100 used /1,079,628 available /
  3,145,728 total Blocks. Both v38 build/read-back/access proofs transfer by
  unchanged PLC/source/image hashes. No PLC or shipping HMI source changed.
- Runner: `C:/work/fraktal-ab-s4b-20261025/desktop_scan_01/qualification_session_v2.py`.

## Proposed guarded session

1. Fresh service/listener/serial/mode/fault/dump/idle/logout/document guards,
   MANUAL normalization if needed, preflight and backup with SDK/access audits.
2. Start read-only native TASK monitoring before download; only after its
   pinned-identity readiness check passes, perform Program/download/Run.
3. The unchanged Dart readiness/observer and five-document restore/41-case
   candidate fixture run, including the original restorations. No added PLC
   write vectors or typed mailbox cases.
4. The real desktop factory, repository and generic UI connect read-only.
   Render discovered module tabs and fieldbus I/O panels; assert read-only
   gates and local start/login refusal. Those assertions must produce no wire
   writes. Then perform the existing idle equivalence, acquisition and native
   scan measurement.
5. Stop the monitor, then pinned-copy genealogy rollback, exact original five
   host documents, 31 baseline cases, MANUAL cleanup, final checks/preflight.

Any desktop/monitor failure still enters guarded rollback. Monitor readiness
failure stops before download. Fault/counter clears, clock changes, power and
vendor-state operations, and Echo hard kills remain excluded. No new session
approval is inferred from the completed reader run.

## TASK finding and instrumentation

All 87 previous native pairs already show MaxScan 10,033 us/OverlapCount 1,
starting at the earliest pair (probe sample 2,350). No further overlap appears
in that timeline; its cause and initial location are unknown. The new helper
polls four fixed HealthProbe DINT scalars at nominal **100 ms**: Samples,
TaskLastScanUs, TaskMaxScanUs and TaskOverlapCount. These are native GSV TASK
observations, not an atomic canonical row or a host-derived PLC scan duration.

Monitoring begins on the verified genealogy baseline before download and
continues through candidate timing. It records host monotonic/UTC read bounds,
counter transitions and temporary tag/transport failures during the download.
It validates identity before readiness and at completion, writes no tags and
never resets counters/faults. This gives bounded event placement, not proof
that an outlier was caused by host scheduling. Its added read traffic is part
of the disclosed workload. No scan-period/acceptance limit is widened.

## Desktop proof and limits

The helper's captured-native fixture passes **31 views**, seven modules and
three fieldbus nodes, with real fonts, verified tab selection, read-only
banner, start/login refusals and zero client write calls. The 31 PNGs and result
are archived. This static fixture deliberately supplies fixture quality and
omits the native freshness envelope; it proves rendering only.

**Live mode never applies fixture substitutions.** It uses the shipping
`createExternalRepository` for the exact pinned `cip://` endpoint, the real
session client's source ages/quality, repository and AppState. Every module
and bus node is discovered from the returned data; no station screen is added.
Live output is separate and cannot be counted as captured-fixture acceptance.

The desktop plan remains **20 attempts /one second**, equal-even counter proof,
accepted windows shorter than the published 10 ms interval, fast Good/expiry
1/3 seconds, slow 7.5/15 seconds and strict root checks. No cached Good identity,
queueing or station declaration is introduced. UI success will not waive a
scan finding; physical/CIP Security evidence remains separate.

## Gates, failures and source bindings

Seven mocked workflow/native-read tests pass: ordinary cleanup, desktop and
monitor failures, readiness failure before download, valid scalar retention,
download transport-error retention and invalid/partial-sample rejection.
All sixteen existing authorization refusals, missing-approval CLI/SDK checks,
and two additional missing-approval monitor/UI refusals pass without controller
access. The fresh SDK helper builds with zero warnings/errors. The final UI
helper replay and analyzer pass.

Earlier helper compile, navigation, fake-async output timeout and unused-import
runs remain archived with their sources. They occurred in captured-fixture or
offline analysis mode and made no Echo connection. No production correction
was required. The earlier incomplete navigation run is not acceptance.

All **316 production/test inputs** match the isolated mirror
and prior successful gates: Flutter **3.47.5 /Dart 3.13.4**, **647 tests,
12 skipped**, enforced lockfile, analyzer and Windows build. These results
transfer by unchanged source hashes. **373 PLC/gate bindings** retain
2,336 AB tests. All 74 root tests and spec/contracts/strict consistency and
Windows-aware whitespace gates pass again. Both original and mirror runtime
sources and the private package map are pinned for this new desktop session.
The owner's facet and Siemens archive edits remain untouched.

**84 prior seals /25947 artifacts** verify unchanged. No approval,
started marker, backup or deployment attempt exists in this new workspace.
Credentials and ACD binaries are excluded; earlier failed evidence is retained.

[AGENTS.md §3a](../../../AGENTS.md) requires “current explicit authorization
and an exact target check immediately before use.” This fresh download/session
therefore needs approval. V2/Part III remain inactive. After S4b desktop and
scan review come S5 gateway/installer, S6 migration/persistence/events/retirement
and S7 physical/CIP Security acceptance, including S3 real-I/O proof. Nothing
is committed or pushed.
