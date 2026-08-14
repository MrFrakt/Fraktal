# Fraktal/AB R3 — Frozen contracts

**Gate:** R3 frozen contracts

**Result:** **PASS — the six logical contracts are frozen at version 1 in a
single machine-readable artifact, gated against Part III, with every capacity
remaining an owned hole**

**Date:** 2026-08-13

## 1. What R3 required

R3's exit is "versioned manifest, mailbox, registry, repository-handshake,
quality/timestamp, and host-event schemas". The port plan's Step B scopes this
precisely: freeze the **logical** schemas, leaving `FRK_MAX_*` capacities as
named holes for the sizing spikes, and explicitly *not* freezing physical UDT
layout, capacities or polling budgets.

Part III already specified all six in prose, each already labelled "version 1".
What did not exist was a form a generator, a gateway and a gate could all read.
Prose is the normative statement; it is not a contract anyone can consume
without transcribing it by hand — and a hand transcription is the duplication
objective O9 exists to prevent.

## 2. What is frozen

[`AB_FROZEN_CONTRACTS_V1.json`](AB_FROZEN_CONTRACTS_V1.json) is that artifact.

| Contract | Version | Content |
|---|---|---|
| `registry` | 1 | header plus the identity, execution, first-out and coherence row groups |
| `manifest` | 1 | eleven header fields and eight tables, each naming its capacity symbol |
| `valueEnvelope` | 1 | nine fields and the exact `GOOD`/`UNCERTAIN`/`BAD` quality set |
| `mailbox` | 1 | eight request and ten response fields, plus the commit rule |
| `repositoryNegotiation` | 1 | `ClientHello`, `ServerHello`, `Incompatible` and the ordering rule |
| `hostEvents` | 1 | seven ring-metadata fields and the ten-field Core §11.6 record |

The file also carries the S12-measured `logicalTypes` map and the encoding
rules that follow from it, so a generator reads one place to learn both what a
contract contains and how that content is spelled on this controller.

## 3. What is deliberately not frozen

Nine capacity symbols remain unresolved, each naming the spike that owns it:
`FRK_MAX_ROOTS`, `FRK_MAX_MODULES`, `FRK_MAX_FIELDS`, `FRK_MAX_OPERATIONS`,
`FRK_MAX_LOCALIZATION_KEYS`, `FRK_MAX_REASONS`, `FRK_MAX_OPTIONAL_PROFILES` and
`FRK_MAX_HOSTEVENT_RECORDS` (S7), and `FRK_MAX_MAILBOX_ARGUMENTS` (S9).

Five further holes are recorded with their owners: the UTF-8 policy above ASCII
and the generated timestamp representation (S12), coherence tokens, freshness
thresholds, poll budgets and quality mapping (S9), manifest table splitting and
CIP fragmentation (S7), and the GSV-sourced health and timing fields (S3).

A generator shall refuse to emit a deployable artifact while any symbol it needs
is unresolved. That rule is already normative in Part III; the freeze makes the
symbol list explicit rather than scattered through prose.

## 4. Why this is a gate and not a document

[`tools/check_ab_contracts.py`](../tools/check_ab_contracts.py) runs over the
freeze and Part III together and fails the build on:

- a contract with no version, or whose Part III marker string is missing or
  does not occur exactly once;
- **a field name in the freeze that does not appear in Part III** — so renaming
  a field in either representation is caught rather than left to be noticed;
- a field whose logical type is not declared;
- **a field using a type the baseline records as unavailable** — this is the
  machine-checkable half of AB §3.8's ban on silent narrowing. Adding a
  `float64` field fails the build instead of quietly becoming a `REAL`
  somewhere downstream;
- a contract referencing an undeclared capacity symbol;
- an unresolved capacity that names no owning spike; and
- **a capacity claiming to be resolved without a value and its evidence** — a
  number can never enter the contract without a measurement behind it.

Its own tests include a vacuity check: an empty freeze must fail, so a clean
result cannot come from the gate simply having nothing to look at.

## 5. What this does and does not authorize

Settled: the logical shape of every R3 contract, the type spelling for each
field on the pinned baseline, and the boundary between what is frozen and what
the sizing spikes still owe.

Not settled, and not implied by this gate:

- **no capacity is a number yet**, so no deployable manifest, mailbox or ring
  can be generated;
- **the wire encoding** of the repository protocol remains the gateway
  implementation's concern; the freeze fixes the first exchange's fields and
  order, not their serialization;
- **coherence and freshness semantics** are S9's, so a gateway written against
  this freeze cannot yet claim the §3.13 snapshot contract; and
- the current `fraktal.opcua.gateway.v1` implementation has no handshake at all
  and remains explicitly pre-contract.

R3 is PASS. R4 needs the packaged gate to survive S15's unattended question, R5
still has no test target, and R6 waits on S8.
