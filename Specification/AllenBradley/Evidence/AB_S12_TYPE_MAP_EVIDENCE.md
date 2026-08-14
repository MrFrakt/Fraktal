# Fraktal/AB S12 — Core→Logix type map evidence

**Spike:** S12 physical type map

**Result:** **PASS — the acceptance matrix removes three candidate types from
the binding, and the physical run measured the CIP layout, exact round trip,
overflow, NaN, string, array and duration behavior on the named target**

**Date:** 2026-08-13

## 1. What was asked

AB §3.8 requires a complete Core→Logix→repository type table before any public
UDT is generated, and forbids silent narrowing: an unsupported target
arithmetic shall use a range-checked representation or the controller leaves
the baseline. Part III explicitly refused to assume a native `TIME` exists.

The first question is therefore not "how does this type behave" but "does this
type exist here at all". That question is answered offline, and it is answered
below. It needed no controller.

## 2. Method, and why the cases are split

[`fraktal_ab_s12_type_probe.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s12_type_probe.py)
emits one minimal full-project L5X per case from the reproducible empty v33
seed. Every candidate is emitted **twice**:

* `declare` puts the tag in the project and nothing else; and
* `use` adds one type-appropriate operation.

A single combined fixture would only ever prove "something in here is
unsupported". The split is what lets a failure name one type, and it earned
its keep immediately: `LINT` passes `declare` and fails `use`, which is a
different fact with a different consequence.

Each case ran through SDK import and then Studio v33 **Verify Controller**.

## 3. Result

| Core concept | Logix spelling | SDK import | Verify `declare` | Verify `use` | Verdict |
|---|---|---|---|---|---|
| 8-bit signed integer | `SINT` | pass | 0/0 | 0/0 | **usable** |
| 16-bit signed integer | `INT` | pass | 0/0 | 0/0 | **usable** |
| 32-bit signed integer | `DINT` | pass | 0/0 | 0/0 | **usable** |
| 64-bit signed integer | `LINT` | pass | 0/0 | **1 error** | **transport only** |
| 32-bit float | `REAL` | pass | 0/0 | 0/0 | **usable** |
| 64-bit float | `LREAL` | pass | **1 error** | 3 errors | **unavailable** |
| boolean | `BOOL` | pass | 0/0 | 0/0 | **usable** |
| bit string | `DINT` + mask | pass | 0/0 | 0/0 | **usable** |
| duration | `TIME` | **import aborted** | — | — | **unavailable** |
| duration | `TIME32` | **import aborted** | — | — | **unavailable** |
| string | `STRING` (82) | pass | 0/0 | 0/0 | **usable** |
| array | `DINT[10]` | pass | 0/0 | 0/0 | **usable** |
| public UDT | mixed members | pass | 0/0 | 0/0 | **usable** |

Exact diagnostics:

- `TIME` and `TIME32` — SDK import fails closed with
  `XMLSrv_E_IMPORT_ABORTED_NO_CHANGES - The Import was aborted due to errors.`
  The type does not exist for this target, so no Verify was possible.
- `LREAL` — `Tag 'FRK_S12_Probe': The LREAL data type is not supported by this
  controller type.`
- `LINT` arithmetic — `Line 2: Invalid data type. Argument must match parameter
  data type.`

### 3.1 LINT was re-tested before the conclusion was drawn

`LINT := LINT + 1` failing with "argument must match parameter data type" does
not by itself prove LINT arithmetic is unavailable — it is equally consistent
with the `DINT` literal simply not being promoted. A further case with matched
operands, `LINT := LINT + LINT`, produced the **same single error**. Only then
was LINT recorded as transport-only.

## 4. Three consequences for the binding

**Duration is no longer a choice.** AB §3.8 offered native `TIME`/`TIME32`
*or* a range-checked `DINT` of milliseconds. On this target the first does not
exist, so the second is the binding, and the S12 fixture performs the range
check in the controller rather than trusting the caller.

**`LREAL` must leave the type table for this baseline.** Core's 64-bit float
cannot be represented on a 1769-L24ER at v33. Because AB §3.8 forbids silent
narrowing, this is an explicit recorded constraint: either the Core value is
carried as `REAL` with its precision loss stated in the contract, or a
deployment needing 64-bit floats needs a different controller family. It is not
a decision the generator may take quietly.

**64-bit integers cannot be computed on the controller.** `LINT` may be
declared, carried in a UDT and transported over CIP, but no arithmetic form
tested compiles. Any Core value that needs 64-bit accumulation must either be
computed in the gateway or represented as `DINT` with declared rollover
semantics.

## 5. SDK import is not a type gate either

`LREAL` imported through the SDK with `Warnings="0" Errors="0"` and was then
rejected by Studio Verify. S15 already recorded that SDK `BuildAsync` is not
semantic Verify; this adds that the SDK's **import summary** is not a type
check. A gate that trusted the import summary alone would have admitted a data
type this controller cannot execute.

## 6. The physical fixture, built and waiting

[`fraktal_ab_s12_fixture.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s12_fixture.py)
generates the memory-only execution fixture from the accepted types only. It
carries a public UDT of `BOOL`/`SINT`/`INT`/`DINT`/`LINT`/`REAL`, and it makes
the wire layout self-describing: the controller `COP`s the UDT into a `SINT`
array, and `COP`s two adjacent instances into a second array so the **padded
stride** is measurable. Trailing padding is invisible on a single instance, so
a fixture that copied only one could not report a size at all.

