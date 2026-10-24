# AB S3c sequence publication — runtime acceptance, 2026-10-22

**S3c passes at its 647-path genealogy subset on local Echo 601FC87B.**
Candidate and restored-baseline fixtures pass 31/31 each on their first runs.
Four decision pairs, 14 held/fault pairs and 21 sequence pairs match every
value/type under the unchanged whole-scan proof. Genealogy is restored and
the corrected final checks verify actual MANUAL=1/idle, logged out, Run,
not faulted, scanning and all five saved documents equal live.

See [preparation](AB_S3C_CANONICAL_PREPARATION_2026-10-22.md),
[scope notes](../AB_CANONICAL_PUBLICATION_S3C_NOTES_2026-10-22.md),
[inventory](../AB_CANONICAL_PUBLICATION_S3C_INVENTORY_2026-10-22.json),
[wire draft](../AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md) and
[payload hashes](AB_S3C_CANONICAL_RUNTIME_2026-10-22/manifest.json).
Date follows the client's America/Mexico_City date. Source commit is
`a1163c7c7bec21988167bc971145b1366206e9ce` plus uncommitted work. Shipping
Part III/V1 remain authoritative and V2 remains inactive. No commit or push.

## Authorized session and artifacts

The owner answered **“Approve this guarded S3c session”**, explicitly including
the MANUAL correction, fresh backup, Program/download/Run of the prepared pin,
five-document restore and candidate regressions/captures, idle/scan reads,
genealogy rollback, document restore and baseline regressions, and final
MANUAL normalization/checks. Fault clearing and clock changes were excluded.
This approval is consumed by the completed session; it grants no future image
or new session authorization.

Preparation work:
`C:/work/fraktal-ab-s3c-20261022/prepare_147ef60398974c44abf7b2959b2d813f/`.
Runtime work:
`C:/work/fraktal-ab-s3c-20261022/runtime_54dacf3ba2dd4ecbbb8dcc7bcad6a038/`.

| Artifact | SHA-256 |
|---|---|
| Generated S3c L5X | E58BB88F9E63BE9144AF90C4032714F9B44B167CA02E2B2A64C933788F4E70A2 |
| Original prepared candidate pin | A255918860C3062D8F0DF3FA4E70373EF84372DDB3214E050AF23A08A0C2286C |
| Fresh controller backup | 848BC099CE613B99FE5B88D15C53764E2CF6974146D9155206BA493550A09988 |
| SDK-saved candidate after download | CE52EB2EA19C764561DF511D70BEEA1092B99BE8CD9BBC2970D269ACE3A3EA9B |
| SDK-saved rollback copy | 0BD558104C11EFE0094F8D133E2E71D261924597C5437B60F6EB380070F8003C |
| Immutable genealogy original, unchanged | D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084 |

All 247 preparation artifacts, its report and 64 source bindings verified
before the first controller operation. Service, 44818 listener process,
identity, fault/keyswitch and active-session guards passed. The original
preflight was recorded once after approved MANUAL normalization and verified
before backup/download and again after final restoration. Every SDK log is
audited; upload is labelled “Open Project From Controller,” so backup audits
require successful Save and Save As. No ACD binary or credential contents are
archived. The immutable genealogy original was hashed and copied, never opened
by SDK/Studio; only its checked copy was downloaded.

Both candidate and restored exports pass strict read-back. Candidate comparison
covers 95 UDTs, seven AOIs, 130 tags, one program/task, 45 executable bodies,
the 21-step SFC graph and all 26,230 authored initial values. Its access audit
covers all 130 tags and 37 canonical types. Restored genealogy matches the
sealed genealogy source and all 109 tag/access pairs exactly.

## Equivalence and regression coverage

The subset is 304 accepted S3b paths plus 343 sequence/current-step paths.
The PLC Chart still owns visits, durations and marks; no client accumulates
history from polls. V6.2 binds the separate definition record to the discovered
root. Live FragmentRevision changes invalidate cached definition values.
The generic reader discovers seven modules and 647 leaves without importing
a station declaration or deriving step text/recipes itself.

The candidate passes 31 inherited regression rows, four active decisions,
ten held captures and four Unit first-out fault captures. The latter cover
held/fault state across rendition ordinals 0/1/2. Twenty-one sequence captures
cover seven cases in each of ST/SFC/LD: OK, handled_NOK, HELD_resume, abort,
mode_change, adopted_fault and single_reset_restart. Mode changes clear the
chart, handled failures retain sparse warning notes, and completed steps
shorter than 100 ms remain visited after execution in every rendition.

Idle equivalence and an independent generic capture also pass. All **40 paired
captures**, including idle, re-decode to exactly their recorded native
snapshots and legacy inputs; the independent oracle reproduces every value
and type. The generic capture replays identically. The only path corrections
are the approved D2 bounds applicable to this subset.

