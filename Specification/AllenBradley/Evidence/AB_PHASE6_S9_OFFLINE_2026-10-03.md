# Phase 6 item 6 — S9 prepared offline, press68

The write-enabled S9 implementation and verification tools are prepared.
**This is offline evidence, not the native write-enabled claim.** Press67 stays
the verified loaded baseline. No controller I/O, tag write, download, mode
change, provisioning, gateway restart or client deployment occurred in this work.
The bench's recorded legacy v33/write-enabled decision is unchanged. The
machine-readable record is
[AB_PHASE6_S9_OFFLINE_2026-10-03.json](AB_PHASE6_S9_OFFLINE_2026-10-03.json).

## Artifacts and memory

| Artifact | Identity | Manifest |
|---|---|---|
| `C:\work\press68.L5X` | SHA-256 `E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7` | major 4; `7A9B9A8B59EEFD16` / 8035226; 68,472 bytes |
| `C:\work\phase6_s9_template.L5X` | SHA-256 `95BAE8768BB240E625D54BA5D31706FD733E012B098D1CC728BAA1F48C2C43E2` | major 4; `48F810ECD83FC78E` / 4782096; 58,232 bytes |

Both outputs reproduce byte-for-byte, including a final-source regeneration.
The seed is the existing empty v33 seed. The press uses Fields 565/640,
Localization 570/640, Rationalization 23/32 and WriteCapabilities 9/64. The
template uses Fields 379/448 and Localization 481/576. No extra manifest reserve
is allocated. AOIs, modules, tasks, private user registrations and access-state
defaults are equal to their respective baselines. The four-user ceiling stays;
three press registrations and one template registration are allocated.

| Growth over successful baseline | Press67 → press68 | Previous template → S9 template |
|---|---:|---:|
| Declared data bytes | +1,088 | +1,088 |
| ST source bytes | +4,119 | +4,002 |
| ST statement terminators | +63 | +63 |
| ST lines | +64 | +64 |
| Ladder rungs | 0 | 0 |

The native frame is three bounded 89-DINT arrays (transport, CPS sample and the
same-layout private login request) plus five scratch DINTs. Byte extraction is
one shared loop. Generated counts omit compiled instructions, AOI instance
storage and controller overhead; they do not prove free memory or fit. The SDK
probe on the new file again failed during `OpenLogixProjectAsync` with
**“No valid license”**, exit 3762504530, before opening or Verify. The owner must
Verify and complete linking/download in licensed Studio. Verify alone does not
advance the successful memory baseline.

## Native command profile and reconnect behavior

The public HMI request paths, ten logical members and TC3 operation ordinals stay.
Native `HmiRequestV3` appends frame schema 1 to the released prefix. Decoded
scalar/string arguments are private; frame and final Sequence form the native
command write surface. The pinned pylogix serializer's conservative 500-byte
rule derives 89 words and **312 aggregate ASCII argument bytes**, in addition to
each field's existing bound. The installed serializer emits one ordinary write
service; one extra word would force fragmentation under its chunking rule.
Large ConfigSet records retain their separate staging transaction.

The controller CPS-samples the complete frame after a new Sequence, validates
schema, matching sequence and individual/aggregate lengths before decoding,
then wipes transported and sampled words before acknowledgement. Corrupt or
premature commits are refused once; a late payload never self-executes. Existing
access, release, configuration and command handlers still own acceptance.
Every production/new-vector primitive native write checks the exact serial
immediately beforehand, including private ConfigSet staging.

The native profile contributes to ContentHash and BindingVersion becomes 2,
preventing the new writer from using an incompatible old downloaded contract.
Part III §7.7's earlier nonzero/skip-zero draft wording is corrected to the TC3
oracle: full uint32 bit patterns, including wrap to zero, stored as signed DINTs
and compared for inequality on the PLC. Both gateways reserve before I/O;
duplicates and backward/half-range sequences refuse. A fresh explicit request
may skip burned attempts. Native lagging/zero observations cannot reset the
replay guard. The AB gateway refuses a new frame while the previous committed
request lacks acknowledgement, and holds serialization until its worker has
finished even if the caller is cancelled. The HMI seeds from committed input
across wrap and may adopt a newer native observation without moving backward.

