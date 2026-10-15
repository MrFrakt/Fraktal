# Typed line engine bench

P1 is in progress. `tools/fraktal_tia_line.py` and
`Framework/Core/line_services.scl.in` implement the shared owner/mirror engine.
This bench uses two independent copies on an isolated S7-1500. The shipped press
does not yet declare a line; production composition, mailbox/audit routing,
named line sets, LOAD_DB document consumers and live HMI verification remain.
The optional Core Line profile also needs P2 shifts.

The engine is infrastructure beside the Unit forest. It has no HAL, parent,
registry row or equipment command lifecycle. It shares config capability
resolution, metadata, scalar/decimal codec, enum validation and typed assignments
with station config and model config. Line values require `line.*` keys, a complete
schema-versioned record and the Core line capacity (32), independently of the
per-module capability capacity (12). Widths and ordinals derive from Core.

An owner advances a nonzero revision on every accepted edit and rebuilds its
image only when the revision changes. A mirror stages the entire image before
committing it, including field revisions, domains and native bounds. It refuses
wrong identities, missing/duplicate/unknown records, older revisions and changed
values carrying the same revision. Equivalent numeric spellings remain valid
heartbeats. Revision and millisecond wrap are explicit.

Restoring an image reapplies its typed values, even at the same revision; it does
not claim a new source observation or synchronized timestamp. Source failure
keeps the previous values. Expiry raises a deduplicated LOW/SYSTEM AUTO_RESET
event that never blocks production and closes on recovery. Manifest entries use
the referencing root's scope and `Line/` items; mirror entries are read-only.

```powershell
python FraktalCore/PLC/Siemens/Tests/Line/make_fixture.py <new-sources>
python -m unittest discover -s FraktalCore/PLC/Siemens/tools -t FraktalCore/PLC/Siemens/tools -p test_fraktal_tia_line.py
```

The generated bench has 51 behavioral assertions, with numbered descriptions in
`assertions.json`. `Main` only calls its test FB. Native Serialize/Deserialize
proves image round-trip and restart reapplication; it does **not** qualify
LOAD_DB durability or a power-loss/restart sequence of the simulator.

`bench.json` owns the isolated identity and addresses. The shared
`tools/Invoke-TiaIsolatedBench.ps1` helper hosts only a newly registered,
unmapped CPU1516 in the reserved test address range. It refuses existing
registrations, preserves the network mode and other instances, and powers off
and unregisters only its own registration when its stop file appears.
`run_bench.py <revision>` verifies the exact source package, clean compiler log
and approved driver hash, downloads only this bench and checks that the saved
Fraktal instance's state/addresses/mappings remain unchanged. Each download
plan/log is exclusive; `--observe` reads without repeating a download.

See [dated evidence](../../../../../Specification/Siemens/Evidence/TIA_LINE_ENGINE_2026-10-15.md)
for native read-back, runtime checks, initial compiler findings and remaining P1 work.
