# S3k engineering notes - mailbox, reports and remaining Unit fields

Non-normative working notes, 2026-10-25. The semantic contract is already
owner-approved in the [remaining-S3 review](AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md).
S3k is in progress: read surfaces, the versioned report owner and R4 compile
offline. Command binding awaits the [A/B owner choice](AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md).
No S3k controller operation is authorized or performed. The restored genealogy
baseline remains loaded; read-only identity/preflight checks pass. No commit or push.

## Inventory and implemented read surfaces

The approved inventory's stage labels select exactly **133 frozen paths**:
126 mailbox/report, five production fields and two Features flags. Of the 126,
122 describe the complete 24-slot release report, three the response and one
the request Sequence. Nine additional Core request arguments are discovery
surface, not cyclic process values. There are 39 Core operation ordinals,
including NONE=0. Supported/refused operations remain declaration-dependent.

The stage-13 engineering profile publishes those 133 paths with Core widths,
UInt32 counter/sequence bits, shared derived Starved/Blocked conditions and
native BOOL Features flags. A safe input tap supplies only request Sequence.
The report renderer resolves portable keys/source identities through shared
PLC text, updates on acknowledgement, clears all unused rows, publishes ACK
last, and invalidates corrupt or overflowed reports. Its invalid state stays
latched until a new response; unknown diagnostics preserve the legacy key and
signed-number fallback. Full request arguments are not yet published.

The independent S3k oracle extends the accepted S3j reference by the exact
133-path inventory. It reads only safe request Sequence, response/report and
existing approved inputs; it never samples Frame, Secret or staged credentials.

## Reports and R4

The private V2 report owner derives capacity from Core MAX_RELEASE_REASONS=24.
Earlier profiles retain their released eight-entry owner. All append/open/
close/copy emitters receive the declaration. The new owner marks Overflow,
refuses invalid indices without array access and cannot release an incomplete
report. Generation checks reachable Start-report completeness against 24.

R4 replaces repeated manual-command CASE routing with generated module/command
tables and one bounded dispatcher. Cache the exact Busy and directional permit
facts **inside the mailbox handler, after its session/data/config prologue and
immediately before dispatch**. Accepted intent is applied automatically in the
existing generated module scan path, preserving same-scan Execute drop and
ManualCmd behavior. No project call is added. Missing permits retain the
existing device HELD behavior rather than adding a stricter action gate.

## Command ABI decision remains open

The earlier engineering idea of aliasing the entire legacy request into the
canonical request is not selected. The existing request embeds staged services;
its declared-size tally is 9,448 bytes, not a measured native Template size.
It cannot simply be written whole under the current unfragmented-payload rule.

The [concrete review](AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md)
asks the owner to choose A: a compact typed Core payload, PLC routing, one owner
and temporary legacy Frame adapter; or B: the frozen Frame ingress with fully
PLC-published generic encoding/lookup metadata. No dependent command binding
is implemented while this required choice is pending. Core BoolValue must be
a genuine BOOL; the old overloaded private DINT cannot be relabelled.

ConfigSet/ConfigProvider extensions must remain discoverable and validated
until their S6 replacement owners exist. Generic cyclic acquisition must never
sample command payloads. Secret exclusion must cover uncommitted bytes and
bytes beyond LEN before any readable frame or persisted capture exists.
The safe Sequence tap is not qualification of that complete command policy.
There must be one dispatcher, bounded snapshot/commit ordering, explicit
competing-ingress refusal, and no reconnect replay. Full operation/service
inventory and boundary proofs remain mandatory.

## Completed offline gates

Work: `C:/work/fraktal-ab-s3k-20261025/`, especially `read_surface_01/`.
Evidence: [offline record](Evidence/AB_S3K_READ_SURFACES_OFFLINE_2026-10-25.md).

- **2,264 AB tests** pass; **74 root tests**, spec/contracts and strict
  consistency gates pass. Executed model tests cover all 24 reasons, overflow,
  invalid indices, ACK clearing/caching, signed fallback, counter bit patterns,
  corrupt descriptors and released/new manual action/report equivalence.
- Generated read-surface source `ADA479AC...01FD515` compiles on both v38
  EchoController and PhysicalController targets with zero import warnings/
  errors. Strict read-back matches 64 bodies and 58,314 initial values; native
  effective-access audits pass. The generated inert owner probe also passes.
- Offline ACD `CB180CDD...6F0ED6` opens, builds, saves, reopens and reads back
  equivalently. It is an incomplete engineering image, not a deployment offer.
- Automatic Studio Capacity: **1,807,120 used / 1,338,608 available / 3,145,728
  total Blocks**, **57% displayed**, +64,040 versus accepted S3j. No S3k scan
  measurement has been made; its controller runtime is unaccepted.
- All **12 accepted image pins** regenerate byte-identically. All **1,385
  archived captures** replay with their exact historical schemas/rules.
- Failed development checks and the build-driver comparison of a stale export
  are preserved. Correct final source/export pairs pass; an intermediate full
  suite whose source changed is explicitly superseded by suite 02.

## Next and remaining gates

Resolve the A/B ABI choice, freeze its detailed wire/state table, implement
command discovery/owner integration and prove secret exclusion and all service
bindings. Then run the complete S3k offline gates on the full image, measure
Capacity and prepare native report/request regressions with exact restoration.
Only after that can a current, exact-image authorization request be made for
the guarded native session, inherited regressions, value/type equivalence and
scan measurement. This partial image is not authorized for download.

S3 final also needs press ST/SFC/LD equivalence and real-module identity/offline
proof. S4-S7, physical/security acceptance and the later persistence, station
write-posture, hardware and commit/push decisions remain open. V2 stays inactive.
