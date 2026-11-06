# S6 WP6.6 C4b ? press harness views over canonical rows and O10

Recorded 2026-11-06. Offline only; no controller accessed or changed.
C4a is committed as `0406f72c6`. This checkpoint migrates the basic press
walk's readers and the canonical press walk's inherited state reads. It does
not activate the collapsed profile for unaccounted genealogy/parity harnesses.

## Change

The generic Python row reader can co-read a bounded O10 V1 structure with
canonical leaves under the same published **scan** generation. It discovers
the fixture's native Symbol and Template, validates its flat DINT layout,
and returns those values separately from canonical values/types. The fixture
never borrows a header owner's longer proof: selecting it forces the base
scan binding, including when a selected header also has an owner revision.
The existing 20-attempt/one-second budget, strict 10 ms proof and progressing
scan requirement remain intact. Template handles and packet plans are resolved
before the proof opens. Public roots, command/service tags, arbitrary UDTs,
wrong fixture versions, malformed extents and mixed owners refuse.

`fraktal_ab_fixture_reads` maps exact public aliases to canonical paths and
reads the 29 declared private members natively. It reconstructs no lifecycle,
diagnostic, duration or count. Missing asserted facts refuse. The Door
`RunCount` key, which the basic walk reports but does not assert, is explicitly
unavailable (`None`); it is not fabricated as zero. The fixture requires an
already guarded serial and the collapsed declaration. Ordinary baseline
profiles retain the old reader in one temporary `fraktal_ab_legacy_reads`
module. A collapsed profile cannot fall back to the legacy layout.

The press `run` predicates and `PressRun` case methods are unchanged from C3.
Other HX profiles must account their own facts before migrating. Their Frame
commands and the old standalone canonical launcher still await the C5/O11
migration; this record does not claim native qualification of that launcher.

## Evidence and gates

- **2,574 AB tests pass** by full discovery, with 74 focused tests under
  ResourceWarnings-as-errors. Source hashes are unchanged throughout the suite.
- **44 Dart gateway tests pass**, analyzer clean; **85 root tests** and AB
  spec/contracts plus strict consistency pass.
- Fresh v38 build/read-back: genealogy on EchoController and PhysicalController,
  press on EchoController; SDK and access audits pass.
- Source 13 regenerates C4a source 12 **byte for byte**: genealogy
  `E25317EC6B713FB08285109F198004C5552BE49C0CE09A5AD48E72480AB5368F`, press
  `216E09BB96BB195596F60D639287C67469FC420C334D06E6290E55461084CBA4`.
  Legacy regeneration is also byte-identical to source 07.
- Exact prepared ACD `EB43312E237B2BF5FCB155F90F6C93DAEBA2B5E8A3726D566DE072830A97B215`;
  Capacity **61%, 1,921,584 used / 1,224,144 available / 3,145,728 Blocks**.
  This is offline Studio Capacity, not a runtime scan measurement.

The replay uses 86 accepted press snapshots (idle plus 85 paired captures)
from `AB_PRESS_S3_EXIT_RUNTIME_2026-10-25`. It keeps their raw canonical bytes
and old private values, supplies the new O10 structure and scan-binding
metadata synthetically, and compares every accounted fact/exact public alias.
It compares 85 before/after `PressRun.record` outputs, all 15 row predicates
and the walk's wait predicates over the accepted states and both acknowledgement
verdicts. An AST comparison pins the case logic against `8e74160c6`.
This establishes offline source equivalence, not native timing or coherence of
the collapsed image. S6-Q follows C7.

Failed investigation `c4b_predicates_01` is retained: its replay environment
omitted `slide_index`; adding the actual declaration-derived value fixed the
test without changing any case predicate. Every gate's complete log, command,
exit and source bindings are in the payload. No credentials, ACD or generated
L5X are archived; generated image and ACD hashes bind the external preparation.

## Next

C4c narrows module AOI members to externally needed parameters and private
locals and removes unused fields, keeping instance-specific initial values.
Then C5 switches commands to O11, completes the remaining harness migrations
and removes Frame/staged ingress; C6 removes the legacy tables; C7 selects
production AUTO. Native S6-Q and S7 physical/security acceptance remain open.
