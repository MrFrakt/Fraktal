# AB host events, nameplates and declaration reuse — 2026-10-18

Non-normative, append-only evidence. This closes source/compile gaps, not the
complete AB port or a new controller deployment. Base commit `fa49adcc5`, with
the exact dirty-source snapshots and hashes in the
[payload manifest](AB_HOST_NAMEPLATE_2026-10-18/manifest.json).

## Implemented

1. **One press declaration.** Echo derives the seven controller/deployment
   differences from the physical press. Shared recipes, equipment, chains and
   policy are no longer duplicated. The simulation-only account/mailbox access
   remains isolated. The inaccurate Echo description is corrected. Physical
   and Echo generated baseline files remain byte-identical; the physical
   comparison uses the HEAD generator and the same synthetic v33 seed, while
   the Echo comparison uses the workstation's empty SDK seed.
2. **Optional digital nameplate.** Root/module declarations carry all Core
   nameplate fields through the manifest and existing generic HMI paths. New
   text-key columns select manifest major 5; older declarations keep major 4
   and its exact row. Missing optional identity is empty, never inferred from
   recipes, controller defaults or a gateway URL. Identity is outside writes.
3. **Optional PLC-owned non-part HostEvents.** Capacity 1..64, default omitted.
   Native AOIs/UDTs supply one append owner, called by ST/SFC/LD. Current
   producers are mode change, Changeover start/success and reason-coded NOK.
   The NOK helper preserves a captured ReportedReason or a registered literal
   the step owns. Part/resource change producers remain unimplemented.
4. **Coherent projection and acknowledged delivery.** Odd/even metadata
   brackets initialization/publication. Reads retry within a bound and refuse
   torn/invalid batches. Per-sink cursors persist only after acknowledgement,
   with explicit overwritten-interval/publisher-epoch loss notices, source
   scoping, an exclusive lock and atomic replace. Delivery is at least once;
   supplied keys permit sink deduplication. A serial/build-guarded CLI can
   append into a local JSONL sink; it performs no PLC writes and starts no
   outbound network service.
5. **Stronger source/native/live agreement.** The new read-back gate reuses the
   existing construct/SFC comparisons and also compares executable bodies and
   authored initial values. Live projection rejects missing/corrupted static
   manifest rows even when the header still carries the expected hash. The
   manifest owns its nameplate import, including outside the root gate's
   temporary tool-path scope.

## Native-reuse and compatibility decisions

No alarm state machine or SFC scheduler is added. Native AOIs/UDTs provide
execution/storage, CIP provides acquisition, and GSV provides clock/time
quality. Portable event vocabulary, coherent publication, loss and sink
acknowledgement remain framework policy. Nameplate identity remains in the
existing authoritative manifest. Native alarm-provider comparison and the
external-module/time-source runtime qualification stay open.

Required InOut additions select a new capacity/version-named Unit AOI rather
than replacing a released signature. The host UDT and append AOI are likewise
capacity/version-named. Frozen logical host schema v1 is unchanged; inapplicable
PartUid/Subject fields are empty. Positive DINT event sequences fail visibly
at exhaustion rather than wrapping to reused keys. Startup clock words scope
the epoch; they do not prove uniqueness under clock replay or physical restart.

Existing deployment declarations do not enable these profiles. No existing PLC
image, gateway service or controller setting was changed.

## Final compiler/read-back result

Disposable fixture: `fraktal_ab_host_demo.py`, derived from Echo, all three
AUTO renditions, eight-event ring and explicitly fictitious asset identity.
Target seed: **1756-L81E, 38.011**, no physical I/O; periodic 10 ms task with
output updates disabled. Studio **38.00**, SDK client **2.1.974**, repository
offline host. Both targets below are **offline compiler targets**.

Accepted source SHA-256:
`81B5DE52A046750DBB5195BD3F5A4B83DDC0C74A345B33BCAA30879897C9F75A`.

