# S3k option A command binding - offline gates pass

Client date: 2026-10-25, America/Mexico_City. This is an **offline
engineering slice** under the owner's approved
[remaining-S3 semantic contract](../AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md)
and the owner's choice of **A** in the
[command-binding review](../AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md)
(question `call_f17f50e248404825813327f8477a84f4:0`). That choice covered
offline work only. **S3k native acceptance has not run.** No download, mode
change, tag write, fault clear, clock change, power operation or hard kill
occurred. The restored genealogy baseline remains on Echo; fresh read-only
identity and preflight comparison pass. No commit or push.

## Scope and behavior

The [V6.6 wire draft](../AB_CANONICAL_PUBLICATION_S3K_WIRE_DRAFT_2026-10-25.md)
is implemented on the stage-13 profile. A typed payload Template carries three
DINT envelope fields (SchemaVersion, ManifestRevision, StagedSequence) and the
nine exact Core arguments: Kind, TargetPath (255), NameValue (160), TextValue
(255), User (32), Secret (32), IntValue, native BOOL BoolValue and UInt32-bit
DurationMs. A separately writable DINT commit follows it. The hashed
CommandBindings row publishes payload, commit, reply and status endpoints, a
4,000-byte connection, a 1,024-byte payload bound and read role `CommandOnly`.
CommandOperations publishes a disposition for every one of the 39 Core kinds.
Discovery merges the argument schema under Root/HmiRequest from Templates and
never reads payload bytes; the client encoder uses Template offsets, the BOOL
bit and Template attribute 1, with no station map.

The ingress snapshots both commit scalars, keeps independent last-seen values
and uses UInt32 serial arithmetic. First scan baselines visible commits.
Simultaneous legacy and typed commits are both consumed and refused. A stale
serial is refused without sampling its payload. A valid typed commit is
resolved on the PLC - module identities, configuration key and live revision,
strict DINT value text, force channel/value and live model code - and handed
to the released access/release owner, which acts once. Stale revisions and a
foreign root keep the owner's named refusals; unknown keys, modules, channels
and models resolve to no ordinal and are refused by name. The legacy Frame
writer keeps its encoding and its own acknowledgement; the typed reply is a
separate read-only record and carries the typed token.

Transport Secret and TextValue, including bytes beyond LEN, and the legacy
Frame words are wiped on every path - accepted, refused, malformed, stale and
colliding - before acknowledgement. Cyclic acquisition, the observation frame
and persisted captures never read the typed payload, its private sample, the
staged services or the reply. The set-service status is published only to a
logged-in session holding the config-set gate (taken from the access gate
table and bounded through the shared permission predicate), for the matching
accepted sequence and a bounded name; values appear only where readable.

This slice also tightened the earlier option A work: resolution failures that
previously all reported `command_payload_invalid` now keep their specific
reason, the refusal table is one generated function exercised for every arm,
the config-set gate is no longer a literal `11`, and generation refuses a
capability table too small for the set-status loop rather than emitting an
out-of-range index.

## Offline validation and exact artifacts

