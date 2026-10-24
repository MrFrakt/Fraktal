# S1 reference captures

These gzip files expand to the original recorded JSON bytes. `manifest.json`
binds both the compressed bytes and original SHA-256; compression uses gzip
mtime 0. Never edit a capture to fit new code. Record another acquisition.
The fixture budget is 256 KiB compressed total and 16 MiB expanded per input.
Current total: 39,172 compressed bytes (511,321 expanded bytes).

`genealogy_projection_01.json.gz` is the 2026-10-19 Echo V1 projection capture:
50 native reads and 4,437 expected values, declaration
`fraktal_ab_genealogy_demo`. It contains no transport type metadata. Replay runs
in a fresh process because the legacy projection selects its declaration at
import; the station-aware replay adapter is separate from the canonical reader.

`s0_raw_capture_02.json.gz` is the corrected S0 probe capture. It includes
Symbol/member definitions and raw bytes, but no Template structure sizes or
canonical manifest. Diagnostic replay reproduces the actual native time values
and the REAL-rounded LREAL; it does not establish strict canonical acceptance.
`s0_measurement_replay_03.json.gz` preserves the historical replay oracle. All
47 checks reproduce: 45 equal and the two recorded DT/LREAL findings retained.

The test's synthetic templates are explicitly synthetic. They exercise strict
canonical decoding, logical annotations, authoritative structure-array stride,
packed BOOLs, malformed inputs, exact Int64 and nanosecond DateTime transport.
They are not recorded controller evidence.

From the repository root:

```powershell
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_projection_replay.py FraktalCore/PLC/Allen-Bradley/tools/fixtures/canonical/genealogy_projection_01.json.gz
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_reader.py --capture FraktalCore/PLC/Allen-Bradley/tools/fixtures/canonical/s0_raw_capture_02.json.gz --s0-diagnostic --output <new-json>
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_equivalence.py --projection <typed-v1-document> --canonical <typed-v2-document> --output <new-json>
```

The equivalence report compares every supplied path and transport type. Its
only path remapping comes from the five D2 corrections in frozen contracts V2.
`--values-only` is a diagnostic and explicitly cannot pass type acceptance.
Separate V1/V2 manifest hashes may differ; each acquisition validates its own
configuration token. Live equivalence additionally needs recorded same-state
evidence; matching manifest tokens alone does not make separate reads atomic.

The generic live `read_document` seam reads Symbol/Template/tag bytes and calls
a PLC manifest loader before and after acquisition. The normalized manifest
model used in S1 is not a physical V6 row ABI. S2 must implement that standard
loader; no live station-declaration or manifest-file option substitutes for it.
Strict canonical decoding rejects a missing Template structure size, unknown
logical types, invalid strings, missing bounds/counts, and unsupported array rank.
Native TIME/DT values can be inspected diagnostically; canonical V2 accepts DINT
duration and LDT timestamp publication as approved.

No recorded press projection read/values capture was found in this checkout or
`C:/work`. That fixture and recorded V6 canonical/typed paired-state captures
remain open until an appropriately gated image is available. Nothing here
asserts full live canonical equivalence or the later HMI/runtime gates.

Structure sizes use Template class `0x6C`, attribute **5**, per Rockwell's
[1756-PM020I data access manual](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf).
