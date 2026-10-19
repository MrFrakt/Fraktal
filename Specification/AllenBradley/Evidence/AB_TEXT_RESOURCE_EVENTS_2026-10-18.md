# Captured text resource values — 2026-10-18

Optional host schema V4 now captures bounded text tool/material values at the
owning confirmation MARK. All 1,878 AB tests, four v38 compiler/read-back cases,
31 live tower/Part/resource regressions and 31 final checks pass. Nine live text
confirmations across ST/SFC/LD preserve quotes, dollar signs and a CDATA
terminator through the generic HMI projection and SQLite. Numeric resource and
opt-out tower output remain byte-identical.

Evidence payload, source bindings, logs and native artifact hashes:
[`AB_TEXT_RESOURCE_EVENTS_2026-10-18/manifest.json`](AB_TEXT_RESOURCE_EVENTS_2026-10-18/manifest.json).
Baseline commit: `5b5104a2f21b83882b2259ccbccb93d51137224a`.
Earlier [numeric resource evidence](AB_RESOURCE_EVENTS_2026-10-18.md) and
[native-window/restart evidence](AB_NATIVE_WINDOWS_RESTART_2026-10-18.md) remain
unchanged historical records.

## Target, authorization and deployment

The owner's standing statement **“simulated plc is available for you to download
anytime”** authorizes this local Echo replacement. Each mode change/download is
preceded by the exact serial/product/revision/listener guard: `127.0.0.1`,
slot 0, Emulate 5580 product 288, firmware 38.011, serial `601FC87B`, with the
local EmulateControlLogix5580 listener. Final inspection identifies controller
`FraktalPhase0`, GUID `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`.
No physical-controller operation, fault clear, clock/PTP setting, Echo scaling,
network configuration or electrical output operation occurred.

Before replacement, the existing resource/private-window image was uploaded
and saved. All five live configuration documents matched their saved medium;
the Unit was MANUAL/idle and the session logged out. The compiled/prepared ACD
passed read-back before download. Configuration restore used the ordinary
validated medium path, recognizing the exact prior declaration with only the
new text confirmation omitted. No wildcard revision or schema bypass was added.
Credentials remain local and are not archived.

The new declaration is `fraktal_ab_text_resource_demo`, manifest major 5,
content hash `999F73A4689D3C50`, configuration revision 10067827. Source:
`C:/work/fraktal-ab-text-resources-20261018/text_01.L5X`, SHA-256
`E96AF70FFC0C77FD2E44AB8CEB1B8F14FF5381A1D9A5830EC640A825872C71C9`.
The prepared/downloaded ACD and full native exports remain local; their exact
hashes and actual read-back reports are archived.

## Implementation and native overlap boundary

The typed `ResourceText` declaration selects exactly one form:

- `literal`: 0..80 printable ASCII characters, including empty text.
- `source`: an exact declared Cfg/Unit/module DINT array of 1..81 ASCII cells.
  No expression, scalar source or explicit indexing is accepted. Shorter arrays
  are padded; the captured value must terminate by cell 80 and have a zero tail.

The existing MARK owner captures all cells before calling the existing single
append AOI. A failed Part helper on the same MARK still prevents publication.
Invalid capture latches the stream's Failed flag before changing sequence,
head, revision or retained rows. Readers refuse the bad stream rather than
dropping a malformed record to manufacture continuity. This adds no resource
command, output driver, generic string editor or device protocol.

Only declarations consuming text select V4. It preserves the V3 member prefix
and appends a private capture selector/buffer, per-slot ValueFormat and packed
text words. Four ASCII bytes occupy each positive DINT, low byte first; each
retained slot uses 21 words/84 bytes including termination/padding. Non-text
records clear that slot. Numeric resources retain signed decimal Value; Part
identity and resource Subject remain distinct. Unit/Part-service required-InOut
types and the append AOI get new versioned names; the named V4 emitter has one
body with or without Part composition.

This is a transport encoding within the binding's existing all-DINT raw reader,
not a new string-processing service or a claim that Logix lacks native strings.
The manifest already uses a native StringFamily carrier with its own typed
reader. Native device/string-provider integration remains a separately
qualified seam; this batch does not expand the public primitive type map or add
another event engine. No performance advantage over native STRING is claimed.

