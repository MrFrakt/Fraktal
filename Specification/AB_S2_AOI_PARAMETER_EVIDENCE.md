# Fraktal/AB S2 — AOI parameter, nesting, access, and upgrade evidence

**Spike:** S2 AOI parameter model and target limits

**Result:** **PASS — the named v33 target executed one public UDT `InOut`
contract through eight nested AOIs, enforced member/local External Access over
EtherNet/IP, and the v33 compiler fixed the relevant boundaries and upgrade
rules**

**Date:** 2026-08-13

## 1. Baseline and safety boundary

The target is the R1 controller `1769-L24ER-QB1B/A`, firmware `33.014`, serial
`7036B510`, at `192.168.100.89:44818`. Studio 5000 Logix Designer v33 and the
Logix Designer SDK `2.00.00` / C# client `2.0.861` were used. The controller was
isolated, all physical I/O was disconnected, the embedded I/O module was
inhibited, and the fixture's periodic task had output updating disabled. The
generated logic contained no physical-I/O operand.

The user explicitly authorized the download. Studio selected only USB path
`Backplane\16` after the controller type, firmware major, serial and current
controller identity matched. The download completed with zero errors and zero
warnings and the controller returned to `REMOTE RUN`. Compiler-limit and
signature variants were offline-only and were not downloaded.

## 2. Executed parameter shape

`fraktal_ab_s2_fixture.py` generated eight nested standard AOIs from the same
fresh v33 controller skeleton used by Phase 0. Each AOI has:

- `Ctx : FRK_T_S2Ctx` as a required UDT `InOut`;
- `Text : STRING` as a required complex `InOut`;
- one atomic `DINT` Input and one atomic `DINT` Output; and
- for levels two through eight, one private nested-AOI instance local named
  `Child`.

The public context is six `DINT` members (24 bytes of authored member data).
This proves the public-by-reference shape used by the binding; S12 still owns
the final physical size of every production contract. Rockwell's current AOI
manual fixes the platform data-instance ceiling, including Inputs, Outputs and
locals, at 2 MB. The generator shall reject a compiled AOI data instance above
that ceiling and shall report the computed size; it shall not infer acceptance
from available controller memory.

The generated full-project L5X was
`01594F69A8E6FA2F9BA9E9A531162A23490CCF2CE1434E638BB216AC05ADB9C8`.
The SDK import reported `Warnings="0" Errors="0"`; Studio Verify reported
`0 errors / 0 warnings`. Two SDK export passes differed only in the three
already-approved volatile timestamps and had the same canonical SHA-256:
`5F0AE331878CA74C90027986FEF3239B06EFBA33DA38CECDCF4B0E56D1F4544F`.

## 3. Physical execution and External Access

`fraktal_ab_s2_execute.py` required the exact controller identity and an exact
fixture fingerprint before any write. It wrote only the fixture's command
member and test string, then required all of these observations:

| Case | Physical result |
|---|---|
| unconditional execution | scan counter advanced and completion stayed asserted |
| UDT `InOut` | command-derived result matched through the leaf AOI |
| nested invocation | `DepthSeen` reported level 8 |
| complex `STRING` `InOut` | length-derived result matched |
| atomic Output | output result matched the same execution |
| Read/Write member | the fixture command member accepted the guarded write |
| Read Only members | result, depth and string-length writes returned CIP privilege violations |
| `External Access: None` UDT member | symbolic read/write returned path-segment errors |
| `External Access: None` AOI instance/local surface | instance/private paths were not externally readable or writable |

The tool restored command and text inputs and verified the cyclic result,
length and output returned to their clean state. It emitted
`execution_passed=true`; values are intentionally not retained in repository
evidence.

The subsequent read-only time probe matched the S2 fixture fingerprint and
confirmed the controller clock remained host-aligned while
`TimeSynchronized=FALSE`; S2 did not set the clock.

## 4. Exact target binding after download

The ordinary canonical comparator intentionally rejected the pre-download and
post-download exports. The separate
`fraktal_ab_target_binding_compare.py` then required the precise physical
binding and normalized only these asserted changes:

| XML field | Before | After |
|---|---:|---:|
| `Controller/@MinorRev` | `11` | `14` |
| `Controller/@ProjectSN` | `16#0000_0000` | `16#7036_b510` |
| local controller module `@Minor` | `11` | `14` |

After those exact target fields and the usual three timestamps were removed,
both documents had canonical SHA-256
`5F0AE331878CA74C90027986FEF3239B06EFBA33DA38CECDCF4B0E56D1F4544F`.
Its focused tests prove a different serial, unexpected stamp, or ordinary tag
change is rejected. These fields are not added to the normal comparator's
volatile list.

## 5. AOI nesting and InOut-count boundaries

Separate disposable projects were generated from the same empty v33 source,
imported through the SDK with zero import errors/warnings, and compiled through
Studio v33 Verify Controller. None was downloaded.

