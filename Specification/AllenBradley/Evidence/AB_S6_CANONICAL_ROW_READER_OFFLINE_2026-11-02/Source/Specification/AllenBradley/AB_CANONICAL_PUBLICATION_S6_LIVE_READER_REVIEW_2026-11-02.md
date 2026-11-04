# S6 shared live-row reader — offline checkpoint

Non-normative WP6.2 progress, 2026-11-02. This follows the first S9 migration;
it does not complete live harness migration, S6 qualification or V2 activation.
No controller operation or PLC generation change is introduced here.

`fraktal_ab_canonical_reader.open_row_reader(comm, expect_serial=...)` now
provides the shared discovery entry point. The implementation is in
`fraktal_ab_canonical_live.py`. A live caller supplies a connection and serial,
never a station declaration or capture file. The capture constructor is the
offline replay seam. Imports load no declaration, generator, station, projection
or Python gateway.

## Discovery and lifetime

The exact serial guard precedes Symbol discovery. Manifest candidates use the
same Template-shape function as the existing physical manifest loader. No
candidate returns `None`, permitting the temporary legacy-baseline reader.
A present malformed, unsupported or ambiguous canonical manifest refuses;
it never causes legacy fallback. This clarifies the plan's earlier “any other”
wording while retaining its valid legacy-baseline path.

For a canonical image, an initial strict S1 acquisition validates the complete
schema and bindings. That acquisition is not a coherent live sample. Its values
and raw records are discarded after constructing the metadata cache. Every
returned row comes from new I/O. Reopen after download, reconnect or mode-change
boundaries; harness lifecycle integration is still pending. The initial whole
schema acquisition and scalar request performance are not native-qualified.

## Row acquisition

Callers select explicit canonical leaves. The reader resolves physical addresses
from Templates, fragment/product bindings, type annotations and logical bounds.
It does not infer station tag names or rename fields. StringFamily bounds,
BOOL bits, exact integer widths, Float32, LDT nanoseconds and logical scalar
conversions share the existing S1 decoders. No second projection is added.

An indexed leaf brings its published occupancy-count dependencies into the same
proof. The reader refuses out-of-selection, unoccupied or over-capacity indices.
It never substitutes allocated-but-unused slots for the published logical view.
Mixed owners require separate rows; their results are not document-atomic.

Each row has at most 20 attempts within the existing one-second total acquisition
budget. Source time starts before I/O; decoding is included in final acquisition
age. Protocol 1 retains its strict mutation-period window, including the
10,000 microsecond scan window on this image. Protocol 2 uses only its published
owner window and independently proves scan progress. Equal frozen counters
cannot produce a result. Odd/changing counters, elapsed windows, failed reads
and malformed replies return no values. Counter wrap uses 31-bit serial order.

The connected scalar reader validates service/status, native type or StringFamily
structure handle, and exact payload length. It issues read services only. Partial
replies refuse; packet batching/fragmentation and native latency remain work to
measure, without increasing any proof or acceptance limit.

## Fixture facts that must remain explicit

The engineering audit records 47 members of the selected legacy Unit context.
Only `GoodCount`, `ReworkCount` and `RunStyle` have a literal same-spelling root
leaf in the sealed S5 document. This is a spelling inventory, not a claim that
the other 44 have no semantic correspondence.

Existing harnesses also assert private facts such as `SchemaVersion`,
`Par_TaskPeriodMs`, `RunRequest`, `AbortRequest`, `ResetRequest`, `Running`,
`Complete` and `Aborted`. They are not identical canonical Core leaves. Published
status checks need explicit canonical paths; fixture-only controls, counters and
fingerprints need their own apparatus observations. A private latch cannot be
fabricated from a public state or dropped to make a migration pass. No existing
press assertion, serial/fingerprint check, write vector or cleanup changes in
this checkpoint. The next harness migration must account for each required fact
and preserve its sealed verdicts before retiring the context reader.

For example, `fraktal_ab_canonical_publication.cyclic` publishes Unit state in
the priority order Error, Running, Complete, Ready. It does not encode every
combination of those flags or the separate Aborted latch. Inverting that summary
into an old Unit dictionary would invent information. Mode and step have direct
published paths (`ModeActivePublished`, `CurrentStep/StepNo`); private fixture
checks require a separate accounting.

## Validation and current boundary

The focused suite passes 27 tests, including all 5,264 occupied S5 leaves through
complete row/count proofs, exact value/type replay, independent progress, odd
and torn retries, wrap, strict window/deadline boundaries, malformed wire replies
and discovery refusal/fallback cases. The first run used two nonexistent test
paths (`Status/Busy`, `Status/Done`) and an incomplete Template fake; that failed
run is retained, and tests now use actual published paths. No PLC defect is
claimed from that tooling failure.

Final review also makes array-index spelling exact: aliases such as `[00]` and
`[-0]` refuse before I/O. The focused tests cover them; the final full suite
passes with unchanged before/after hashes for all 385 Python modules.

The fresh S9 canonical replay passes all 124 contract cases. All 2,397 AB tests
and 74 root tests pass, as do strict consistency and the specification/contract
gates. Both v38 targets pass fresh builds/readbacks/SDK audits; generated source
is byte-identical to S5. The unchanged HMI retains its prior 802 passed/12 skips.
The [offline evidence](Evidence/AB_S6_CANONICAL_ROW_READER_OFFLINE_2026-11-02.md)
records exact outputs, source bindings and retained failures.
The census is refreshed in
[classification 03](AB_S6_CONSUMER_CLASSIFICATION_2026-11-02_03.json): 385 Python
modules, 309 classified, three additional artifacts, zero unclassified and 106
direct legacy references. The two added modules increase conservative import
closure from 292 to 294; no extra HX owner is claimed migrated.

Read-only host inspection finds the Echo service stopped and no 44818 listener.
Native discovery/fallback, row performance and active-workload equivalence are
therefore unrun. No service start, download, mode, tag write, fault clear, clock
change or power operation is attempted. S6 remains uncommitted under O1.

Next: add bounded row-body packet batching, then wire the press harness lifecycle and public assertions to this reader,
separately account for fixture-only observations, and replay the original cases.
Then finish the other HX/helper migrations and WP6.3's final oracle replay.
The [WP6.4 inventory](AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_2026-11-02.md)
is written; service layouts/implementation, collapse, retirement, S6-Q and activation remain open;
physical S7 remains deferred.
