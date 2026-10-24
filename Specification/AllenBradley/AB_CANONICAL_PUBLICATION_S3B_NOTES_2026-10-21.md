# S3b preparation — diagnostics and command timing

S3a runtime passes at 94 paths. S3b adds 210 independently inventoried paths,
for **304 total**, without changing the five permitted D2 bound differences.
The [inventory](AB_CANONICAL_PUBLICATION_S3B_INVENTORY_2026-10-21.json) was
recorded from the sealed legacy projection and prior inventory before the
generator implementation. The approved runtime session now passes at this
subset; see [runtime evidence](Evidence/AB_S3B_CANONICAL_RUNTIME_2026-10-21.md).
See [preparation evidence](Evidence/AB_S3B_CANONICAL_PREPARATION_2026-10-21.md)
for exact checks, retained failed runs and payload hashes.

## Published surface and limits

Each of the seven modules gains `Status.Diagnostic` fields `ReasonCode`,
`Description`, `IoTag`, `IoAddress`, `Since`, `TimeSynchronized` (42 paths).
`Description` contains the existing portable key. The three commanded cylinder
CMs gain eight `Timing.Rows` with `Id`, `Label`, `Count`, `Last`, `Minimum`,
`Maximum`, `Avg` (168 paths). Rows follow the oracle's one-based logical view;
unassigned command rows retain the oracle's zeros/empty keys. Durations use
DINT milliseconds; `Since` uses native LDT Unix nanoseconds. Unset timestamps
remain numeric zero with logical transport type `DateTime`. Nonzero ISO UTC
strings retain three to nine fractional digits for strict value equality.

The genealogy fixture has one Unit and six CMs, **no EM**. It cannot establish
EM runtime acceptance. These full-Core fields lack oracle paths and remain
explicit gaps: `Status.DescriptionKey`, `ControlDomainId`, `TileEnable`, and
`Status.Diagnostic.SourcePath`, `Severity`, `Category`. The earlier
`Decision.Timeout`/`SourcePath` gaps also remain. This subset does not invent
values or claim full-Core status completion.

New versioned status/leaf/root UDTs preserve accepted S2/S3a layouts. The
V6.1 manifest carries duration/timestamp annotations, effective access and
logical array views. A generic client imports no declaration or module model.

## Owning PLC behavior

One generated private resolver owns reason-key lookup, held permit/area key
selection, electrical-role joins and Gregorian calendar conversion. Module
owners supply existing reason, onset, role and permit facts. Private input
caches avoid rebuilding descriptions, joins and timestamps until these inputs
change. Command timing values update on changed completed-command counts.
First-scan initialization and reset-to-zero counts are included.

The resolver validates real calendar dates and the signed 64-bit nanosecond
range. Exact quotient calculation removes the remainder before Logix integer
division; native conversion otherwise rounds. LINT intermediates supply LDT
assignments, including zero. Direct DINT zero to LDT failed native compilation
and was corrected before preparation. All working storage is top-level
External Access None, outside the public whole-read records. Existing
publication access and mailbox/fixture write allow-lists remain enforced.

## Acquisition and read-back

The paired oracle retains the same equal-even whole-scan proof and bounded
100 attempts / five seconds. The larger read plan batches small legacy UDTs
with CIP Multiple Service Packets; large canonical records retain fragmented
reads. Raw responses are decoded only after the closing generation read.
Strict service/count/offset/type/status/length validation preserves complete
UDTs, including their first DINT. The vendor public multi-read parser is not
used for these UDTs. A read-only transport diagnostic against restored genealogy
returned eight complete UDTs in two wire reads; this is transport evidence,
not S3b same-scan acceptance.

Large Studio manifest exports omit Decorated initial values and retain L5K.
A strict schema-based L5K fallback now compares all 1,717 authored manifest
values, including string padding/lengths and authoritative array extents.
Unsupported atoms and malformed/truncated input fail. No authored values were
waived to pass read-back. Native source/read-back and prepared ACD audits
retain the original top-level access allow-list and check all canonical members.

The existing 31-row fixture adds read-only observations before its existing
held-PressRam and PartSlide-fault-stimulus clears, alongside four decisions.
Adoption drops the child's Execute and clears its local diagnostic; the Unit
owns the latched first-out, which is the fault observation's diagnostic path.
Metadata `module` names the cleared stimulus; `diagnosticPath` names the owner.
Acceptance must require held/fault coverage across all three rendition
ordinals. It adds no stimuli, writes, model creation or regression rows.
Observer errors are retained and fail acquisition; they cannot prevent the
parent harness's cleanup writes after failure.

## Prepared artifacts and Capacity

Work folder:
`C:/work/fraktal-ab-s3b-20261021/prepare_17bd9babe817422b977d82139bae95cb/`.

| Artifact | SHA-256 |
|---|---|
| `genealogy_s3b_final.L5X` | `72B9FAA0ECA228FEBAD8D19B5628A09DC06B87E739AAB3473C63E1E891CEF589` |
| `s3b_canonical.ACD` | `634A3A86B88E666CFFCA9F530AC1D279709078BCF3E2C7EC2727B4B134394EEF` |

Both v38 targets compile with clean imports and equivalent read-backs. The
prepared ACD was reopened, built and exported equivalently. Regenerated S2
and S3a outputs retain their accepted hashes; their sealed pairs replay with
unchanged path values/types. Failed source/import/build/read-back runs remain
in the preparation evidence.

The [automatic Capacity method](AB_CAPACITY_FORECAST_METHOD_2026-10-21.md)
reproduced the owner's exact S3a values before measuring this pinned S3b ACD:
**991,612 used / 2,154,116 available / 3,145,728 total Blocks**, displayed31%,
+174,136 over S3a. The source hashes remain unchanged and both review processes
closed. This supplies the offline measured Capacity gate without another
screenshot. The forecast, excluding S3b from calibration, was 977,992 blocks
(13,620 low, 1.3735%); its advisory planning budget was 1,229,016 blocks.

## Runtime result and remaining work

The owner approved the exact guarded S3b session. Fresh backup, candidate
download/Run, restore, both 31-row matrices, full read-backs/access audits and
final readiness pass. All 304 paths/types match; four decisions, ten held and
four Unit fault pairs cover all three renditions. The first eight-row run
failed scan acquisition on the mailbox's 500-byte connection. The second
31-row run passed values/behavior but lacked fault coverage. Independent
4,000-byte observation and correct Unit ownership close both gates without
changing PLC code, writes or proof. Failed runs and all 101 actual regression
rows (62 accepted, 39 extra candidate) are retained.

Native candidate median LastScanTime is 123 us (122–123), cumulative maximum
1,190 us, zero overlaps. S3a was 110/1,178 us; workloads differ. Restored
genealogy median/max is 99/1,167 us. Final gates pass 2,011 AB tests, 74 root
tests and spec/contracts/strict consistency. The candidate's SDK-saved ACD
hash is `B308A9E4DE98B5E7557CDA84F55A6C57281DA161100B22D3A5F3AC7EA2079835`;
retain the original pin. Genealogy/five documents are restored and all final
checks pass. Do not rerun this completed session. Physical/security acceptance,
the named full-Core gaps, later surfaces and shipping activation remain open.
No commit or push is authorized.
