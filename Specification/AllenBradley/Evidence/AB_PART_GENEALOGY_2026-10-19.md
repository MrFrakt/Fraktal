# Confirmed Part genealogy and read-only gateway recovery — 2026-10-19

The local Part provider now supports bounded consumed-component genealogy.
Confirmation batches are atomic, repeated UIDs are idempotent, result write-back
precedes PROCESSED, and historical Part events retain their own parent sets.
The shared HMI renders current parents across AB/TC3 array layouts. A disposable
read-only gateway also passes forced process termination and reconnect against
the live Echo, preserving 260 Part/host-history values.

Evidence, source bindings, native hashes and logs:
[`AB_PART_GENEALOGY_2026-10-19/manifest.json`](AB_PART_GENEALOGY_2026-10-19/manifest.json).
Baseline commit: `21acd6fc900203635831e3d81e27194d5da3aa31`.
Preparation began October 18; download and final acceptance completed October 19.
Earlier dated evidence remains unchanged.

## Target and authorization

The owner's standing statement **“simulated plc is available for you to download
anytime”** authorizes this local replacement. The current text-resource image was
uploaded/saved before download, and all five configuration documents matched
the saved medium. The Unit was MANUAL/idle and logged out. Exact local
serial/product/revision/listener guards preceded mode changes and download:
`127.0.0.1`, slot 0, Emulate 5580 product 288, firmware 38.011, serial `601FC87B`.
Final inspection confirms `FraktalPhase0`, GUID
`91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`, Run and fault-free.

The new declaration is `fraktal_ab_genealogy_demo`, manifest major 5, content
hash `6DEC4C1DC2F7F78A`, configuration revision 7203916. Generated source:
`C:/work/fraktal-ab-genealogy-20261018/genealogy_01.L5X`, SHA-256
`91BF67C9101EAE863CF29C1A9DF6413D7256AB056D985394587F0183AA525714`.
Prepared ACD SHA-256:
`0B799CF5B53B7C8421875DCDCCB051F1C29896F95426060E347A34C9D79F46D3`.
Download-correlated ACD SHA-256:
`759ED22FA5255647B7BAD71CD5906202AF87DDD454A8D7C8F0BD78B87CAFE621`.
Pre-download backup ACD SHA-256:
`61163F2F91A37FC4C0DEA7E22EAA6B03760DB76A5FBAD054824728475020D64D`.
Full native files remain local; their references/hashes and actual read-back
reports are archived. Credentials are not archived.

No fault clear, physical-controller operation, clock/PTP setting, Echo scaling,
network change or electrical output operation occurred. The controller clock
remains unsynchronized; this does not qualify clock replay or UID uniqueness
across arbitrary clock/download replay.

## Implementation and overlap review

`LocalCarrier.genealogy_capacity` defaults to zero. An opted-in 1..8 capacity
requires an actual confirmed-parent consumer. `Step.part_parents` supplies a
tuple of `AsciiSource` literals or exact declared DINT ASCII-array operands at
an existing non-terminal MARK. The descriptor also backs the compatible
`ResourceText` alias; validation/capture logic is shared rather than duplicated.
Parent UIDs are 1..64 printable ASCII bytes. Shorter values have a zero tail;
full-width 64-byte values are supported.

The existing Part service validates the entire batch before changing the Part.
Empty/control/non-ASCII IDs, nonzero tails, self-reference and overflow fault
with `RESULT_RECORD_REJECTED`; no partial parent append or result count occurs.
Repeating an existing UID or a UID within the same batch confirms it once in
first-confirmation order. Parent-only MARK failure blocks transitions in all
three languages, including the native SFC condition. Failed Part work also
prevents a resource confirmation on that MARK.

Part V2 and its private provider get new capacity/version names. Result commit
copies parents before verdict counters and the PROCESSED append. Each new
receive clears the live parent set; completed results retain their parents
while idle. Aborts capture confirmed context without committing success.
No new canonical Part event kind is introduced.

Physical HostEvents V5 captures parents at each Part lifecycle boundary through
the existing single append owner. Its names encode genealogy capacity and text
presence (`V5T0G<n>` / `V5T1G<n>`); genealogy-only applications allocate no text
buffers. Sixteen packed DINT words hold each retained parent UID. Non-Part
events clear parent storage. Strict readers refuse malformed bounds, bytes,
padding, duplicates, self-reference and inappropriate parent fields.
Historical events are never joined to later live state.

The generic HMI reads the published array extent, including native TF6100
layouts, and shows selectable parent UIDs. It accumulates no genealogy history
and adds no station-specific screen. Its intended committed sources were
tested in an isolated snapshot, excluding the owner's unrelated HMI edits.
The evidence source bindings for the shared card use staged bytes.