## Reader and shared HMI contract

The AB reader caches manifest rows only after matching leading/trailing headers,
including the complete live read between them. A connection drop clears that
cache. All viewers' slow/excluded sets intersect before changing the native
plan. Bounded fieldbus, profiler and access-audit groups support slow heartbeat,
exclusion and targeted promotion; any fast leaf keeps its whole native record
cyclic. Alarm-ring reads remain cyclic because that record also supplies active
and global diagnostics. This is native record granularity, not a claim that every
excluded leaf saves an independent CIP transaction.

Gateway server timestamps represent acquisition UTC. Cached groups retain their
acquisition timestamp; no controller/source UTC is invented. A failed forced
read invalidates cached Good state. Per-connection model-page overlays update
both value and metadata. An explicit HMI DataValue lacking a quality code is
Bad; the existing legacy scalar-only compatibility path remains.

The same repository suite runs on TC3 contract fixture paths and a production
AB projection/Gateway snapshot generated from native test fixtures. Its command
session is a fake PLC response, so this proves shared repository semantics, not
TC3 hardware or network behavior. Python tests separately execute the emitted
AB decoder/handler and production gateway with a scan after each primitive write.
The original `fraktal_ab_s9_execute.py` coherence fixture is retained intact.

## Verification

| Gate | Result |
|---|---|
| Full AB tool discovery, fresh unused bytecode prefix | **1,505 tests pass**, 209.920 s |
| Root consistency | **0 errors, 0 warnings** |
| Root consistency unit suite | **33 tests pass** |
| Explicit shared repository / reconnect / gateway / existing repository runner | **60 tests pass**, AB document supplied |
| Full Flutter suite | **448 pass, 7 skipped**; AB runner above supplies the otherwise skipped AB case |
| Flutter analyze | **No issues found** |
| Flutter release Web build | succeeds at `C:\work\press68_hmi_web`; not served |
| In-memory S9 mutations | **10/10 detected**; no source-file mutation or controller I/O |

Mutations remove schema/sequence checks, aggregate bounds, CPS, either frame
wipe, commit-last ordering, signed native mapping, reservation before I/O and
cache invalidation on failure. Normal tests cover login sampling/secret wiping,
signed-boundary and zero wrap, incomplete/reversed arguments, serial changes,
five replay boundaries, cancellation, native tier caching, coherent manifest
cache and the hardware vectors' restoration/failure paths. The new read-cost
vector's offline test proves exclusion really reduces native calls and targeted
reads/promotion restore them.

## Owner step and owed native evidence

Import `C:\work\press68.L5X`, Verify, and **complete the download**. Restart the
gateway from this source and report “done.” Native fit and controller state are
not inferred before that confirmation. The prepared HMI Web artifact will then
be served/reloaded within the authorized verification workflow.

Keep the owner's HMI idle while the exclusive supervised
`fraktal_ab_s9_write_execute.py --execute-fixture` runs. Its fixed vector changes
only session/timeout through the PLC mailbox, injects the five replay boundaries,
crosses the signed and uint32 limits, stages incomplete and reversed argument
segments, confirms consumed-frame wiping, and restores the original known
session/timeout in finally. Wrap/rejoin use bounded inert/timeout commands, never
private sequence-counter writes. All primitive writes retain exact target checks.
Regressions and S3 timing/restoration still need to pass on the downloaded build.

`fraktal_ab_s9_read_execute.py` is read-only. It measures cold/steady native
reads, excluded/slow/targeted profiler cost and six viewers sharing one gateway
reader. Current-station freshness thresholds and poll budgets remain to be
declared against these measurements. Phase 0's historical 100 ms budget is not
transferred to the expanded press. **Write-enabled S9, native fit and physical
retention remain owed.**