The equal-even whole-scan generation proof, 100 attempts and five-second
budget are unchanged. Accepted captures use 1–6 attempts: 21 need one,
18 need two and one needs six. Observation uses a separate 4,000-byte
connection; existing mailbox framing remains 500 bytes. No PLC, reader or
fixture source changed during this runtime session.

The original genealogy fixture then passes another 31 rows and restores its
policy/configuration. There are **62 actual regression rows, zero extra rows**.
The approved MANUAL helper performs three LOGIN/SET_MODE(1)/LOGOUT sequences
(nine additional mailbox commands), before preflight and after each fixture's
AUTO cleanup. It changes no policy, clock or simulation stimulus. Individual
tag-write call totals were not instrumented; command sequences are recorded
without claiming a measured per-tag total.

## Capacity and native scan

The exact pinned offline Studio measurement from preparation remains:
**1,107,552 used / 2,038,176 available / 3,145,728 total Blocks**, displayed
35%, **+115,940 Blocks** over S3b. Blocks are not assumed bytes. Two stable
samples, source preservation, Offline identity and review-process closure
passed the qualified driver/normalizer. No screenshot was requested. This is
an offline Capacity estimate, not measured online memory.

The four-sample held-out forecast was 1,114,908, error +7,356 (+0.6642%), with
planning budget 1,338,899. After acceptance, the current observation catalog
adds S3c as its fifth hash-bound sample. The original held-out catalog/output
remain sealed; no forecast error guarantee is claimed.

| Observation | LastScanTime median/range (µs) | Cumulative MaxScanTime (µs) | Overlaps |
|---|---:|---:|---:|
| Prior accepted S3b | 123 / 122–123 | 1,190 | 0 |
| S3c candidate, 20 samples | 200 / 200–201 | 1,600 | 0 |
| Restored genealogy, 20 samples | 99 / 99–100 | 1,167 | 0 |

Native values come from PLC GSV TASK measurements; the candidate's publication
and legacy health observations agree. MaxScanTime is cumulative since task
reset and includes earlier workload. S3c adds 21 sequence captures while S3b
had disclosed failed/retried fixtures, so these are observations, not an
isolated publication-cost measurement. No clock was set or synchronization
invented; prior timestamp semantics remain unchanged.

## Corrected readiness and retained failed audit

Earlier work scripts labelled Mode 0 MANUAL. The declaration defines AUTO=0,
MANUAL=1. The preparation finding and older sealed reports remain intact.
Under current approval the corrected guards now verify actual MANUAL=1.
Final policy and original preflight compare exactly; the Unit is idle,
logged out, not restoring and scanning, with all five documents equal live.
Native inspect confirms Run, not faulted and Remote keyswitch.

The initial backup access audit mistakenly reused the canonical-image
allow-list against legacy genealogy, requiring four absent canonical tags.
It failed and stopped deployment. The corrected work audit takes its policy
from the hash-bound sealed genealogy source and requires exact tag/access
equality. All 109 entries pass before deployment and again after rollback.
The first audit, its code, output and failure exit remain in the payload.
No controller access rule or acceptance requirement was relaxed. No regression
or equivalence run failed in this session.

## Verification and boundary

The unchanged 64 source bindings retain the preparation's **2,052 passing AB
tests (271.430 s)** and both v38 offline compiler/read-back gates. They were
not rerun without source changes. Fresh runtime audits cover downloaded
read-backs/access, all captured native bytes/oracle values, fixture results,
readiness, pins and fifth Capacity observation. Root/spec/contracts/strict
consistency, focused Capacity checks and whitespace gates are recorded in the
payload. All twelve predecessor canonical seals / 1,795 artifacts verify
unchanged. No HMI source changes were made; Flutter gates do not apply.

Fresh outputs:

- Root suite: `Ran 74 tests in 1.905s` / `OK`.
- Capacity tests: `Ran 11 tests in 0.110s` / `OK`.
- Spec: `Fraktal/AB specification gate: clean.`
- Contracts: `Fraktal/AB frozen-contract gate: clean.`
- Strict consistency: `0 error(s), 0 warning(s)` across inventory,
  localization, parity and readsurface.
- Whitespace: exit 0 with CR-at-EOL configuration.

The fixture has no EM or concurrent branch. Its 21 annotation slots preserve
the oracle above Core's default 16. Existing missing Core fields and the
legacy false ErrorActive/cursor TimedOut semantics remain explicit in the
scope notes. No full-Core, physical-controller, CIP Security or HMI acceptance
is claimed. Later surfaces and shipping activation remain open. **S3d
(AlarmLog and StateFlags) is next.**
