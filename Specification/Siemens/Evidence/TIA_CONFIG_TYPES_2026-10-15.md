# Typed configuration and current-value exports, 2026-10-15

Generator0.21 extends the existing owning configuration/provider services on the
simulated CPU1516 with TIA V20/PLCSIM Advanced7. The separate wired press compiles
offline. This is a selected prototype qualification, not released conformance or
physical process acceptance.

## Behavior and ownership

Owning declarations resolve REAL/LREAL, SINT/USINT/UINT, Core enums and explicit
scalar array elements. Array indices are constant, canonical and in bounds;
a model region must cover every element before being offered. Native bounds and
enum choices derive from the type/Core catalog. Existing EnumDomain metadata
feeds the generic HMI choice control; positive enum text has no leading plus.

One validator serves live writes, provider/retained reads, recipe preparation
and imported sets. Decimal input is parsed as a bounded integer rational and
rounded directly to binary32/binary64, nearest with ties to even. The formatter
extracts the binary significand, emits17 significant decimal digits and verifies
an exact reverse conversion. No VAL_STRG/STRG_VAL dependency remains in this
production codec. Integer workspace is FC TEMP data; its bound derives from the
Core value width and bounded decimal exponent. No per-module workspace or
application scheduling call is added.

Zero and normal finite values are admitted. Nonzero subnormal initializers and
edits are refused as underflow: the target interprets denormalized bit patterns
as zero. This agrees with [Siemens V20 floating-point ranges](https://docs.tia.siemens.cloud/r/en-us/v20/data-types/floating-point-numbers/invalid-floating-point-numbers).
Malformed/nonfinite values, overflow, unsupported array indices and enum values
are refused before publication. Set/recipe commit remains a bounded memory
publication after complete validation. Released Core records/ordinals and the
saved-document format are unchanged. The fixture's expanded station config has
its own schema3; the press retains its existing owning schemas.

EXPORT_CURRENT_CONFIG uses the existing Core/HMI request and consumed set
workspace. It captures complete current station config or an offered model
config without using a saved slot, including when the store is full. An inactive
model capture leaves active identity and ParCfg unchanged. A32-character hex
client token, root session generation, document name and exact next line bind
continuations. Every refusal/intervening operation invalidates the cursor;
every line rechecks complete read authorization. Saved-set export retains its
existing empty token. Station config requires model index0; the Line profile
is absent. MAIN retains three calls in the press.

## Native and host evidence

| Gate | Result |
|---|---|
| Numeric platform witness, runtime13 |33 samples:32 normal IEEE values pass exact parser/PLC-text/independent host comparisons; one subnormal is refused |
| Typed config/current export, runtime13/types03 |138 native assertions pass: typed edits/bounds, exact text/snapshots, full-store export, cursor invalidation, failed import, inactive model and LOAD_DB STOP/RUN restore |
| Saved-set regression, runtime13/sets_regression03 |241 native checks pass, including whole-set refusal/atomicity, JSON transfers, access/privacy and verified STOP/RUN recovery |
| Live generic HMI, hmi01 |Pass: authenticated two-root discovery, rendered manual command, enum choice identity, LREAL edit and complete current config export without a saved slot |
| Privacy/idle/durability before and after HMI |48 checks pass in each run; MANUAL/READY, sessions NONE, no blocking alarms, verified persistence; private reads200/readonly writes205 |
| Runtime13 compile/download |0 errors,0 warnings; source/interface witness381/84 |
| Press05 compile |0 errors,0 warnings; source/interface witness437/102 |
| Native press object parity |GRAPH19AUTO/4HOME; LAD161 networks/155 calls;185 source replay |
| Shipped default replay |24 sources |
| Siemens tool suite |202 tests pass |
| Repository consistency suite |35 tests pass; consistency0 errors/0 warnings |
| Siemens lint |0 findings; declaration-model-only pending categories remain explicit |
| Selected HMI unit/widget tests |42 pass; config sets/editor/manifest/Web API mapping/durability |

The numeric witness includes exact halfway cases, both signs, largest/smallest
normal LREAL values and deterministic samples across the normal exponent range.
The native transaction fixture covers REAL, LREAL, USINT, a Core enum and INT
array elements; SINT/UINT declaration bounds also pass the host gate.

Canonical witnesses exclude initialized DB sources, whose values TIA moves into
BEGIN. The press additionally excludes optional23_ ST twins and28_ GRAPH
adapters from that source witness because native export omits reference
annotations/empty sections. Independent GRAPH/LD object parity remains required.
Runtime/press consume different feature profiles; their counts are not directly
comparable to earlier synthetic sequence-recovery fixtures.

## Corrections recorded by the gate

Native compilation caught EnumDomain's String/WString boundary; WSTRING# literals
correct it. Runtime05 preserves that failure. The platform conversion witness
then exposed malformed VAL_STRG text near a rounding boundary and STRG_VAL
precision/underflow failures. Runtime08's exact export admission refused the
bad conversion rather than publishing a rounded document. Runtime09 preserves
the raw native comparisons. The integer codec's first compile caught fixed-array
bound queries and implicit shift conversions; generated bounds and explicit
conversions correct both errors/warnings. Runtime11/12 preserve formatter
admission failures while significand extraction was corrected. Runtime13 uses
binary extraction throughout and passes the independent numeric witness.

The REAL Web API leaf is a separate transport limit:1.175494e-38 is returned for
the stored smallest normal REAL, while its readonly typed text is exactly
1.1754943508222875E-38. The transaction test checks the raw leaf at its measured
seven-digit display precision and separately proves exact stored value through
that PLC text, including direct binary32 halfway rounding. Failed attempts and
the independent raw/text observation remain preserved.

The expanded station set invalidated an older regression assumption: its new
fields require READY, so a whole load while BUSY must refuse. The regression now
queries declared capabilities and checks unchanged live values. A fixture
command timeout is explicitly increased for that guarded phase and restored.
A subsequent old run tried login before asynchronous LOAD_DB restore finished;
the regression now waits for restore and verified durability before continuing.
It uses the shared complete-argument/final-sequence mailbox with guards before
arguments and commit. Production admission/barrier rules are unchanged.

An external VM restart removed the simulator registration. Manual recovery
first reopened Fraktal in Softbus, then created a separate unprogrammed Fraktal1
at192.168.0.1. Inspection confirmed its unspecified CPU and separate storage.
The agent stopped/unregistered that unused instance while preserving its files,
then used Resume-TiaSimOwner.ps1 to reopen the original Fraktal storage.
Keeper8564 restores CPU1516/TCPIP,169.254.212.49 plus192.168.1.1 and physical
mappings0. The existing pinned certificate still matches. The README now names
this recovery path; no blank replacement or re-pin is used for qualification.

## Reproduction and remaining scope

Current projects under AppData/Local/Fraktal/TiaStations are
Config_Types_Runtime_20261015/FrkS12/FrkS12.ap20 and the separate
Config_Types_Press_Offline_20261015/FrkS12/FrkS12.ap20. Mutable work is under
AppData/Local/Fraktal/TiaSpikes/Config_Types_20261015; final sources are runtime13
and press05. The approved unchanged candidate_structure_examples driver SHA256
is ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
No driver rebuild/whitelist, original-image replacement, address change or
physical adapter mapping is used. Native mutations use the isolated target guard
and complete-argument, final-sequence protocol; writes are never replayed.

Broader provider dispatch, runtime model creation, collection/capture and
translated enum labels remain open. The Line profile binds line config and
shifts together and is not partially published. Baseline/degradation/OEE,
module/HAL expansion, broader loss/conformance and deployment/physical acceptance
remain separate gates. GRAPH/ST permissives stay wired; ST/LD twins stay
uninstantiated. Earlier evidence remains immutable.

Evidence payloads are in [the separate archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_CONFIG_TYPES_2026-10-15/SHA256SUMS).
The SHA256SUMS manifest binds failed attempts, final source/native exports, raw
native/host logs, HMI artifacts, consumed Core dependencies and curated knowledge.
The private knowledge-database backup, native engineering-project/cache files,
SDK binaries and plaintext credentials are excluded. The sibling seal record
records manifest verification. The source snapshot preserves the prior Part IV
text bytes; only this continuation's measured section is appended there.