| Gate | Result / exact output |
|---|---|
| Full AB discovery, final unchanged code | **2,282 tests**, OK; `Command/ab_suite_01.log` and exit JSON |
| Root tests | **74 tests**, OK; `Command/root_tests_01.log` |
| AB spec / contracts / strict consistency / whitespace | Pass; `Command/ab_spec_01.log`, `ab_contracts_01.log`, `consistency_01.log`, `whitespace_01.log` |
| Both v38 targets | EchoController and PhysicalController build; zero import warnings/errors; SDK Open project, Build and Save As audited clean |
| Final source/native read-back | Equivalent on both targets; **67 executable bodies, 60,166 initial values**; `readback_*_01.log` |
| Effective access | Pass on both native exports; payload and commit are the only new writable tags, private scratch None, reply/status Read Only, no command storage observed |
| Offline ACD prepare/read-back | Pass; strict prepared read-back equivalent; SDK audit clean |
| Automatic Studio Capacity | **1,907,592 used / 1,238,136 available / 3,145,728 total Blocks**, **60% displayed**, verified fit; source unchanged |
| Capacity change | **+100,472** versus the read-surface slice; **+164,512** for S3k over accepted S3j, inside the capacity plan's +80 to +200 K band |
| Accepted image compatibility | **12 / 12** regenerate byte-identically; `accepted_images_01.json` |
| Archived native captures | **1,385 / 1,385** replay with exact historical schemas and values/types; `capture_replay_01.json` |
| Prior immutable evidence | All prior report, manifest and artifact hashes verified; `prior_seals_01.json` |
| Current baseline, read-only | Exact Echo identity/fault/keyswitch guard and `preflight.py --verify-only` pass |
| Native Template size, one-packet write, live requests, scan, retention | **Not run**; no S3k native authorization |
| HMI / Flutter | Not applicable; no HMI changes |

- Generated source `s3k_command_a_01.L5X` SHA-256: `426289A5E71CDEC1DBC5A4C5C7FBCDE4E706676B311362A12A91CFD36083EE78`.
- Offline ACD `command_a_01.ACD` SHA-256: `5B62CAC28C8EB5A819850D49FC854123C0B0B00449E2E8663FAC08B96C3000F6`. The byte-identical review
  copy was used for automatic Capacity. These pins identify engineering
  artifacts; they do not offer or authorize deployment.
- Source, both native exports and prepared read-back are archived compressed.
  No ACD/BAK binary or credential file is archived.

## Failures retained and corrected

The earlier option A work in `command_a_01/` is archived whole. Two scripted
integrations refused ambiguous anchors (`integrate_02`, `integrate_03`) and
changed nothing; `integrate_04` applied the corrected anchors. The first
focused run lacked the new owner-input fields in its fixture. Native build 01
refused a wide literal (`RxLsE_VALUE_OUT_OF_RANGE`) and build 02 an implicit
BOOL-to-DINT operand (`RxSTX_E_BOOLOPND_UNEXPECTED`); both were rewritten
(16-bit serial halves; explicit BOOL test) and build 03 passed. That build
predates the CommandOperations integration, so it does not bind this image.

In this slice, `full_ab_01` failed one test: the reply and set-status logic now
runs in the mailbox cyclic block, and that fixture typed the BOOL manifest
`Valid` as a DINT and lacked the set-status tags. The fixture now uses BOOL and
the shared set-status tags; the owning logic was unchanged by that fix. Suite
01 ran after every code change in this record.

Two harness slips changed no document or code. `finalize_docs_01` stopped
before writing because the suite log holds a console-code-page byte; `_02`
reads logs tolerantly. `write_report_01` ran an incomplete stub (archived as
`write_report_01_stub.py`) that wrote nothing, so `ab_spec_01`, `ab_contracts_01`,
`consistency_01` and `whitespace_01` ran before this record existed. They are
superseded by `write_report_02` and the `_03` gate runs after this text.

## Next step

A native S3k session for this exact image must prove inherited regressions,
up-to-24 release reasons, accepted/refused/stale/colliding typed and legacy
requests, the native Template size and one-packet encoding, secret wipe, exact
restoration, value/type equivalence and scan. It needs a current exact-image
owner authorization; none is requested or implied by this record.

S3 final still needs press ST/SFC/LD equivalence and real-module identity/offline
proof. S4-S7 and the later persistence, station write-posture, hardware and
commit/push decisions remain. V2 is inactive.

Work: `C:/work/fraktal-ab-s3k-20261025/`.
Append-only payload: [manifest](AB_S3K_COMMAND_BINDING_OFFLINE_2026-10-25/manifest.json).
The plan, inactive V2, S3k notes and wire draft record this status; their
before/after hashes and copies are archived.
