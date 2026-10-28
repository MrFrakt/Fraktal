# S3k engineering notes - mailbox, reports and remaining Unit fields

Non-normative working notes, 2026-10-25. The semantic contract is already
owner-approved in the [remaining-S3 review](AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md).
S3k genealogy runtime acceptance **passes**: read surfaces, the versioned report
owner, R4 and the owner-chosen option A
[command binding](AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md)
pass 41 inherited and 14 typed/interleaving check rows on `AA4239C6…1653BBDF`.
PIN login completes, transport wiping and independent ACKs pass, and both
colliding commits are refused without replay. All 91 pairs replay exact values/
types; generic acquisition returns 4,428 values/seven modules/nine arguments.
Capacity is 60%; maximum native scan is 8,969 us with zero overlaps. Genealogy
and original host documents are restored; 31 baseline and final/preflight checks
pass. Current authorization is consumed. The full S3 declaration/rendition exit
and S4–S7 remain; V2 inactive; no commit/push. See the
[accepted runtime scope](Evidence/AB_S3K_CANONICAL_RUNTIME_2026-10-25.md).

Earlier, the authorized revision retry restored all five documents and
passes two Access/eight configuration cases. Twelve typed ACK/wipe rows are
recorded, but the login completion wait fails. Main 31 rows, legacy-after-typed,
collision and post-case scan remain unrun. All 39 pairs independently replay.
Genealogy and its original five host documents are restored; 31 baseline cases
and all final/preflight checks pass. Current authorization is consumed. An
offline synthetic reproduction confirms a private login snapshot uses the
legacy Sequence instead of the typed owner token. See the
[latest runtime record](Evidence/AB_S3K_CANONICAL_REVISION_RETRY_RUNTIME_2026-10-25.md).

The private login snapshot is now corrected offline to use the shared committed
owner token. Three coupled tests, 2,295 AB/74 root tests, both v38 builds/read-
backs/access, 12 earlier image pins and 1,431 archived capture replays pass.
Only `FRK_PressHmiMailbox` changes; all types and initializers remain equal.
Prepared ACD `AA4239C6…1653BBDF` measures 1,903,344 used / 1,242,384 available /
3,145,728 total Blocks (60%, +36 Blocks). It is not downloaded. The unapproved
retry restores exact original host documents before the genealogy baseline
fixture. See [login retry preparation](Evidence/AB_S3K_CANONICAL_LOGIN_RETRY_PREPARATION_2026-10-25.md).

The earlier authorized request walk stopped at live-document restore:
two Access cases/five pairs pass; the main regressions and typed vectors were
not reached. The unchanged-schema documents' prior publication revision is
not recognized by S3k. Genealogy is restored, with 31 baseline cases and all
final/preflight checks passing. Current authorization is consumed. Native S3k
acceptance remains open; no commit or push. See the
[attempt/rollback record](Evidence/AB_S3K_CANONICAL_ATTEMPT_2026-10-25.md).

The correction now passes offline: the shared set validator derives the exact
stage-12 publication revision from the same declaration, preserving every
other configuration validator. A short existing scratch operand avoids the
native compiler's operand-length limit. Only `FRK_Press_ConfigSets` changes;
data types and controller tag initializers are identical. Both v38 builds/read-
backs/access audits, 2,292 AB/74 root tests, 12 image pins and 1,385 prior capture
replays pass. Corrected ACD `12211B81…45995D9` measures 1,903,308 used /
1,242,420 available / 3,145,728 total Blocks (60%). It has not been downloaded.
The combined request/rollback retry is prepared behind current exact-image
authorization; genealogy remains loaded. See
[retry preparation](Evidence/AB_S3K_CANONICAL_REVISION_RETRY_PREPARATION_2026-10-25.md).

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
signed-number fallback. All nine request arguments have command-only discovery
metadata; only Sequence joins the cyclic process snapshot.

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

## Command binding - option A implemented offline