The disposable fixture derives the numeric resource fixture and adds one
fictitious `MATERIAL_CHANGED` confirmation at existing MARK230, after the Part
measurement helper. It adds no chart row, configuration field or device action.
The captured subject is `Fixture.ConfirmedLotLabel`; value:

```text
LOT-2026-10-18.A / press "A" / $ / ]]> / end
```

The handled-NOK path exits before that MARK and emits no fictitious text
confirmation. Abort/mode/fault paths retain only confirmations actually visited.
The shared acceptance owner validates ordered resource tuples, complete results
and the single-reset restart; the text fixture extends its expected tuple set.

## Qualification scope and results

- **1,878 AB tests pass**, 316.573 seconds; subprocess exit code zero is captured.
  The 15 new tests cover empty/max-80 text, explicit source whitelisting, build
  identity, exact configuration compatibility, snapshot immutability, malformed
  source/wire data, version refusal, stale capture isolation, wrap, SQLite replay
  and ST/SFC/LD whole-cycle parity. Invalid-source failure is model-tested.
- **74 root tests pass**. AB specification, frozen-contract and strict
  cross-artifact consistency gates pass.
- Studio 38 / SDK 2.1.974 builds both literal and declared-array cases for
  EchoController and PhysicalController: **four successful compiler cases**.
  Import summaries have zero warnings/errors. Both forms' native exports match
  **42 executable bodies, 20,880 authored initial values and 21 SFC steps**.
  The prepared ACD reopens/builds, and post-download read-back also matches.
- The array compiler case uses the existing `PressRam.TimLast` DINT array only
  to prove real operand resolution in all renditions. It is **never downloaded**
  and does not declare timing data to be a resource source. Array contents and
  later source mutation are tested in the execution model; a real native/device
  string adapter is not live-qualified by this test.
- **31/31 live regressions pass**, including 21 resource/Part rows. All three
  languages produce the text once in OK, HELD/resume and single-reset restart:
  **nine confirmations**. Adopted faults, handled NOK, abort/mode changes,
  disconnected native lamp-test expiry and restoration still pass.
- **31 final checks pass**. The final PLC ring contains the exact text with
  empty PartUid and ordinary resource semantics. The normal gateway/HMI
  projection carries that same string. The dedicated SQLite sink contains
  16 retained events plus one explicit overwrite notice; reopening adds no
  rows, integrity is `ok`, and the exact text survives JSON/SQLite encoding.
- All five documents equal their pre-download values and reopened medium.
  Original access policy, simulation inputs and logged-out session restore.
  Final regeneration equals the compiled source hash.

The V3 numeric baseline remains SHA-256
`445FFD50B129DEE4D1338A3C73B6F5BD60BFDFF02EA91B24CDD0DC48688C33A2`;
the V2 tower baseline remains
`03BE7A3D4F16118E328673F096EA06C250D2D64FC14027BE043B824F535A99ED`.
Declared data grows **1,736 bytes**, 122,868 to 124,604, only for the text
profile. ST source grows 18,428 bytes/323 terminators/353 lines; RLL remains
23 rungs. These are source/layout measurements, excluding AOI storage,
compiled instructions, object metadata and reserve; they do not prove physical
controller fit.

## Final state and remaining work

Echo remains **Run, fault-free, MANUAL/idle**, with no active Part or lamp test,
all simulation inputs and the original access policy restored, and logged out.
The text fixture remains loaded and replaces the completed private-window
image; select `FRAKTAL_AB_DECLARATION=fraktal_ab_text_resource_demo` for its
gateway/tools. The prior timing observer is not present in this image.

Device-backed carriers, genealogy, native device/string integration, physical
retention/fit/security and browser/packaged deployment acceptance remain open.
Text is bounded printable ASCII; Unicode and arbitrary native string types are
not claimed by this profile. Native alarm/health adapter promotion, clock/scaling
qualification, Line transport and network/gateway recovery retain their tracked
boundaries. This batch does not complete the port.