| Check | EchoController | PhysicalController |
|---|---|---|
| SDK Open / Build / Save As events | PASS | PASS |
| Import warnings / errors | **0 / 0** | **0 / 0** |
| Construct census, descriptions and access/type/task settings | equal | equal |
| SFC executable graph: 18 steps | equal | equal |
| ST/RLL executable bodies: 39 | all equal | all equal |
| Authored initial values: 18,670 | all equal | all equal |
| Input unchanged | yes | yes |

Current source regenerates the accepted file byte-identically. Source, both
exports, SDK logs and comparison reports are preserved in the payload. The
native task/logic build was performed; no runtime execution is inferred.

## Important rejected result retained

The fixture deliberately includes quotes, a dollar sign and `]]>` in its
product text. Splitting that text into adjacent XML CDATA sections produces
valid XML but **does not preserve Logix initialization**: candidate 04 builds
on both targets, imports with one warning and resets the manifest Localization
array's initializer. The header's claimed hash survives. The warning includes
`XMLSrv_W_DD_SET_GENERAL_WARNING` / `XMLSrv_E_SYNTAX_ERROR_EXPECT_DATAMEM`.
The stricter native read-back rejects both exports.

The correction belongs in the existing Logix ASCII encoder: encode the closing
character as `$3E`, retaining one CDATA payload. Candidate 05 imports cleanly
and preserves every value, including the original product text. The comparator
decodes native dollar escapes and recognizes the SDK's empty-ASCII normalization
without accepting loss of nonempty text. Same-size ST/rung mutations and
identity-value loss are paired negative tests. The rejected source, exports,
logs and failed comparison results remain in `RejectedCdata/` within the ZIP
and the negative JSON reports; no failing artifact was relabelled accepted.

## Regression and footprint

| Check | Result |
|---|---|
| Full AB tool discovery | **1,754 PASS**, 234.710 seconds; 53 added tests |
| Root specification/contract/consistency tests | **74 PASS** |
| AB specification and frozen-contract gates | clean |
| Strict cross-tree consistency | **0 errors, 0 warnings** |
| Existing physical/Echo baseline output | byte-identical |
| Final accepted artifact regeneration | byte-identical |
| Whitespace | clean with the repository's preserved CR-at-EOL allowed |

Tests execute generated append ST and the generated ST/LD NOK calls, check the
SFC call owner, mode/start/completion behavior, first-out preservation, false
ladder power, fast-event history, full/overwritten rings, sequence/revision
limits, torn/failed reads, model/time validity, sink rejection, reconnect,
epoch changes, corrupt cursors, writer exclusion, source scoping and CLI
refusals. Kind/verdict ordinals are checked against the Core DUTs. Nameplate
tests cover version refusal, native rows, generic snapshot paths, malformed
identity/URLs and encoding. Live-row tests reject the exact dropped-localization
failure class rather than drawing an empty valid station.

Against the **same three-rendition declaration with both profiles disabled**,
the fixture adds **3,104 declared bytes**, 2,507 ST source bytes, 41 statement
terminators and 52 ST lines, with no extra ladder rungs. These are generated
size deltas, not measured controller memory or fit on the L24ER. Longer asset
text can increase the shared manifest key width; measure the actual declaration.

## Remaining acceptance and next gaps

- Live execution, sink/gateway recovery, clock replay/startup identity and
  retention across real downloads/power cycles remain unaccepted.
- Actual asset identity and browser acceptance are separate; the fixture's
  nameplate must never be commissioned as a real machine identity. No optional
  IDTA/AAS companion claim is made.
- Part/carrier integration and its four canonical host events, resource-change
  producers, signal tower, line mirror/shared-root transport, remaining native
  provider qualification and final port closure remain open.
- The v33 physical benchmark's memory/acceptance is not transferred to this
  v38 fixture; the new profiles require their own target qualification.

No download, mode/tag/clock/fault/network/firmware change, gateway restart,
commit or push was performed. Earlier unrelated workspace changes are preserved.
