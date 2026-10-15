# GRAPH recovery demo and root decisions - 2026-10-12

The owner requested TC3 AUTO recovery/jump examples, GRAPH naming and wiring of
GRAPH sequences plus ST permissives. ST/LD twins remain optional examples. There
is no physical bench for press process qualification.

## Qualified result

- The isolated wired demo compiles with zero errors and warnings. Four final
  compiler results cover the complete application, single hardware-driver FB and
  explicit config default branches. The unchanged grouped driver is SHA256
  ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
- All95 generated sources replay. Native GRAPH retains AUTO19/HOME4 steps, two
  alternative branches, the simultaneous fork/join and exact comparison wiring.
  Native LD readback matches161 networks and155 calls across release, AUTO, HOME
  and load-position examples, including operands, typed pins, return wires and order.
- The separate two-root/nested-Unit bench passes36 decision/private/readonly checks,
  plus96 state/alarm,120 config and122 access regressions. The decision harvest is
  repeated after regressions. Large test scratch records use private DB storage;
  the attempted101514-byte temporary allocation exceeded the native16KB stack limit.
- 144 Siemens tool tests and35 consistency tests pass. Lint reports0 findings,
  consistency reports0 errors/warnings, diff check is clean, and relocation verifies
  all11166 original payload files and their existing historical SHA bindings.

Main is three calls: input read, root scan, output write. One concrete hardware
FB owns the logical I/O; no addresses or synthesized feedback are introduced.
The Unit owns GRAPH AUTO/HOME and ST release. Typed CM operations retain common
lifecycle/lease handling in Core. Branch identity prevents cross-leg ownership.
Early exits abort a still-BUSY child; a handled ram failure withdraws the failed
output while awaiting deliberate scrap confirmation. Homed is derived every scan.

N180 chooses return-to-load on two-hand release; N190 jumps to N100. N200 chooses
scrap confirmation on failure, then rejoins return-to-load. The TC3 serialized
N200 failure transition reads ADVANCE although its action selects JUMP1. This port
uses the intended JUMP1; original TC3 files are frozen unchanged under TC3Reference.
The visual parallel demonstration leg adds no invented machine operation. ST/LD
share sixteen main process steps; three GRAPH-only rows express the native fork/join.

Decisions allocate one private slot per actual root. Requests are full-value
idempotent, overlap does not overwrite the first, finite defaults must be offered,
operator answers win expiry, only the root answers and only the raiser consumes.
Generated management owns withdrawal; root mirrors are readonly. Ordinary faults
retain MANUAL_RESET capture; handled messages close as AUTO_RESET.

## Evidence and current environment

Raw payload: [archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_GRAPH_RECOVERY_DECISIONS_2026-10-12/).
SHA256SUMS binds 8152 files (124739478 bytes), verified after freezing.
The useful entry points are30_example_parity.json,33_gates.json,
34_final_decision_probe.jsonl,35_final_build_summary.json, the native export_gated,
SourceSnapshot and the four JUnit harvests. Earlier failed imports and compiler
attempts are preserved alongside the accepted results.

Runtime qualification uses decision_candidate_04 and its saved native image;
offline press qualification uses candidate_gated/current generated sources. Config
generator default ELSE branches were subsequently made explicit and compiled in
the offline demo. These are separate qualified scopes, not a physical process test.

The wired offline project is
`%LOCALAPPDATA%\Fraktal\TiaStations\Auto_Recovery_Verify_20261012\FrkS12\FrkS12.ap20`.
The owner Fraktal simulator runs
`%LOCALAPPDATA%\Fraktal\TiaStations\Decision_Runtime_20261012\FrkS12\FrkS12.ap20`:
RUN, CPU1516, TCPIP,169.254.212.49 and192.168.1.1, physical adapter mappings0.
Keeper PID1748 is preserved. The press application was not downloaded.

The workstation whitelist script overwrites one Entry per executable basename.
The old preserved candidate ceased to match that entry after the grouped candidate
was whitelisted. Its stalled headless session was stopped; run_plan.py --driver
now selects the existing approved grouped executable without a rebuild or new
owner whitelist step. That retry downloaded the isolated qualification bench.

## Limits and next port slice

Physical addresses/process testing, complete four-table sequence frontier/HMI chart
integration, complete parameter-alias exclusion, option-specific policy extensions,
durable audit/alarm media and named config sets remain open. TIA strips flags on
structured/FB chart aliases; HostStatus avoids a duplicate direct Status browse root
but does not prove complete exclusion. Full binding conformance is not claimed.
The next config slice is named sets/import-export using the existing typed
validate/stage/commit and access handlers.
