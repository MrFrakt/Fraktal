# Fraktal/TIA candidate ABI gate (2026-10-15)

**Measured.** `C:\Projects\Fraktal\tools\check_tia_contracts.py` protects the
implemented S7-1500 subset before the remaining-features plan's P1 line work.
`FraktalCore/PLC/Siemens/Contracts/TIA_FROZEN_CONTRACTS_V1.json` is immutable;
Part IV binds SHA-256
`65ea0e812b82586de6f27012880a9d0200f4ed283dee39a8f420a7dead101524`.

The gate derives current facts from Core DUTs, the binding, sequence-publication
helper and HMI adapter. It checks 31 records, 22 enum domains, eight referenced
capacities, 19 native type mappings, ten sequence publication members and 21
HMI datatype projections. `--generated <full-profile-package>` and
`--native <Openness-export-directory>` require all frozen UDTs and compare their
ordered types, bounds and ExternalAccessible/ExternalVisible/ExternalWritable.
Missing, duplicate and empty exports fail. Checks never rewrite the baseline.

Nine mutation tests pass, also against an isolated staged-source snapshot based
on d65e2b03. The working press package and existing press07 native XML match all
31 layouts. Siemens tools: 208 tests; lint zero; declaration replay 24 and press
216 sources. No PLC source, simulator state or approved driver changed.

**R3 stays OPEN.** Candidate layout checks do not qualify all features, behavior,
clock quality, coherent reads, S7-1200, OPC UA, hardware or destructive loss.
Full R4 orchestration and R5 PLC test runner remain open. P1 local line owner/
mirror is next; cross-controller transport is a later owner decision.

The existing AB specification checker is stale against Part III (readiness,
S16 and S15 status): its CLI reports three findings and its repository test
fails. Do not claim the whole hosted CI green from the passing TIA gate.

Evidence: `Specification/Siemens/Evidence/TIA_CANDIDATE_CONTRACTS_2026-10-15.md`.
