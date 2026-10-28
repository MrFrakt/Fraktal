# S3k read surfaces and R4 - offline gates pass; command ABI decision pending

Client date: 2026-10-25, America/Mexico_City. This is an **incomplete offline
engineering slice**, under the owner's approved
[remaining-S3 semantic contract](../AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md).
It implements the 133 frozen read paths, versioned 24-reason owner and R4
table-driven manual dispatcher. **S3k native acceptance has not run.**
No S3k download, mode change, tag write, fault clear, clock change, power
operation or hard kill occurred. The restored genealogy baseline remains on
Echo; fresh read-only identity and preflight comparison pass. No commit or push.

## Scope and behavior

The stage-13 profile extends S3j's native typed tree by exactly **133 frozen
paths**: 126 mailbox/report, five production fields and two Features flags.
Of the 126, 122 describe the complete 24-slot Core release report, three the
response and one request Sequence. The oracle adds exactly this inventory,
retaining Core UInt32 bit patterns, native BOOLs and Int16 report Count.
Starved/Blocked reuse the existing machine wait conditions. Features derive
from declared capabilities, rather than constant client assumptions.

The response renderer resolves key/source identities through PLC-published
text, publishes ACK last, clears unused rows and caches only a complete
response. Invalid counts, Overflow or corrupt source indices invalidate the
frame; that invalid state remains latched until another ACK. Known diagnostic
keys resolve exactly; unknown keys retain the legacy fallback including signed
MIN_DINT formatting. The oracle reads only a safe request Sequence tap and
response/report facts. It never reads command payloads, Frame or credentials.

The new private report owner is versioned V2 with **24 reasons**, derived from
Core MAX_RELEASE_REASONS. Earlier profiles keep eight entries and regenerate
unchanged. Overflow cannot produce Released. Invalid indices never reach an
array access, and generation bounds the reachable Start-report conditions.

R4 uses generated module/command tables and a common bounded dispatcher.
Its Busy/permit cache runs inside the mailbox handler **after the session,
data and configuration prologue, immediately before dispatch**. Accepted
intent is applied automatically in each existing generated module path,
preserving same-scan Execute drop and ManualCmd assignment. Project code adds
no correctness call. Missing directional permits keep the released device's
HELD behavior; the action gate is not strengthened by a release query.

## Offline validation and exact artifacts

| Gate | Result / exact output |
|---|---|
| Full AB discovery, final unchanged code | **2,264 tests**, OK, 367.996 s; `ReadSurface/ab_suite_02.log` and exit JSON |
| Root tests | **74 tests**, OK; `ReadSurface/root_tests_02.log` |
| AB spec / contracts / strict consistency / whitespace | Pass; corresponding `*_02.log`, `whitespace_03.log` and exit JSON |
| Both v38 targets | EchoController and PhysicalController compile; zero import warnings/errors; SDK Open project, Build and Save As audited clean |
| Final source/native read-back | Equivalent on both targets; **64 bodies, 58,314 initial values**, 21-step SFC; `readback_*_03.log` |
| Effective access | Pass on both final native exports; safe Sequence tap Read Only, private scratch None, legacy validated endpoints retain access |
| Offline ACD open/build/save/reopen/build/export | Pass; strict prepared read-back equivalent; SDK audit clean |
| Automatic Studio Capacity | **1,807,120 used / 1,338,608 available / 3,145,728 total Blocks**, **57% displayed**, verified fit; source unchanged |
| Capacity change from accepted S3j | **+64,040 Blocks**; compares offline Studio measurements on this same target |
| Accepted image compatibility | **12 / 12** regenerate byte-identically; `accepted_images_01.json` |
| Archived native captures | **1,385 / 1,385** replay, exact historical schemas and values/types; `capture_replay_01.json` |
| Prior immutable evidence | All prior report, manifest and artifact hashes verified; `prior_seals_01.json` |
| Current baseline, read-only | Exact Echo identity/fault/keyswitch guard and `preflight.py --verify-only` pass |
| S3k live equivalence, native report/request cases, scan and retention | **Not run**; command slice incomplete, no S3k native authorization |
| HMI / Flutter | Not applicable; no HMI changes |

