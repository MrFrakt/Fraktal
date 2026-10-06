# Phase 6 — bounded model creation and current-value file export

Date: 2026-10-04 (America/Bogota).
Result: **offline checks PASS; press69 owner deployment and native acceptance pending.**
The Web client is deployed and HTTPS asset hashes match. Press68 remains the
last successfully downloaded controller-memory baseline. No controller write,
download, mode change, gateway restart or physical cycle was performed here.

The owner requested a way to create models, export current parameter sets and
remove the press-demo air-pressure Start condition from Changeover. The generic
HMI now offers Configuration -> Model data -> **New model**: choose an existing
model and enter a unique code. A saved Model set offers **Create model from set**.
Both append an inactive recipe; its values can be edited through the existing
Model selector. Only ordinary Changeover activates it. Direct Model-set load
into the running recipe remains refused.

The optional native catalog has eight total slots, including three seed models.
Existing indices are immutable and there is no delete action. The PLC validates
capacity, code, source schema, complete typed records, bounds and each value's
read/write permissions before publishing Count last. Creation does not change
active ParCfg or ModelOrdinal. Boot tests retain created values and reject
corrupt catalog metadata; physical created-model retention is still owed.
Four users remain. Creation uses the existing CONFIG_SET gate, staging,
snapshots, scratch variables and audit machinery. It adds no direct tag-write
surface. The write-enabled profile is widened by kinds 37/38; it is **not**
claimed hardware-verified until native acceptance passes.

**Export current values** takes a permission-checked PLC snapshot without a
named saved-set slot. Successive export lines use one immutable connection-local
document. Current and saved exports offer **Download file** (`.jsonl`, UTF-8)
and Copy. Missing/refused lines reject the complete export. The exact press68
configuration revision is accepted as a value-schema-compatible predecessor;
arbitrary revisions still refuse. Catalog values/names come from the PLC, not
an independently maintained gateway recipe store.

The root press-demo air-pressure Start permit now applies to AUTO/HOME only.
Changeover no longer reports that condition. Cylinder pressure and directional
permits remain in every mode. Tests exercise the same generated report used by
Start authorization, rather than merely hiding an HMI warning.

The prepared artifact is [C:/work/press69.L5X](C:/work/press69.L5X), SHA-256
`850E2C57CFD9F348AC649E2F3EF6E81AA3B61DF1A713A466C2DB1BC89A93B052`.
It regenerates byte-identically from the seed, declaration and validated initial
configuration. Manifest: `66C4A00ABDB4FCC3`, revision 6735008, major 4 / binding 2,
68,472 bytes, Fields 565/640 and Localization 570/640.

| Offline size trend | press68 baseline | press69 | Delta |
| --- | ---: | ---: | ---: |
| Declared data bytes | 106,624 | 109,324 | +2,700 |
| ST source bytes | 286,681 | 291,766 | +5,085 |
| Statement terminators | 4,479 | 4,533 | +54 |
| ST lines | 5,515 | 5,564 | +49 |
| RLL rungs | 20 | 20 | 0 |

These exclude compiled code, AOI instance storage, metadata and reserve. Native
fit requires owner Studio Verify **and completed link/download**. The baseline
does not advance on these offline results.

An exact-serial read of loaded press68 at 2026-10-04T19:27:39.246783Z captured
the two configuration records, three recipe banks and current model ordinal.
The validated initial image preserves those values, including minimum air
pressure **400**. The earlier owner-confirmed 451 power-cycle observation remains
historical evidence; this turn did not write either value. The image excludes
credential-provider data, sessions and command latches. No download/upgrade
credential retention claim is made.

Validation: full AB discovery **1,561 PASS**; root **33 PASS**; consistency
**0 errors / 0 warnings**; HMI **488 PASS, 7 expected skips**, analyzer clean and
release build PASS. Five in-memory mutants are killed by assertion failures:
duplicate codes, incomplete Model sets, removed copy permissions, activation
during creation and unscoped air Start. Baseline tests pass; no mutant source
file or controller was changed. Export snapshot immutability, no-slot export,
legacy revision migration, invalid index/corrupt-count refusal and commissioning
image validation also pass.

TC3 reserves shared enum kinds 37/38 and bumps Core to 0.22.0.0; it publishes
neither optional runtime capability. Both lint profiles pass (387 objects), and
TC3 tools pass 79 tests with one expected skip. Library install and all six
CheckAllObjects solutions stopped **before compilation** on this host:
VisualStudio.DTE.18.0 solution configuration selection throws
System.ArgumentException (`SolutionContexts.Item(1)`, parameter Index); the
DTE.17.0 retry fails COM startup with 80040154 / REGDB_E_CLASSNOTREG. Those exact
logs are bound in the JSON; no TC3 compiler or runtime acceptance is claimed.

Deployment: main.dart.js SHA-256
`68696C413596EFF6A1B938DC69ABAFBAC4E599E8D9623C874BFB2CB4DC6A557D`.
main.dart.js, flutter_bootstrap.js and index.html return HTTPS 200 and match
local bytes with press.localhost TLS identity validation. Previous assets are
preserved at C:/work/press69_web_backup_01. Browser interaction/file-download
acceptance is pending; widget tests cover creation and selector updates.

Owner next step: import/Verify/download press69, restart the existing gateway,
then Ctrl+Shift+R in Chrome. Verify exact serial/fingerprint before any authorized
native harness write. Do not append disposable test models: obtain an
owner-selected code/source for creation acceptance, inspect inactive values,
perform the owner's Changeover and check retention after the owner's physical
cycle. Inspect current/saved exported files as separate browser acceptance.
The [machine-readable record](AB_PHASE6_MODEL_CATALOG_EXPORT_2026-10-04.json)
binds artifacts, source, size trends, mutation results, gate logs and HTTPS checks.
