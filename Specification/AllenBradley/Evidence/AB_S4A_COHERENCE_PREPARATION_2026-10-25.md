# S4a V6.7 coherence discovery and bounded-read qualification — preparation

2026-10-25, America/Mexico_City. **Offline preparation passes; native S4a
qualification is not run. No controller change is authorized or performed.**
Only the read-only service/listener/identity/fault/keyswitch check ran: it passes
for local Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0, GUID
`91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`. No backup, download, mode or tag write,
fault clear, clock change, power operation or hard kill ran. Last accepted S3
evidence remains unchanged; its genealogy rollback is the last verified baseline.
Nothing is committed or pushed. V2 remains inactive.

## Approved contract and implementation

Owner reply to `call_6bf53f81733f4bac8119326954e3b4d6:0`:
**“A — publish existing counter bindings (Recommended)”**. The
[review](../AB_CANONICAL_PUBLICATION_S4_COHERENCE_REVIEW_2026-10-25.md) records
the missing V6.6 association and exact V6.7 table. This is wire-contract and
dependent offline approval, not controller authorization.

`canonical_read_coherence` is an opt-in flag. V6.7 adds hash-covered exact
count/capacity/rows for `CanonicalPrefix`, `RevisionSymbol`, `Protocol` and
`MutationPeriodUs`, reusing the existing odd/even scan counter. Runtime validation
requires exact root/product coverage, nonoverlap, valid symbols, protocol and
period, and discovered DINT scalar counters. No canonical value, root layout,
cyclic publisher, write endpoint or existing profile changes. Fourteen accepted
profiles regenerate byte-identically: the twelve earlier pins, genealogy S3k and
the press S3 exit image.

The reference reader understands V6.7 but retains its documented whole-record
acquisition limitation. It does not become the shipping coherence engine.
`fraktal_ab_read_group_probe` separately plans small groups from discovered
Templates and bindings, with no station declaration, naming inference or
observation-frame dependency. The schema-only preview, using accepted unchanged
physical layouts with explicitly injected new descriptors, finds **eight groups**:
seven module Status records and one fieldbus channel row. Sizes are **872–1,156
bytes** (root Status 880). That preview is not native V6.7 evidence.

Each probe attempt reads pre-counter, exact group bytes and post-counter.
Equal positive even counters, a window including the first request shorter than
the declared 10,000 µs interval, and the total one-second acceptance deadline are
required. At most three attempts run. Socket timeouts are reduced to remaining
budget; late data is refused. A transport/layout/deadline failure is Bad, closes
the connection and stops acquisition. A coherence conflict is Uncertain with no
payload. Qualification takes 100 samples per planned group, requires at least
95 Good samples for each group and observed counter progress, and checks the
manifest again at the end. Whole-record discovery/cold reads are excluded from
accepted samples. Failed measurements are written with their failure and partial
samples. This first feasibility gate does not accept active-workload freshness,
every consumed row or the full desktop read tiers.

Two internal headless Dart foundations are also implemented:

- `CipTemplateDecoder`: authoritative Template sizes/array strides, full
  12-bit handles, BOOL packing, strict UTF-8 byte lengths, exact BigInt 64-bit
  values, finite floats, bounded depth/expansion and malformed-layout refusal.
- `CipReadCoherenceGuard`: bounded per-group acquisition and quality degradation
  with no non-Good payload. Its caller must validate metadata and establish
  counter liveness; this component does not claim session freshness by itself.

Eight physical golden records come from hash-verified accepted genealogy and
press captures and are checked against the independent Python physical decoder.
Fixture SHA-256: `78795E71320413689F68590C84D7166A578D4A55B2960402C2EAA52A1ECE73AD`.
These are physical decoder goldens, not complete logical snapshot goldens.

## Image, Capacity and passed gates

- Generated L5X SHA-256:
  `20F27F80CF9D0AEFEFA72EB64848927AE6076CF05CB544073575A55728825996`.
- Pristine ACD SHA-256:
  `07C54E8DCE8D70A1EC487684B65F3596922D615448881AA05470304821CC2FF3`.
- Immutable genealogy rollback SHA-256:
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

Automatic Studio offline Capacity, on a disposable review copy:
**1,904,400 used / 1,241,328 available / 3,145,728 total Blocks**, **60%**.
Fit, unchanged source and closed review process are recorded. The increment over
accepted genealogy S3k is **1,056 Blocks**. This is not a native scan measurement.