The owner chose **A** (question `call_f17f50e248404825813327f8477a84f4:0`):
a compact typed Core payload, PLC-side routing, one owner and a temporary
legacy Frame adapter. The [V6.6 wire draft](AB_CANONICAL_PUBLICATION_S3K_WIRE_DRAFT_2026-10-25.md)
holds the endpoint, commit/acknowledgement and refusal tables. The choice is
not a download authorization and does not enable a station's gateway writes.

The payload Template carries three DINT envelope fields and the nine exact Core
arguments: string widths 255/160/255/32/32, native BOOL BoolValue and UInt32
DurationMs bits. A separately writable DINT commit follows the payload write.
A hashed CommandBindings row publishes every endpoint, the 4,000-byte
connection and 1,024-byte payload bounds, and the read role `CommandOnly`;
CommandOperations publishes a disposition for all 39 Core kinds. The client
encoder uses Template offsets and attribute 1 only, never a station map.

The PLC resolves module identities, configuration keys and revision, force
channels and values, and live model codes from its own generated facts, then
calls the released access/release owner once. Stale revisions and foreign
roots keep the owner's named refusals; unknown keys, modules, channels and
models resolve to no ordinal and are refused by name. A strict DINT parser
accepts only full integral text. Simultaneous legacy and typed commits are both
consumed and refused; a stale serial is refused without sampling its payload.
First scan baselines visible commits. Transport Secret/TextValue bytes,
including those beyond LEN, are wiped on every path before acknowledgement.

The set-service status is published only to a logged-in session holding the
config-set gate, for the matching accepted sequence and a bounded name; values
appear only where the data class is readable. Cyclic acquisition, the
observation frame and persisted captures never read the typed payload, its
private sample, the staged services or the on-demand reply.

ConfigSet/ConfigProvider staging and the legacy Frame/Sequence ingress remain
discoverable until their S6 replacements. Their native writers keep the
released encoding and their own acknowledgement.

## Completed offline gates

Work: `C:/work/fraktal-ab-s3k-20261025/`, especially `read_surface_01/` and
`command_a_02/`. Evidence: [read surfaces](Evidence/AB_S3K_READ_SURFACES_OFFLINE_2026-10-25.md)
and [command binding](Evidence/AB_S3K_COMMAND_BINDING_OFFLINE_2026-10-25.md).

Option A, on the full image:

- **2,282 AB tests** and **74 root tests** pass; AB spec/contracts, strict
  consistency and whitespace gates pass. Executed model tests cover serial wrap,
  collisions, first-scan baselines, envelope/length refusal, every refusal arm,
  DINT parser bounds, PLC-side key/revision/model resolution, full-width wipes
  on every path and the set-service status conditions.
- Source `426289A5...6083EE78` compiles on both v38 targets and reads back
  strictly equivalent (67 bodies, 60,166 initial values); effective access
  passes, the typed payload and commit are the only new writable tags and no
  command storage is observed.
- Offline ACD `5B62CAC2...3000F6` prepares and reads back equivalently.
  Automatic Studio Capacity: **1,907,592 used / 1,238,136 available / 3,145,728
  Blocks**, **60% displayed**: +100,472 versus the read-surface slice and
  +164,512 for S3k over accepted S3j, inside the plan's +80 to +200 K band.
- All **12 accepted image pins** regenerate byte-identically and all
  **1,385 archived captures** replay.

Read surfaces alone:

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

Prepare the native S3k session for this exact image: inherited regressions,
up-to-24 release reasons, accepted/refused/stale/colliding typed and legacy
requests, native Template size and one-packet encoding, secret wipe, exact
restoration, value/type equivalence and scan. A current exact-image owner
authorization is required first; this offline image is not authorized for
download and no authorization is requested by these notes.

S3 final also needs press ST/SFC/LD equivalence and real-module identity/offline
proof. S4-S7, physical/security acceptance and the later persistence, station
write-posture, hardware and commit/push decisions remain open. V2 stays inactive.