This reuses native UDTs/AOIs and the existing Part/event owners. Atomic consumption
policy and portable projection remain Fraktal responsibilities. Packed ASCII is
the current all-DINT transport encoding; no claim that Logix lacks native
STRING, or that this is faster, is made. No device protocol, string-processing
service, second journal or external Part-write API is added. A real device
adapter must supply confirmed component identities and qualify its own read/
write failures and identity checks.

## Qualification

- **1,890 AB tests pass**, plus the 12-test focused genealogy
  suite. Coverage includes atomic rejection, replay, self-reference, capacity,
  full-width IDs, dynamic-array capture, clear/commit ordering, malformed
  snapshots, ring wrap, SQLite replay, configuration identity and all-language
  whole-cycle/failure parity. Invalid-batch and private commit-order witnesses
  are execution-model tests; private carrier storage was not exposed for CIP.
- **74 root tests pass**; AB specification, frozen-contract and strict
  cross-artifact consistency gates pass.
- **Four v38 native compiler/read-back cases pass**: the literal/text fixture
  and a genealogy-only declared-array variant, each for EchoController and
  PhysicalController. Import summaries have zero warnings/errors. The primary
  fixture matches 42 executable bodies, 21,926 authored initial values and
  21 SFC steps. Prepared/reopened and post-download exports also match.
- The compiler-only array operand is the existing `PressRam.TimLast`, used
  solely to prove real operand resolution; this variant is never downloaded
  and does not declare timing data to be a component UID source. Device-array
  acquisition is not live-qualified by that build.
- **31/31 live tower/Part/resource regressions pass**, including 21 genealogy
  rows across ST/SFC/LD. OK, HELD/resume and one-reset restart confirm both
  fictitious components at MARK230: nine completed genealogy captures. Early
  handled-NOK, abort, mode-change and adopted-fault paths carry no fictitious
  unvisited parents. Every received event starts with an empty parent set.
- **37 final checks pass**. Current Part and retained history project correctly;
  the normal SQLite sink stores 16 retained events and one explicit overwrite
  notice. Integrity is `ok`; reopening adds no duplicates and retains parents.
  The first verification attempt incorrectly expected idle cleanup to clear the
  completed result; the retained failed check and corrected script document
  that only a new receive clears the context. PLC behavior was unchanged.
- **12 HMI tests pass**, including actual Echo snapshot hydration and the
  selectable-parent card; analysis of the four affected files reports no issues.
- **Read-only gateway process recovery passes**. An independently launched
  loopback gateway is forcibly terminated while a WebSocket client is connected.
  The client observes disconnect, a new process starts on the same endpoint,
  and reconnect/discovery/snapshot preserve all 260 Part/host-history values.
  Writes are refused before reaching the native writer in both processes.
  No installed service is stopped or changed. A preliminary client without an
  Origin header is correctly refused; the accepted check supplies an allowed
  loopback Origin.
- **12 post-gateway checks pass**, including exact final Echo identity, Run/
  fault-free state, MANUAL/idle, no active lamp test, logged-out session,
  original policy, unchanged host history and all five saved/live documents.

The genealogy-free V4 text source remains byte-identical:
`E96AF70FFC0C77FD2E44AB8CEB1B8F14FF5381A1D9A5830EC640A825872C71C9`.
The V2 tower baseline also remains byte-identical:
`03BE7A3D4F16118E328673F096EA06C250D2D64FC14027BE043B824F535A99ED`.
Only the opted-in fixture grows: declared data +4,184 bytes (124,604 to
128,788), ST source +25,087 bytes/357 terminators/448 lines. RLL stays at
23 rungs. These source/layout measurements exclude AOI storage, compiled
instructions, metadata and reserve and do not establish physical fit.

## Remaining boundaries

The port is still incomplete. Device-backed RFID/DataMatrix/host carriers,
native string adapters and external expected-identity acquisition remain open.
Native alarm/health provider promotion still needs its ownership, semantics and
physical/clock/scaling qualification. Mirror/shared-root Line transport,
installed gateway-service recovery, authenticated write recovery and remote
network/sink failures are separate gates; this read-only process proof does
not claim them. Physical artifact fit, retention/download/upgrade, security,
packaged deployment/browser flows and real nameplate/tower/HAL acceptance
require the actual target. Running-model set loading remains the deliberate
shared AB/TC3 prepare/changeover boundary.

Echo remains Run, fault-free, MANUAL/idle, with the original inputs/policy
restored, no active Part/lamp test and logged out. The genealogy fixture remains
loaded; select `FRAKTAL_AB_DECLARATION=fraktal_ab_genealogy_demo` for its tools.