Executed model tests include ninth and twenty-fourth reasons, invalid negative/
large indices, overflow/reset, descriptor corruption, action/report equivalence
with the released dispatcher, unknown diagnostic formatting, unused-row clearing,
ACK cache ordering and counter/wait behavior. These are offline proofs; no live
S3k report, ordering, secret or timing claim follows from them.

- Generated source `s3k_read_surface_02.L5X` SHA-256:
  `ADA479ACA4305DD07E512ABDDC16446E9FDB220562A641FC0E6F026C201FD515`.
- Incomplete offline ACD `read_surface_01.ACD` SHA-256:
  `CB180CDD8F6ED31380C3D288B13FA746313BC8A5E1F1677CBF3630FEAF6F0ED6`.
  The byte-identical review copy was used for automatic Capacity. These pins
  identify engineering artifacts; they do not offer or authorize deployment.
- Source, both native exports and prepared read-back are archived compressed.
  No ACD/BAK binary or credential file is archived.

## Failures retained and corrected

Early inventory scripts misread the approved JSON structure; all failed runs
remain under `Inventory`. A report test initially constructed an unsupported
Member argument. Dispatcher comparisons initially compared generated numeric
key IDs across different manifests; the corrected test compares portable
keys. Renderer tests exposed a missing fixture counter and an invalid attempt
to cache an App containing unhashable dictionaries. Those were corrected;
no App-keyed cache remains. Initial stage-13 generation also hit the
sampled-word fixture's stage-12-only restriction; the same fixture now explicitly
accepts stages 12 and 13.

The initial R4 cache placement preceded the mailbox's configuration prologue.
It was moved inside the mailbox before CASE, so asynchronous configuration
changes cannot leave its permit facts one scan old. Final source 02, both final
native exports, full suite 02 and the prepared ACD bind that correction.

The build driver compiled Echo source 02 correctly but then compared the old
source-01 export. `build_image_02` and `readback_EchoController_02` therefore
fail and remain preserved. `readback_path_diagnosis_01.json` records the stale
file path. The corrected driver compares native export 02, builds physical
export 02 and passes strict comparisons 03 on both targets. The first full
suite overlapped the cache correction and is explicitly not the final code
gate; suite 02 ran after that correction. Failed attempts were not overwritten.

Plain `git diff --check` flags the existing CRLF tool style as whitespace.
The final check uses the established `core.whitespace=cr-at-eol` setting;
working documents retain their original LF style. The plain-check failure
and document newline correction are also preserved; PLC code was not rewritten.

## Pending decision and next step

The [command-binding review](../AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md)
awaits the owner's A/B choice. A is the recommended compact typed Core payload,
PLC-side routing and a temporary legacy Frame adapter feeding one owner.
B retains the frozen Frame ingress and publishes all generic encoding/lookup
metadata. The existing request embeds staged services and has a declared-size
tally of 9,448 bytes; it cannot simply become one unfragmented command write.
The tally is not a newly measured native Template size. The earlier idea of
aliasing the whole legacy request is not selected.

The nine additional Core command arguments, full operation/service discovery,
typed transport binding, owner/adapter state table and secret exclusion are
**not yet implemented or qualified**. Generic acquisition must not sample
credential-bearing values; committed and uncommitted bytes, including bytes
beyond LEN, must be excluded before any readable observation/persisted capture.
This safe read-surface slice alone does not close that requirement.

After the choice: implement and prove the chosen binding, repeat the full-image
offline gates and Capacity, then prepare a current exact-image native session
for owner authorization. That session must prove inherited regressions,
up-to-24 release reasons, accepted/refused/stale/ordered requests, secret wipe,
exact restoration, value/type equivalence and scan. No authorization is requested
for this incomplete image. The semantic approval remains in force.

S3 final still needs press ST/SFC/LD equivalence and real-module identity/offline
proof. S4 generic desktop client and row coherence, S5 Dart gateway/installer,
S6 retirement/persistence/event ownership and S7 physical/CIP Security remain.
V2 is inactive. Later owner decisions remain persistence medium after the S6
probe, gateway station write postures, S7 hardware and commit/push policy.

Work: `C:/work/fraktal-ab-s3k-20261025/`.
Append-only payload: [manifest](AB_S3K_READ_SURFACES_OFFLINE_2026-10-25/manifest.json).
The plan, inactive V2 and S3k engineering notes record this partial status;
before/after document hashes and copies are archived. All prior sealed evidence
and the owner's unrelated Siemens archive edits are preserved.
