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
replies refuse. Row bodies are batched as described below. Native latency is
still unmeasured, and no proof or acceptance limit increases.

## Row-body batching (2026-11-03)

A row's body is planned once, before its first counter read. The plan holds the
selected leaves and their deduplicated occupancy counts. Each attempt sends that
plan's packets between the separately completed counter reads. Replies are
validated after the proof closes. Encoding and parsing CPU therefore never
consume a proof window. Planning time is still charged to source age and to the
one-second deadline. The deadline is checked between packets. A malformed reply
refuses even when its attempt was torn, so a retry never hides a wire defect.

Packets use the Dart `cip://` bounds: at most 64 embedded Read Tag services,
and the connection size capped at 4,000 bytes, with a 500-byte minimum. Both
directions include the two-byte connected sequence count. A lone leaf keeps the
plain single-service request. A leaf that cannot fit alone refuses at planning.
A Multiple Service Packet is not atomic (S4b host timing). Only the unchanged
counter proof makes a row coherent. Seven leaves on two packed BOOL words are
read once per leaf; that duplication is not removed.

A fake controller answers plain and MSP requests from the sealed S5 bytes. It
encodes symbols with pylogix, accepts only read services and enforces the
connection size both ways. Every owner's complete occupied row replays exactly
at 4,002 and 500 bytes. A row over 64 leaves needs fewer than half as many
packets as leaves. MSP header, count, offset, embedded-status, type, handle and
extent defects refuse. Four source mutations are each caught by their named
test. These are plan-in-loop, deferred parsing, a 65-read cap and a missing
reply bound. Thirty-five focused tests pass.

## Press harness fact accounting (2026-11-03)

`fraktal_ab_press_execute.py` reads 33 legacy facts through `read_unit`,
`read_chart` and `read_module`. An automatic accounting covers every declared
layout member it subscripts. It classifies each fact against the copy layer
generated for `fraktal_ab_press_canonical_echo38`, which WP6.6 R8 deletes:

| Class | Facts |
|---|---|
| Exact canonical copy | `Step`→`CurrentStep/StepNo`, `ScrapCount`→`NokCount`, `Mode`→`ModeActivePublished`, PartSlide `OutImm_ExecState`→`PartSlide/Status/State` (observed only) |
| Zero/nonzero equivalent | Unit and Door `Error`→`Status/FaultActive`; the harness compares `Error` only with zero |
| No canonical copy | 27, including `Running`, `Complete`, `Aborted`, `StartLatched`, `ModeSwitches`, `CycleCount`, `Reported*`, `ErrorID`/`ErrorSource`, `DecisionId`, chart `StallReason`/`Visited`/`LastMs`, and module `Execute`/`DoneCount`/`ManualCmd`/`OutImm_Pos`/`OutImm_Armed` |

This inventory does not prove that no semantically equivalent fact is
published. For example, `ErrorSource` reaches the published diagnostic only as
a source path, not an ordinal. `Running`/`Complete` reach only the
priority-ordered State summary. The harness also reads three evidence scalars
and the configuration record's `SchemaVersion` outside the contexts.

Eleven of the 15 rows (1–7 and 9–12) combine both classes in one read. One
example is `Error == 0 and Running != 0 and Step != 150`. The legacy Unit read is one CIP
request, so those facts come from one scan. A canonical row plus a separate
context read would be two requests, and an unchanged assertion could then hold
across different scans. The plan's WP6.2 wording cannot be completed as
written. It asks that assertions stay unchanged, and that the harness lose
`read_unit`/`read_layout`. After R8, the 27 private facts have no source.
Neither publishing them (TC3 path parity) nor rewriting the assertions
(no weakened validation) is available without an owner decision.

The owner decided O10 the same day (plan §6.3), choosing an acceptance-only
observation structure. Under WP6.6 R6, acceptance declarations emit one Read
Only, manifest-excluded structure with exactly these private facts. The
publication routine writes it under the same generation counter, so one row
proof covers both kinds. Assertions stay unchanged. The press harness keeps its
legacy reads through WP6.2 and migrates with the collapse.

## HX coupling accounting (2026-11-03)

The press accounting is generalized to the 24 HX modules marked
`migrate-canonical-reads`, against both S6-Q declarations; see the
[evidence](Evidence/AB_S6_HX_FACT_ACCOUNTING_OFFLINE_2026-11-03.md) (manifest
SHA-256 `329CFDF2C98AD1212560735143E84B69662B6A06301160841A04B2A7D72ED496`).
Fifteen harnesses read private context facts, and none uses exact copies only.
None can move onto canonical rows alone, so all join O10 in WP6.6. Sixteen read
through the Python projection. Two of those, `s9_read_execute` and
`s9_mutations`, test the Python gateway itself and retire with RT.

The accounting also exposes a second gap. Sixteen harnesses command through
the legacy Frame/Sequence ingress: `px.command`, `command_writes` or the runtime
`MailboxWriter`. They include `part_execute`, behind the 41 genealogy cases,
and the press rows. WP6.6 removes that ingress, and the only typed-ingress
writer is the Dart client's (WP5.1). The plan assigned no harness command path
after the collapse, so S6-Q's writer cases would have had no apparatus. The
owner delegated the choice, recorded as O11 in plan §6.3. Harnesses command
through the gateway's brand-neutral `writeBatch` and keep their own CIP
observation.

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

Row-body batching is implemented offline (2026-11-03); see the section above and its
[evidence](Evidence/AB_S6_ROW_BODY_BATCHING_OFFLINE_2026-11-03.md).
O10 moves the press migration to WP6.6. The HX accounting finds no other harness
that can migrate onto canonical reads alone. O11 selects the gateway command
path. The shared client `fraktal_ab_harness_commands.py` is built offline (2026-11-04),
and the real Dart gateway accepts and forwards its request; see the
[evidence](Evidence/AB_S6_HARNESS_COMMAND_CLIENT_OFFLINE_2026-11-04.md).
Harnesses switch to it in WP6.6. WP6.3's final oracle replay is sealed
(2026-11-04; see the [record](Evidence/AB_S6_MIGRATION_ORACLE_FINAL_REPLAY_2026-11-04.md);
manifest SHA-256 `572B84D3817FAEDC880A79B6C3F7FD8E8028B663F0C9905D43A5028524D79090`).
The replay copies and regenerated L5X files under
`C:/work/fraktal-ab-s6-wp63-20261104/` were deleted the same day at the owner's
instruction. The sealed record keeps their hashes, logs and JSON results.
The [WP6.4 inventory](AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_2026-11-02.md)
and the [V6.11 wire draft](AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md)
are written. The client binding, the generic ingress and the Dart V6.11 decoder
pass offline. Next: the host-service routines and V6.11 emission, then WP6.5
and WP6.6. Collapse, retirement, S6-Q and activation remain open;
physical S7 remains deferred.
