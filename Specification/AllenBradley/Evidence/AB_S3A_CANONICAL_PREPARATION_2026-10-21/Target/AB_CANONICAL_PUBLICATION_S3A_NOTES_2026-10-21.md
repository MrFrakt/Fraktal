# S3a Unit core preparation notes, 2026-10-21

S2 runtime exit passes; see [the sealed record](Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21.md).
This is an engineering inventory for the next surface, not an accepted image.
The owner selected preservation of the oracle's logical path set through
PLC-published extents/live count references. The generator, generic V6.1
reader and paired harness now implement that view; see the
[wire candidate](AB_CANONICAL_PUBLICATION_S3A_WIRE_DRAFT_2026-10-21.md).
Native preparation and offline gates do not authorize controller operations.

The [path inventory](AB_CANONICAL_PUBLICATION_S3A_INVENTORY_2026-10-21.json)
uses the successful S2 paired capture and the existing projection functions.
It binds the sealed S2 payload manifest by SHA-256. The S3a target has **94
paths: the 46 accepted S2 paths plus 48** for Decision, command catalogs,
mode policy, supported modes/run styles and the model catalog. Catalogs belong
to the commanded CMs; passive CMs publish CatalogCount=0. The oracle publishes
no Unit command catalog. The existing three D2 lower-bound changes in this
surface are applied explicitly, with no value/type normalization.

Array views need an explicit implementation before generating a candidate:

- The genealogy declaration offers modes 0-3. Core's MODE_COUNT is 7; publishing
  all physical policy/flag slots adds paths absent from the current oracle.
- The declaration's decisions have at most two options. The Core decision
  record reserves six. Unused capacity must not silently grow the accepted set.
- Model storage has eight slots and three current models. AvailableModels is
  projected only through the current PLC count, which can change after model
  creation. Freezing that count to three in engineering metadata is incorrect.

V6.0 currently carries a static ElementCount, and the generic reader requires
non-BOOL array counts to equal physical template extents. S3a therefore needs
a versioned PLC-published logical array view, including a live count reference
where appropriate, with validated bounds and tests for count changes and
unused storage. Any ordinal selection needed for non-contiguous declared modes
must also come from the PLC. A generic client cannot infer it from a station.
The strict path/type/value comparator and five D2 corrections stay authoritative;
do not hide extra capacity paths by shrinking the comparison after discovery.

Decision.Timeout and Decision.SourcePath have no existing oracle paths. They
are a separate full-Core contract gap, not values to invent in this 94-path
migration comparison. The plan's surface names do not establish their existing
implementation or acceptance. Record their disposition before claiming the
complete canonical contract.

Offline preparation now passes; see [the exact artifacts and results](Evidence/AB_S3A_CANONICAL_PREPARATION_2026-10-21.md).
The review copy and proposed guarded session are ready. Current authorization,
the new candidate Capacity result, runtime equivalence/regressions and scan
measurements are still required. S2's measured capacity and
timing provide the prior-stage baseline. A new image needs current controller
authorization; the completed S2 authorization does not cover it.

Working inventory:
`C:/work/fraktal-ab-s3a-20261021/inventory_c8ab4705096a49288e5dca5410435187/`.
