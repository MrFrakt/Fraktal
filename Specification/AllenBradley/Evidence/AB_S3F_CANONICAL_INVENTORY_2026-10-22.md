# S3f configuration inventory and contract review

Date **2026-10-22**, America/Mexico_City; raw timestamps are October 23 UTC.
Scope: read-only source and frozen-capture analysis. **Not a passed S3f
preparation or runtime gate.** No controller/store connection, tag write,
download, mode change, fault clear or clock change occurred in this audit.
No commit or push.

S3e remains accepted at its sealed 2,154-path scope. Its 76 bound preparation
sources still match exactly. Its authorization remains consumed.

## Reproduced findings

The [inventory](../AB_CANONICAL_PUBLICATION_S3F_INVENTORY_2026-10-22.json)
enumerates **801 additional legacy paths**, giving **2,955 cumulative**.
Of these, 750 belong to the 30 editable entries, each with 25 fields. The other
51 cover revision/page counters, persistence, four set headers and document
response/status fields. This is a census of the existing oracle, not an
accepted canonical page shape or a revised full-Core path-count promise.

Core type declarations disagree with the legacy inferred types at **110
enumerated paths**: 60 Int32-to-Double bounds; 36 Int32-to-UInt32 values;
nine Int32-to-Int16 counters; five Int32-to-DateTime values/placeholders.
Twelve Core fields are absent from the frozen oracle. Their exact paths and
the source hashes are included in the payload; no acceptance type was changed.

The current Python oracle builds all 30 entries as one page. The native
QUERY_CONFIG branch only acknowledges, while the gateway selects a model page
in connection state. The reference Core implementation has a 16-entry window,
so these 30 entries would occupy windows of 16 and 14. Sixteen is a reference
constant rather than a mandatory numeric Core limit; the normative requirement
is bounded paging that does not require a full manifest buffer in the PLC.

The current configuration revision **1,376,612,482** is independently reproduced
from the frozen entries. Its SHA material has no boot identity; unchanged
values produce the same token after restart. PendingSince is assigned the
HHMMSSmmm time-of-day word. The inventory gives two different dates with the
same 123456000 word and different absolute timestamps, demonstrating that the
word alone cannot supply Core's timestamp. Saved-set CreatedAt instead comes
from host-computed Unix seconds. Frozen zero values do not qualify either
nonzero timestamp path.

A pure-function set-list counterexample produces count zero from the base
projection and count one from a synthetic broker overlay. No host store was
opened. Non-empty listing/export/rejection responses are owned by the host
broker today; simply publishing the empty defaults would not complete S3f.

## Proposed resolution and current gate

The [review draft](../AB_CANONICAL_PUBLICATION_S3F_CONTRACT_REVIEW_2026-10-22.md)
proposes explicitly versioned Core types, bounded pages, the missing fields,
PLC-owned revision/time and validated provider responses on the existing
mailbox. File I/O stays behind the medium seam; a generic client gets no station
knowledge. This brings forward only the configuration-dependent part of later
adapter/mailbox work. It also records D9's unresolved distinction between an
observational query and the tag writes that transport it; it creates no direct
unsecured write exception.

The supplied handover and plan require identical values/types with **only the
five D2 corrections**. The proposal exceeds that rule, so an explicit owner
decision was requested before dependent implementation. **At this record's
seal the rule is unchanged and the proposal is pending.** V2 is inactive.
No S3f product code or image has been created. This is an evidence-backed
contract review, not authorization for any future controller operation.

## Validation

- Inventory assertions pass: 801 additions, 2,955 cumulative legacy paths,
  30 distinct editable keys, 25 fields each, 110 proposed type corrections,
  16/14 reference windows, revision reproduction, date ambiguity and non-empty
  broker-list counterexamples. Sources/capture are SHA-256 bound.
- Configuration page/query/persistence/sets/data-access suites:
  **Ran 135 tests in 38.636s / OK**. The printed wrong-serial refusal is an
  expected mocked negative test, not controller access or a suite failure.
- Root suites: **Ran 74 tests in 2.175s / OK**.
- Specification and frozen-contract gates: **clean**.
- Strict consistency: **0 error(s), 0 warning(s)**.
- Tracked whitespace: pass using CR-at-EOL configuration.
- All **17 predecessor seals / 3,161 artifacts** verify unchanged.
- The complete **2,078-test / 280.759s / OK** AB preparation result remains
  bound to the exact unchanged 76-source S3e set; it was not rerun for this
  source-analysis-only change. Both prior v38 builds are likewise unchanged.

No S3f compiler/build, Capacity/scan or runtime measurement was attempted,
because no S3f generated controller image exists. HMI/Flutter checks are not
applicable: no HMI code changed. No failed validation run occurred in this
inventory work. Logs, executable inventory script, source bindings, review
snapshots and hashes are archived beside this report. Native ACDs and actual
credential files/contents are excluded.