| Boundary | L5X SHA-256 | Studio v33 result |
|---|---|---|
| 16 nested AOI invocation levels | `9B4F353C43D673703A0A7A438AE7A72D8DE1623A5B1CF5A3ED8C184983146424` | PASS, 0 errors / 0 warnings |
| 17 nested levels | `947EAB35E32171274A27C34E73FF1F8D9C71C47FC5897505026AABAE78641D12` | expected FAIL: maximum 16 invocation levels |
| 64 `DINT` InOut parameters | `8B1D9BE5212431B43C92500AE098925EAB1C3A51D9EFD08F6A70278298BE65AD` | PASS, 0 errors / 0 warnings |
| 65 `DINT` InOut parameters | `3AB97D527B9B21778BE8A09CD8C3BB68E7299E7E3390D6B5EBFD3AB45A9CECC8` | expected FAIL: maximum 64 InOut parameters |

This resolves conflicting older documentation for the pinned v33 baseline.
The platform boundary is 16/64. Fraktal sets the stricter generated nesting
ceiling to **8**, matching the physically executed fixture and Rockwell's
current complexity recommendation. A generated application that would exceed
eight nested AOI invocation levels fails its source gate; it is not allowed to
consume the platform's remaining levels accidentally. The public module
contract uses one `Ctx` InOut, not a growing list of per-field InOuts.

Rockwell also limits the combined number of AOI Inputs, Outputs and local tags
to 512. The generator shall count that surface and fail before import. The
64-InOut, 512-value/local, 2 MB instance, and eight-level Fraktal limits are
independent gates.

Primary references:

- Rockwell Automation, [*Logix 5000 Controllers Add-On Instructions*,
  `1756-PM010N`, September 2025](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm010_-en-p.pdf).
- Rockwell Automation, [*Instruction behavior changes*](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-01/contents-ditamap/studio-5000-logix-designer/import-and-export/instruction-behavior-changes.html).
- Rockwell Automation, [AOI combined Input/Output/local-tag maximum](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-01/contents-ditamap/studio-5000-logix-designer/add-on-instructions/add-on-instruction-error-and-notification-messages/aoi-def-exceeds-max-params.html).

## 6. Signature/import upgrade result

The SDK partial-exported the downloaded fixture's leaf AOI revision 1.0. A
deterministic tool added one final atomic `DINT` Input and imported the AOI over
existing instances in separate disposable project copies:

| Variant | Revision | Required | SDK import | Studio v33 Verify |
|---|---:|---:|---:|---|
| appended optional Input | 1.1 | false | 0 errors / 0 warnings | PASS, 0 errors / 0 warnings |
| appended required Input | 2.0 | true | 0 errors / 0 warnings | expected FAIL: missing argument for parameter 6 |

The optional L5X SHA-256 was
`859F6D726C9A8516F3BD5CD8D86984D24AD054612B8FE35C7A5448CD22914E97`;
the required variant was
`D2117A4FF5E7767B3472941CD7D5F8D48488FCD2C48C8C725CDDFB847F047F8C`.

Therefore an **appended optional atomic Input with a compatible default** may
be a minor AOI revision only when the import and every existing call site
verify cleanly. An added required parameter, any added `InOut` (InOut is always
required), parameter removal/retype/reorder, or a meaning change is breaking
and requires a major version plus coordinated regeneration. No broader
optional-Output claim is inferred from this one tested Input case.

## 7. Decision and remaining boundary

S2 is PASS for the pinned `1769-L24ER-QB1B/A` v33 baseline:

- one public UDT `Ctx` InOut plus inaccessible private state is viable;
- UDT-member and tag External Access is enforced over the selected
  EtherNet/IP adapter;
- local/AOI instance storage can remain externally inaccessible;
- the Fraktal nesting ceiling is eight, with platform hard boundary sixteen;
- AOIs are gated at 64 InOuts, 512 combined Inputs/Outputs/locals and 2 MB data
  instance, while production contracts remain much smaller and are fixed by
  S12; and
- signature versioning follows the tested optional-versus-required rule.

S2 does not prove lifecycle, prescan/restart, Execute-drop release, native SFC
ordering, or mailbox no-replay. Those remain S11/S4/S9 work. It also does not
authorize production runtime/library code while R2–R6 remain open.

## 8. Reusable tools and current controller state

The successful interfaces are documented for a fresh agent in the engineering
workstation runbook. The S2-specific reusable tools are:

- `fraktal_ab_s2_fixture.py` and `fraktal_ab_s2_execute.py`;
- `fraktal_ab_s2_signature_variant.py`;
- `fraktal_ab_s2_inout_limit_fixture.py`;
- `fraktal_ab_target_binding_compare.py`;
- `fraktal_ab_studio_verify.ps1`; and
- `Fraktal.Ab.OfflineProbe`, now able to create a new disposable ACD from a
  complete L5X as well as export L5X.

At closeout the PLC contains the memory-only eight-level S2 fixture, is in
`REMOTE RUN`, reports Controller OK with I/O not present, and has clean fixture
command/text state. Studio is closed. The rollback upload remains outside the
repository at the hash recorded in the runbook.
