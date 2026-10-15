# Typed configuration and current-value documents

Generator0.21 extends the existing owning configuration provider and its keyed
records. REAL/LREAL use a bounded exact decimal codec; SINT/USINT/UINT keep
native integer bounds. Core enums validate against their actual declared values. Decimal conversion
uses bounded integer rationals and nearest/even binary rounding after strict
grammar checks. Formatting extracts the IEEE significand with binary operations
and emits17 significant decimal digits, with a verified exact round trip. Enum
text matches the advertised choices without a leading plus sign.
An array element is an explicit capability such as `StationCfg.Offsets[-1]`;
indices are constant, canonical and within the owning record. A model region
must register every element before offering a complete recipe. Collection
editing/capture and translated enum labels are separate features. Enum domains
come from Core declarations and use the existing generic HMI choice control.

Live writes, restore, recipe preparation and imported sets share the same typed
validator. Recipe/set commit remains an in-memory publication after complete
validation. Existing saved documents and released Core records keep their layout;
new owning configuration layouts require their own schema change.

The existing root manifest advertises `Features/ExportCurrentConfig`. The generic
HMI sends EXPORT_CURRENT_CONFIG with a 32-character hexadecimal token, config
kind and model index. The frame assembles an immutable complete document in its
existing workspace, without allocating a saved slot. Continuations use
EXPORT_CONFIG_SET and the same token/name, session generation and exact next
line. Every refusal or intervening operation invalidates the cursor. Every line
rechecks permissions. Station config accepts only model index0; a model snapshot
may select an offered inactive model without changing the running model.

`make_fixture.py` extends the qualified two-root LOAD_DB bench with floating-point,
enum and indexed station config. `prepare_plan.py` produces full or source-hash
delta plans for the approved unchanged driver. Compile/read back before the
separate guarded download; preserve the Fraktal simulator, addresses and storage.
`probe_web.py` covers typed bounds, malformed input, exact REAL/LREAL decimal
round trips, enum choice identity, complete export/full-store
behavior, cursor invalidation, failed import, inactive model reads and restart.
`probe_numeric.py` compares the shared codec against independent IEEE reference
values, exact halfway cases and reproducible values across the normal exponent
range. Its consumed diagnostic also preserves raw native VAL_STRG/STRG_VAL
results; those instructions are not used by the production decimal codec.
Each native mutation uses the shared target guard and final-sequence mailbox
commit. Test values are normalized and made durable before logout.

The generic live HMI gate additionally accepts
`FRAKTAL_TIA_CONFIG_TYPES_LIVE=1`; it uses the existing gateway, mapper and
repository to discover the feature, edit an LREAL and export all array elements.
The press remains a separate offline compile with GRAPH/ST wired and ST/LD twins
uninstantiated. The optional Line profile must bind line config and shifts
together; this configuration slice does not publish a partial line profile.

The S7-1500 numeric profile admits zero and normal finite values. Denormalized
values are interpreted as zero by the target arithmetic, so nonzero subnormal
initializers/edits are refused as underflow. See [Siemens V20 floating-point
ranges](https://docs.tia.siemens.cloud/r/en-us/v20/data-types/floating-point-numbers/invalid-floating-point-numbers).