| Gate | Result and payload output |
|---|---|
| Full AB discovery | **2,320 tests, OK**; `Preparation/ab_suite_02.log` |
| Focused new metadata / probe cases | **5 + 7 pass**; `coherence_python_tests_01.log`, `group_probe_tests_01.log` |
| Root suites | **74 tests, OK**; `Preparation/root_tests_02.log` |
| AB spec / contracts / strict consistency / whitespace | Pass; `Preparation/final_*` and final gate logs |
| v38 EchoController / PhysicalController | Both build; **0 import warnings/errors**, equivalent native read-backs; `native_*_02.log`, `readback_*_02.log` |
| Prepared ACD read-back / effective access / SDK event audit | Pass; `prepared_compare_02.log`, `access_*_02.json`, `qualification_checks_01.json` |
| Accepted-profile regeneration | **14 / 14 exact**; `accepted_images_02.json`, `qualification_checks_01.json` |
| Session authorization refusal | **16 negative cases**, plus missing-approval Python and SDK entry points refuse before controller access; `qualification_checks_01.json` |
| Session helper | Builds at **0 warnings/errors**; `session_helper_build_02.log` |
| Flutter enforced lockfile | Pass with `--enforce-lockfile --offline`; `pinned_lockfile_01.log`; lockfile unchanged |
| Flutter analyzer | **No issues**; `pinned_analyze_01.log` |
| Full Flutter suite | **608 passed, 12 existing skips**; `pinned_suite_01.log`; 17 new decoder/guard tests included |
| Read-only Echo readiness | Pass; `echo_readiness_01.log`; no session preflight recorded yet |
| Native V6.7/group/scan / desktop rendering / physical security | **Not run**; remain separate gates |

The AB suite retains intentional parser-refusal output and an existing fixture
socket ResourceWarning; unittest's result is OK. Exact console outputs and exit
metadata are archived. This does not convert warnings into runtime acceptance.

Flutter used **3.47.5**, framework
`6a19cca56475dbfba1478ee68d7bd0c2ef891da1`, Dart **3.13.4**, from
`C:/work/fraktal-toolchains/flutter-3.47.5`. It is an isolated SDK worktree at the
locally available pinned tag. The owner's existing SDK was 3.47.2/Dart 3.13.2.
The repository lockfile did not change.

Earlier failed outputs remain archived: the first analyzer caught an unsupported
BigInt API, corrected before the passing runs; the first full suite had two
ShiftCard header overflows in narrow panels, reproduced in the existing publish
tests and fixed by wrapping the header; the first root-suite command used an
unimportable discovery directory, corrected to the three prescribed modules.
The final pinned full suite covers the UI fix. No new dependency was introduced.
Owner Siemens archive `.dart_tool` edits were left alone.

## Prepared current-authorization boundary and rollback

Work folder: `C:/work/fraktal-ab-s4-20261025/session_01/`. Only
`authorization.template.json` exists; approval and operation flags are false.
The session binds source/image/helper/gate hashes and an append-only single-use
start record before invoking any controller tool. Its scope is:

1. Fresh service/listener/identity/fault/dump/session/idle guards; MANUAL
   normalization only if needed; original five-document preflight and fresh
   backup, with Save As/access audit.
2. Program/download/Run of the exact V6.7 ACD copy, with SDK/read-back/access
   audits and exact-image Capacity gate.
3. Five-document restore and the unchanged 31 genealogy candidate cases; then
   read-only migration value equivalence, generic acquisition, eight planned
   small groups × 100 qualifications, and native TASK scan measurement.
   The probe discovers its actual plan live; uncovered/oversize/invalid layouts
   refuse. Migration equivalence is evidence only, not the probe's read path.
4. After any download attempt, guarded genealogy rollback in `finally`. Open
   only a hash-checked copy of the immutable original. Preserve the candidate
   host medium, require original row values, and restore exact preflight host
   documents before baseline regression restoration.
5. Five-document restore, 31 baseline cases, MANUAL cleanup, final
   Run/not-faulted/scanning/idle/logged-out/not-restoring/document-equality
   checks and original-preflight verification. Fault/dump/session guards remain.

[AGENTS.md §3a](../../../AGENTS.md) requires **“current explicit authorization”**
for controller changes and states **“Prior authorization is historical and
shall not be inferred.”** The owner's contract choice does not approve these
new image/mode/mailbox operations. Current exact-image session approval is the
remaining S4a gate. Fault clears, clock changes, power operations, vendor-state
edits and hard kills are excluded.

## Remaining work and next step

**Next:** authorize and run the prepared S4a Echo qualification, restore
genealogy, seal results and decide from measured windows whether contract A is
viable before completing the desktop client. No test outcome is presumed.

- **S3 carryover:** real I/O module identity/offline proof on physical hardware;
  refresh the legacy consumer census before S6.
- **S4b:** EtherNet/IP transport, Symbol/Template wire discovery, manifest/logical
  snapshot assembly and complete logical goldens, worker isolate, demand/read
  tiers and active-workload coherence/liveness, read-only repository/UI state,
  factory routing, spike deletion and Echo desktop rendering acceptance.
- **S5:** shared Dart gateway, typed commands behind its existing write gate,
  installer/tray, browser command and restart acceptance. Owner must choose
  read-only or write-enabled for each station.
- **S6:** migrate harnesses, collapse legacy contexts/copies and observation
  frame, relocate persistence and host-event ownership, remove Python projection
  and gateway, complete capacity reductions and final binding documentation.
- **S7:** physical v37+ CIP Security-capable target, commissioned policy/TLS,
  direct writes and physical fit/scan/retention/security acceptance.

Owner decisions still pending: persistence medium after the S6 probe, gateway
write posture per station, S7 hardware and commit/push policy. The contract A
choice is recorded and no longer pending. V2 activation awaits all stage gates.

Payload: [manifest](AB_S4A_COHERENCE_PREPARATION_2026-10-25/manifest.json).
Prior sealed evidence is verified without modification. No credential fixture,
PIN or ACD/BAK binary is archived.
