# Typed configuration and current-value exports, 2026-10-15

[measured] Generator0.21 extends the existing owning provider with REAL/LREAL,
SINT/USINT/UINT, Core enum choices and explicit constant-index array elements.
The owning type/Core catalog supplies bounds, indices and enum values; a model
region must register every array element. Released Core records/ordinals and
saved-document format stay unchanged. Array collections and translated enum
labels are separate scope.

[measured] One validator serves writes, retained/provider reads, recipe prepare
and imported sets. config_decimal.scl.in owns bounded integer-rational parsing,
direct nearest/even binary32/binary64 rounding and17-digit decimal formatting.
Binary operations extract the significand; an exact reverse check admits output.
Integer workspace is FC TEMP data, sized from Core value width/exponent bounds.
The S7-1500 profile admits zero and normal finite values. Nonzero subnormal
initializers/edits are refused as underflow; Siemens documents denormalized bit
patterns as zero. Framework/Core/config_services.scl.in owns the typed wrapper.

[measured] Native VAL_STRG produced a colon in a numeric mantissa near a rounding
boundary; STRG_VAL also changed least-significant digits and returned zero for
the smallest normal LREAL. The raw native witness is preserved; production
conversion uses neither instruction. Runtime11/12's admission checks caught an
additional significand-conversion mismatch. Exact binary extraction resolves it.
Runtime13 compares33 samples with independent IEEE references:32 normal values
and exact halfway cases pass, with one native subnormal refusal. The transaction
gate passes138 checks, including binary32 halfway rounding, exact typed text and
whole snapshots, full-store capture, invalidation, inactive model and LOAD_DB
STOP/RUN restore. The saved-set regression passes241 checks; live generic HMI login/discovery,
manual command, typed choices/edit/current export pass. Privacy/idle/durability
passes48 checks before and after HMI. Both roots finish MANUAL/READY, session
NONE, no blocking alarms and verified persistence, with the preserved CPU RUN.

[measured] A direct REAL Web API read supplies only seven significant decimal
digits here:1.175494e-38 for the stored smallest normal REAL. Its typed config
text is exactly1.1754943508222875E-38. Use the readonly PLC configuration text for
exact assertions; do not compare that raw JSON number as a full binary64 value
or assume it always round-trips binary32. The production generic editor/export
already uses typed text. Raw REAL telemetry precision is a separate transport
qualification. Failed test assumptions and the raw/text observation are retained.

[measured] EXPORT_CURRENT_CONFIG reuses the existing consumed per-root workspace,
without a saved slot. A32-character hexadecimal client token, session generation,
document name and exact next line bind EXPORT_CONFIG_SET continuations. Every
refusal/intervening operation invalidates the cursor; every line checks complete
read authorization. Station config requires model index0. Inactive model capture
uses provider records and leaves running identity/ParCfg unchanged. Line is
absent; its complete profile must bind line config and shifts together.

[measured] Runtime13 source/interface witness381/84 and press05 witness437/102
match native exports. Both compile0/0; the runtime download is also0/0. Press
GRAPH19AUTO/4HOME, LAD161 networks/155 calls and185-source replay match; default
replay24, tools202 and selected HMI unit/widget42 pass. Source-witness exclusions
are explicit in the [qualification report](../../../Fraktal/Specification/Siemens/Evidence/TIA_CONFIG_TYPES_2026-10-15.md).
GRAPH/ST permissives stay wired; optional ST/LD twins stay uninstantiated.

[measured] Projects are Config_Types_Runtime_20261015 and the separate
Config_Types_Press_Offline_20261015 under AppData/Local/Fraktal/TiaStations.
Final mutable sources are runtime13/press05 in TiaSpikes/Config_Types_20261015.
The approved candidate_structure_examples driver is unchanged, SHA256
ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
No rebuild/whitelist is required. Always use the shared target guard and
complete-argument/final-sequence mailbox; never replay uncertain writes.

[measured] After the external VM restart, manual recovery left the original
Fraktal in Softbus and then created an unused Fraktal1. Its unspecified CPU and
separate storage were verified; it was stopped/unregistered with files preserved.
Resume-TiaSimOwner.ps1 reopened the original Fraktal storage. Current keeper8564
has no expiry. Fraktal is RUN/CPU1516/TCPIP,169.254.212.49 plus192.168.1.1,
physical mappings0, existing certificate/pin intact. Do not create a blank CPU,
rename storage, change addresses or relax guards to bypass recovery. Preserve
this owner/keeper. The README now gives the existing saved-image recovery path.

[pending] Broader provider dispatch, runtime model creation, collection/capture,
translated enum labels, complete Line profile, baseline/degradation/OEE,
module/HAL, broader transport/loss/conformance and deployment/physical acceptance.
