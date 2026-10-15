# TIA candidate contract gate — 2026-10-15

First implementation slice of
[the remaining-features plan](../Reports/TIA_REMAINING_FEATURES_PLAN_2026-10-15.md),
P13. The immutable [candidate V1 baseline](../../../FraktalCore/PLC/Siemens/Contracts/TIA_FROZEN_CONTRACTS_V1.json)
and [`check_tia_contracts.py`](../../../tools/check_tia_contracts.py) protect the
implemented S7-1500 ABI before P1 adds line configuration. **R3 remains OPEN**;
this is an implemented-subset check, not release conformance.

## Scope

- 31 ordered Core record layouts, including the mailbox, configuration page,
  diagnostics, access, command/release, part/event and sequence contracts.
- 22 referenced Core enum domains and eight referenced capacity constants.
- 19 native scalar/string mappings, ten sequence publication members with
  declaration-derived table dimensions, and 21 HMI datatype projections.
- Optional full-profile generated/native checks require every frozen UDT,
  reject duplicates, and compare order, widths, bounds and all three external
  access flags. An empty or incomplete export cannot pass.

The checker derives current facts from the existing authorities. Checks never
rewrite V1. Part IV binds its exact SHA-256:
`65ea0e812b82586de6f27012880a9d0200f4ed283dee39a8f420a7dead101524`.
Private runtime storage and application-specific records are outside this
baseline. Adding a frozen declaration allocates nothing in a deployed station.

Pre-commit runs the candidate check on every commit, including changes outside
the Siemens tree. Hosted CI runs its mutation tests and a Siemens source job
(lint, engineering-tool tests, declaration/press replay and generated-interface
comparison). Native compilation and live behavior remain separate gates.

## Verification

| Check | Result |
|---|---|
| Candidate mutation suite | 9 tests pass, including narrowing, field order/removal/addition, enum changes, table bounds, private visibility, incomplete/duplicate exports and unfamiliar adapter expressions |
| Isolated staged-source snapshot | Same nine tests and full-profile generated-interface check pass against the intended index, based on `d65e2b03`; independent of existing uncommitted press/HMI changes |
| Generated press interfaces | All 31 frozen UDTs match |
| Existing native press07 XML exports | All 31 frozen UDTs match, including order, types and access flags |
| Siemens engineering-tool suite | 208 tests pass |
| Siemens lint | 0 findings |
| Package replay | Default declaration 24 sources; working press 216 sources, GRAPH AUTO 19 / HOME 4 steps, LAD 198 networks / 192 calls |
| Cross-artifact consistency | 0 errors / 0 warnings, strict mode |
| AB frozen-contract gate | Clean |

The native comparison uses existing `Press_Complete_20261015/press07_native`
exports, created by TIA V20. No PLC source, engineering project, simulator state,
certificate or approved Openness executable was changed by this slice. The
isolated staged-source test uses the previously committed press package; both
packages have the same frozen Core layouts. It is a source/contract portability
check, not the full R4 fresh-clone native build gate.

## Existing broader-gate failure

The combined repository-gate suite ran 80 tests with one failure in the existing
`tools.test_check_ab_spec` repository check. Its corresponding CLI reports three
findings: it expects R0–R3 PASS/R4–R6 OPEN while the AB document now records
R0–R5 PASS; it expects S1–S15 while S16 exists; and it requires S15 OPEN. The
AB checker and Part III are unchanged from `d65e2b03`. This pre-existing mismatch
remains open; the hosted cross-artifact job cannot be claimed green.

## Remaining work

P1 line owner/local mirror is the next functional slice. Full R3 qualification,
the R4 native orchestration script, and the R5 PLC test framework/runner remain
open. S7-1200, optional OPC UA, coherent multi-read snapshots, clock quality,
hardware and destructive-loss persistence are outside this candidate baseline.

Raw gate results, the isolated source snapshot and the 31 native UDT exports:
[archive manifest](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_CANDIDATE_CONTRACTS_2026-10-15/SHA256SUMS).
