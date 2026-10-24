# AB canonical publication — S1 reference oracle

2026-10-20 local (`America/Mexico_City`; captures extend into 2026-10-21 UTC).
Non-normative evidence. **The S1 oracle exit passes at the scope below.**
No controller-changing operation, deployment, commit or push occurred.

The owner approved the V2 target contract and Part III amendment with
**“Approve drafts and proceed to S1”**. V2 now records that approval and remains
`active: false`; shipping Part III/V1 remains authoritative until the staged
implementation gates pass. The archived S0 review drafts were not changed.

## Implementation and acceptance boundary

- `fraktal_ab_canonical_reader.py` consumes Symbol/Template/native bytes and a
  normalized PLC-manifest model. Roots are controller structures with top-level
  `Status`, checked against the published root identity and Unit tier. There is
  no station/declaration/projection import in the reader. Its live seam requires
  the standard wire-manifest loader that S2 must implement with the V6 row ABI;
  an external manifest file is not a live discovery substitute.
- The shared S0 decoder has a strict mode using authoritative Template byte
  sizes for array stride. It rejects bad extents, missing/recursive references,
  unsupported rank/types, invalid UTF-8/LEN and non-finite floats. Diagnostic S0
  defaults preserve the historical findings. BOOL offsets/bits, logical array
  bounds/counts, exact decimal Int64 and UTC nanosecond DateTime are covered.
- `fraktal_ab_canonical_equivalence.py` compares every supplied path, transport
  type and value. The five D2 corrections are read from approved V2, applied only
  to the owning Unit's named arrays. There is no global reindexing, value
  tolerance or ignored path set. Live comparison requires explicit same-state
  evidence; configuration coherence alone cannot make separate reads atomic.
- `fraktal_ab_projection_replay.py` isolates the station-aware legacy oracle in
  a fresh process. No shipped gateway uses these tools.

The physical V6 manifest ABI is S2 work in the approved target. The plan is
clarified to put its wire loader and stable paired live acquisition with that
image. S1's synthetic normalized manifest does not freeze a physical layout.
No recorded press projection read/values capture was found in this checkout or
`C:/work`; it remains required before full S3 acceptance on an appropriately
gated image. The retired L24ER was not contacted, and no recorded fixture was
manufactured or relabelled.

## Recorded replay and read-only Echo observations

The three fixtures decompress to the original bytes, with compressed and source
SHA-256 in their [fixture manifest](../../../FraktalCore/PLC/Allen-Bradley/tools/fixtures/canonical/manifest.json).
Total **39,172 compressed bytes**, **511,321 expanded bytes**; budget 256 KiB
compressed total and 16 MiB expanded per input. No credentials were archived.

1. Genealogy V1 capture: **50/50 reads, 4,437/4,437 values**, original hash
   `5CA907E6076A02833A5670EF3741CD62ACA626F762F9DD557F1E4B9C2C3BBE0C`.
   Original transport types were not recorded; this is a value regression,
   explicitly not type or live canonical acceptance.
2. S0 raw capture plus historical replay: **all 47 checks reproduced**,
   **45 equal**, retaining `numbers.Wide` (REAL-rounded LREAL) and
   `dt_from_lint.StampUsFromLint` (LINT-to-DT conversion) as the two findings.
   The capture lacks structure sizes and a canonical manifest; it is labelled
   diagnostic and cannot pass strict canonical acquisition.
3. Exact local Echo guard passed: `127.0.0.1`, slot 0, serial `601FC87B`,
   product code 288, Emulate 5580 Controller, revision `38.11`; listener process
   `EmulateControlLogix5580`. Read-only discovery obtained **61 Symbols** and
   attribute-5 byte sizes for **50 Templates** on restored legacy genealogy.
   The largest observed existing template is 9,356 bytes; this does not measure
   the controller's maximum tag/structure size or settle the supplementary probe.

Template class `0x6C` attribute **5** is the wire structure byte size, per
Rockwell [1756-PM020I](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf).
The reader checks service/count/attribute/status and bounds rather than assuming
a byte gap is a stride. Synthetic tests exercise trailing padding, a full
12-bit handle whose low byte collides with an atomic code, malformed inputs,
coherence changes, exact Int64/ns timestamps and all five D2 mappings. Synthetic
inputs/CLI examples are identified separately from controller acquisitions.

## Gates and exact results

All commands ran from the repository root. Full command arrays and durations
are in the [payload](AB_S1_CANONICAL_READER_2026-10-20/manifest.json).

| Gate | Result / raw output |
|---|---|
| AB discovery suite, final | `Ran 1921 tests in 255.385s` / `OK` |
| Focused canonical suite | 20 tests / `OK` |
| Root spec/contract/consistency test suites | `Ran 74 tests in 1.916s` / `OK` |
| `python tools/check_ab_spec.py` | `Fraktal/AB specification gate: clean.` |
| `python tools/check_ab_contracts.py` | `Fraktal/AB frozen-contract gate: clean.` (active V1) |
| `python tools/check_consistency.py --strict` | `0 error(s), 0 warning(s) across inventory, localization, parity, readsurface` |
| v38 EchoController offline build/read-back | exit 0; clean SDK audit; equivalent read-back |
| v38 PhysicalController offline build/read-back | exit 0; clean SDK audit; equivalent read-back |
| Source AST/whitespace, approval state | passed; V2 approved target and inactive |
| `git diff --check` | exit 0, empty output |

The native builds revalidated the unchanged corrected S0 source, SHA-256
`F3CB9D6CA3BCAC1A7912B1B6721F46F4EC30D2FB2054BE61EA64CE8669A1D1ED`;
both imports report zero warnings/errors, and source remained unchanged.
They do not compile or accept an as-yet nonexistent canonical production image.
The earlier 1,920-test run is retained before the final complete-replay test.
Expected negative guard/CLI messages remain in the raw test logs. Both full
runs also emit the existing unclosed-socket `ResourceWarning`, present in the
prior S0 suite at `fraktal_ab_manifest.py:395`; the suites pass but are not
described as warning-free. No test failures were suppressed.

No HMI code changed in S1, so Flutter dependency/analyze/test gates were not
invoked and no Flutter SDK was selected. No PLC source/data/task changed in S1;
no new Capacity Estimate or native MaxScanTime was obtained. New canonical
surface memory/scan measurements remain mandatory; capture/template byte sizes
are not controller memory estimates.

## Runtime state and remaining gates

Read-only final checks passed: Run, `IsFaulted=false`, keyswitch Remote,
scanning, MANUAL/idle, logged out, not restoring, original access policy, and
all five saved documents equal live. Exact scan counts/timestamps and Echo
inspection are preserved in the payload. The restored genealogy image remains
loaded; the historical S0 session files/pins were not reused or overwritten.

Before S2 runtime acceptance: prepare/build/read-back the supplementary
size/fragmentation/browse-name/effective-access and full-precision LREAL probe;
obtain current controller-change authorization separately; complete its guarded
backup/download/restore sequence and the applicable Capacity/scan gates. S2
then implements the physical V6 manifest and first canonical surface, including
typed paired-state captures/equivalence. Press capture, later surfaces, HMI,
physical target and commissioned CIP Security acceptance remain open.

The payload is append-only and SHA-256 bound by `manifest.json`. It includes
source/approved-target snapshots, original and final gate logs, read-only
observations, diagnostic/legacy replays and explicitly synthetic CLI examples.
Unrelated owner edits were left untouched. Nothing is committed or pushed.
