# S3h offline inventory and finite contract review

2026-10-23, America/Mexico_City. **Inventory/review only. No S3h implementation,
accepted exception, image or controller operation.** S3g's 83-check session is
complete and genealogy is restored; its authorization is consumed. V2 remains
inactive. No commit/push.

## Frozen surface and owning types

The immutable genealogy projection expands to SHA-256
`5ca907e6076a02833a5670ef3741cd62aca626f762f9dd557f1e4b9c2c3bbe0c`.
S3h selects these next-stage paths by exact root member:

| Surface | Added paths |
|---|---:|
| Part and genealogy | 40 |
| HostEvents | 220 |
| Nameplate | 10 |
| SignalTower | 7 |
| MachineState | 1 |
| Total | 278 |

These do not overlap the accepted 4,010 legacy paths. Cumulative legacy
coverage becomes 4,288 of 4,437; 149 remain. With a full event ring, the
canonical page-count forecast is 3,950 / 3,900 / 3,550. The existing consumed
project capacities remain four measurement rows, two parent slots and sixteen
host-event slots. The live ring view follows the PLC-published occupied count;
there is no new D2 bound exception.

Core `ST_HostEvent`, `FB_HostEventPublisher`, `ST_PartResult`, `ST_MeasRecord`,
`ST_PartContext`, `ST_Nameplate`, `ST_SignalTowerOut` and owning base declarations
resolve every consumed Core member. Explicit Part III genealogy/delivery
extensions retain existing binding types/semantics. The inventory proposes
**36 type corrections**, not yet approved:

- 16 ring-event Sequence fields: Int32 → UInt32;
- Count, Capacity and RingHead: Int32 → Int16;
- 16 event stamps plus Part.Result.Stamp: String → DateTime.

The same finite list contains the one explicit value consequence: an unset
Part.Result.Stamp changes from `""` to canonical `0`. Populated timestamps must
retain their exact current UTC values; the existing generic timestamp formatter
round-trips all 17 frozen values exactly. The other **242 added paths** retain
exact values/types, including all measurement Doubles and AB-only metadata.
Existing producer sequence/epoch, append, carrier, genealogy, measurement,
identity and tower/classification owners are retained. No algorithm or domain
change is authorized by this inventory.

The [review draft](../AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md)
and [machine-readable inventory](../AB_CANONICAL_PUBLICATION_S3H_INVENTORY_2026-10-23.json)
enumerate the proposal and its acceptance work. The current plan §1 only permits
the finite previously approved exceptions, so dependent implementation remains
gated. Stage 10 generation still refuses; no production source was changed.

## Verification and retained finding

The independent validation checks the exact frozen path/value set, the exact
36-type allow-list, unchanged extension/Double types, timestamp round-trips,
all owning source hashes and the unchanged **151 accepted S3g source bindings**.
All **26 predecessor seals / 6,059 artifacts** verify unchanged. The current
2,127 AB tests and 74 closing root tests are bound by the accepted S3g seals;
implementation sources remain byte-identical. Specification/contracts/strict
consistency and whitespace gates pass after the new review documents.

The first inventory attempt failed before writing JSON because its declaration
parser did not accept `ARRAY ... OF STRING(64)`. The corrected parser retains
the string width and resolves all 278 paths. Both the failed log and executed
initial helper are preserved. This was an offline inventory-tool finding,
with no controller access or production source change.

Work folder:
`C:/work/fraktal-ab-s3h-20261023/inventory_b4de19ca39824f459912f54a69e6c0c0`.
Raw inventory/validation, source snapshots, review targets and SHA-256s are in
the sibling payload. No credentials or native ACD files are archived.
S3h builds, Capacity, native equivalence and scan are not run because no S3h
implementation/image is prepared; they remain gates after contract approval.