The generated logic contains **no division and no variable array subscript**,
because an integer divide by zero and an out-of-range index are Logix major
faults and no fault-clear authorization exists. Overflow is provoked only by
addition and multiplication, and NaN is copied in as a bit pattern, never
computed. The generator asserts all of this before writing the file.

Offline status:

| Stage | Result |
|---|---|
| generated L5X | `19DA069915495FB4E3C5ABE9C918709C9A85911311A362CDF0621252E1E06F90` |
| SDK import | `Warnings="0" Errors="0"` |
| converted v33 ACD | `2293460063DFAB2C3BE03005590A2FCA700737A1AF53A1133192D2AAFA1A2603` |
| Studio v33 **Verify Controller** | `0 errors`, `0 warnings`, input unchanged, closed cleanly |
| canonical round trip | `25C8C8389B78F39D8149744C75002C1A8B19E82E47A98DA6B31DC04F85896726` both passes |

Verify accepting this fixture also settles two smaller questions the probe
matrix did not cover: a `LINT` **member inside a public UDT** is legal even
though LINT arithmetic is not, and `COP` from a UDT into a `SINT` array is
accepted as the serialization idiom.

## 7. Physical result

The fixture was downloaded over USB with `0 error(s), 0 warning(s)` and the
controller returned to Remote Run.
[`fraktal_ab_s12_execute.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s12_execute.py)
then measured the following, and restored every input it wrote.

### 7.1 The public UDT on the wire

Reading the structured tag returns the raw CIP payload, so the layout was
measured **as the gateway will receive it** rather than as the controller
stores it internally. Each member was written twice with values whose encodings
differ in every byte; the bytes that changed between the two reads are that
member's storage.

| Member | Logix type | Offset | Width | Contiguous |
|---|---|---:|---:|---|
| `Flag` | `BOOL` | 0 | 1 | yes |
| `Small` | `SINT` | 1 | 1 | yes |
| `Medium` | `INT` | 2 | 2 | yes |
| `Count` | `DINT` | 4 | 4 | yes |
| `Wide` | `LINT` | 8 | 8 | yes |
| `Ratio` | `REAL` | 16 | 4 | yes |

**Payload 24 bytes; array stride 24 bytes** (a two-element read returned 48).
Members are naturally aligned, `Medium` sits at 2 rather than being padded to
4, and the four bytes after `Ratio` are trailing padding that exists only
because the `LINT` forces 8-byte alignment on the type. A generated contract
that assumed dense packing would be wrong by four bytes per instance.

The stride is a measurement, not an inference: trailing padding is invisible in
a single instance, so two adjacent instances were required.

### 7.2 Values and behavior

| Case | Result |
|---|---|
| CIP round trip, all six widths | exact, including `LINT` at ±2⁵⁶-scale values |
| `SINT` overflow, −91 + −91 | **74** — two's-complement wrap |
| `INT` overflow, −4661 × 8 | **28248** — two's-complement wrap |
| NaN bit pattern `0x7FC00000` through CIP | survives; reads back as NaN |
| `NaN <> NaN` in Logix ST | **false** — see below |
| `STRING.LEN` after writing 11 characters | 11 — counts bytes |
| Array lower bound and both edges | zero-based; `[0] + [9]` summed correctly |
| Duration 250 ms / −1 ms against the range check | accepted / rejected |
| Cleanup of every written input | verified |

### 7.3 NaN cannot be detected by self-comparison

`FRK_S12_NanReal` reads back as NaN over CIP, so the bit pattern is transported
faithfully. But the controller's own `IF NanReal <> NanReal` evaluated **false**,
so Logix ST does not implement the IEEE property that NaN is unequal to itself.

Any Fraktal/AB validity check for a `REAL` **shall** test the bit pattern or a
range, never `x <> x`. A generator that emitted the idiomatic IEEE test would
compile cleanly, verify cleanly, and silently never fire.

### 7.4 A Logix trap found on the way

The fixture also `COP`s the UDT into a `SINT` array, intended as a second view
of the layout. Those arrays stayed empty, because Logix `COP(Source, Dest,
Length)` counts `Length` in **destination** elements: `COP(udt, bytes[0], 1)`
copies exactly one byte, not one structure. Only the byte holding `Flag`
ever changed, which is precisely the misleading partial result such a bug
produces.

The measurement did not depend on it — the CIP read is both simpler and closer
to the question — so the arrays remain in the downloaded artifact as inert
tags. They are deliberately left in the generator so the recorded hashes stay
reproducible; the next fixture that needs a controller-side copy must size
`Length` in destination elements.

## 8. Commands

```powershell
# reproducible seed - no longer a hand-made artifact
Fraktal.Ab.OfflineProbe.exe --create-seed 1769-L24ER-QB1B 33 FraktalPhase0 `
  <seed.ACD> --export <seed.L5X>

python fraktal_ab_s12_type_probe.py <seed.L5X> <probe-directory>
# then per case: SDK import, then
powershell -NoProfile -ExecutionPolicy Bypass -File fraktal_ab_studio_verify.ps1 `
  -Revision 33 -Project <case.ACD> -ExpectedErrors 0 -ExpectedWarnings 0

python fraktal_ab_s12_fixture.py <seed.L5X> <fixture.L5X>

# controller-changing; current explicit authorization only
python fraktal_ab_s12_execute.py 192.168.100.89 --expect-serial 7036B510 `
  --timeout 5 --execute-fixture
```

## 9. Status and handoff

S12 is **PASS** for the pinned v33 baseline. The Core→Logix→repository type
table now has measured content for every accepted type, plus three explicit
exclusions and two behavioral rules (`LINT` transport-only, NaN by bit pattern).

R2 is no longer blocked by S12. Its remaining input is **S4's construct matrix**
— schedules, generated reset targets beyond the proven `SFR`, and generated
manifest/mailbox records.

Not covered by this spike:

- **UTF-8 above ASCII.** `STRING.LEN` was confirmed to count bytes, but only
  ASCII was written. A multi-byte code point's behavior through the Logix
  `STRING` and the gateway is unproven, and AB §3.8's UTF-8 policy still owes
  that case.
- **Layout on any other controller family or revision.** Offsets, stride and
  the accepted type set are properties of `1769-L24ER-QB1B` at `33.014`. Any
  new target reruns this spike; the table is not portable.
- **Large or nested public UDTs.** One flat six-member type was measured.
  Nested structures, arrays inside a UDT, and the 500-byte S1 transport ceiling
  interact, and S7 owns the sizing question.
- **`REAL` precision loss** where a Core value expected 64-bit float. The
  constraint is recorded; choosing per-value representation is Phase 2 work.

The controller retains the clean S12 fixture in Remote Run with every writable
input at zero.
