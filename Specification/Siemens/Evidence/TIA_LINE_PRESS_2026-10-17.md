# Line profile in the press and public admission (2026-10-17)

Generator 0.25 completes the press integration/admission part of P1. The wired
press declares a local Line owner beside its station/model config, with the
complete V3 weekly calendar and per-shift targets. **37 Line checks and 64
existing GRAPH regression checks pass** on the reserved simulated CPU1516.
The original saved Fraktal program and the physical 1214C remain unchanged.

The [sealed payload](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_LINE_PRESS_2026-10-17/packaging.json)
contains 5,320 raw/source/knowledge payloads plus its SHA256SUMS manifest,
97,464,134 bytes in total. No credential initializer required omission or
derivation. The manifest SHA-256 is
`8184cad6d184709eeab0d79410bcdaf96bce299f970170dd29033f4c45147d44`.
The exact staged-source projection also passes all 266 tool tests, consistency,
lint and candidate contracts. Earlier evidence remains immutable.

## Composition and admission

The press declares `line_config` with its LineId, owner and stale window. One
shared `calendar_contract` helper derives flat typed calendar fields, canonical
keys, bounds and shipped localization labels from the Core row capacity. Both
the press and operations fixture use it. The Line engine derives the row
defaults from Core ST_ShiftRowV3 and owns validation, revisions, shared views,
named sets and LOAD_DB persistence. Main remains a calling routine; no project
per-scan service call is introduced.

Normal generation now admits a complete Line declaration: it requires the V3
calendar and production accounting on each referencing root. A mirror already
requires a bound F_ image provider; that provider is now included in declared
runtime dependencies. Its payload remains untrusted and whole-image validated.
The explicit `line_workbench` path remains for partial engine experiments. Its
manifest marker is emitted only when the caller actually requested it, and
ordinary generated packages preserve normal admission during verification.
The press uses the normal entry point.

This admits the qualified provider contract. OUC TCP transport is the selected
P12 continuation and remains separate from the synthetic source fixture.
The prior owner/mirror engine, atomic sets, stale/offline restore, V3 accounting
and data-class evidence remains applicable; the new integration reuses those
services.

## Checks

The Line-enabled press has 281 replayed sources. Both native software stages
pass with zero errors and warnings; 617 canonical objects, 162 FB/type interfaces
and 71 DB interfaces match native read-back. GRAPH remains AUTO19/HOME4/
CHANGEOVER6/LoadPosition4 steps; the LD examples remain 198 networks/192 calls.
An independent fresh engineering project repeats both clean native compile
stages and the same 617/162/71 read-back and GRAPH/LD comparisons.
The old 0.24-to-public-0.25 program change is generated version comments only;
the final source and native read-back are rechecked.

The 37 live Line checks cover all 21 canonical root-scoped LINE_CFG capabilities,
owner metadata, calendar writes, overlap refusal without partial application,
complete set export, atomic Line set load, model coexistence and actual restart
with the active PLASTIC model and Line target preserved. The existing wired
HOME/CHANGEOVER jumps, pacing, privacy, host events and original-instance guard
then pass 64 checks against the same deployed program.

The initial probe expected a target edit to rewrite ShiftProductionTarget in
an open interval. Core §8.5.2 explicitly requires latching at interval start;
the runtime correctly kept 7 while future configuration changed to 9. The probe
now checks configured and latched values separately. The disposable session
was closed through its stop file and rerun; no uncertain mutation was replayed.

All 266 Siemens tool tests pass, including complete owner/bound-mirror
admission, partial-profile refusal, marker-preserving round-trip and the shared
calendar contract. Repository consistency, Siemens lint and the candidate V1
contract gate remain clean. Full R3/R5/R6/HMI and physical qualification remain
open.

## Scope

Native-first review: this change composes the already qualified Core Line
contract and existing RD_SYS_T/RUNTIME/Serialize/WRIT_DBL/READ_DBL services.
It adds no second clock, file store or controller transport. The active target
continues to be reporting data and issues no equipment command.

The fixed `.56` press CPU is unmapped and released in finally. Offline compiles
finish before simulator downloads. The original Fraktal remains RUN/TCPIP
CPU1516 at 169.254.212.49 and 192.168.1.1, with Press_Complete_20261015 and zero
adapter mappings. Its saved storage/certificates and all physical commissioning
gates are preserved. The approved Openness driver is unchanged.

P1's local-owner/press integration and complete profile admission are now
implemented. P12 OUC TCP, manual held actions, I/O/PROFINET/forcing, module
expansion, durable host FIFO, reusable connectors, remaining conformance gates
and deployment/physical qualification remain. Device-specific P15 ports stay
deferred by owner decision.
