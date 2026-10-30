# S4b O8 configuration heartbeat qualification — 2026-10-28

**The final-source WP4b.5 rehearsal prerequisite passes. Native S4b-Q is next;
no native acceptance is claimed here.** Echo remains on genealogy with passing
before/after preflights and zero controller-changing operations.

The owner approved the [read-tier review](../AB_CANONICAL_PUBLICATION_S4B_METADATA_TIER_REVIEW_2026-10-28.md)
with “Approve CIP configuration heartbeat (Recommended)”
(`call_a7b096025e8b4393802914b727457fab:0`). This record supersedes the original-tier
checkpoint in [the scheduling record](AB_WP4B5_SCHEDULING_2026-10-28.md), whose
1,474 artifacts and source snapshots remain immutable.

## Implemented policy

`OpcUaConfigurationReadPolicyClient` is an optional transport capability.
`CipSessionClient` enables it; reconnecting clients delegate the active client's
capability and default off when absent. The repository includes its value in
the tier-cache signature, so a capability change recomputes tiers even if the
paths, roots and manifest replacements are identical. No CIP type check or
station declaration is added to the repository.

Only when a budgeted tiered transport opts in, existing configuration-container
leaves without exact hydrated replacements use the declared metadata period /
Good /expiry of **5/7.5/15 seconds**. The existing classifier and container list
remain authoritative. The sealed genealogy inventory has **230 candidate
leaves**: Meta 186, AvailableModels 8, Catalog 18, ModePolicy 8 and Nameplate 10.
This is an inventory, not a runtime allowlist. Exact replacement overlays retain
their existing behavior. Unknown leaves and configuration-name heuristics alone
stay fast.

Status/identity, capabilities, active alarms, counters and station freshness
retain fast Good/expiry **1/3 seconds**. Field values/types/bounds, per-group
equal/even counter proof and full I/O window below 10 ms, 20-attempt/one-second
budget, source timestamps, access masks and the read-only write gate remain
unchanged. Non-CIP transports do not opt in and retain their existing policy.

Tests exercise both policies, identical-path capability changes, reconnect
delegation/downgrade, all five static containers, fast identity/alarms/unknown
metadata, and the real CIP capability through the sealed socket stack. The
other scheduling, configuration-cache and trace corrections retain the scope
documented in the prior record. No PLC source or image changes.

## Exact-source rehearsals

All four runs bind identical copies of the **27 HMI inputs**. The
independent verifier checks those against the current tree and against each
other, plus the frozen inventory, every capture's LIVE flag, refusals, peer
delay samples, graceful shutdown and before/after genealogy checks.
The prior scheduling record's phrase “27 changed inputs” refers to these bound
inputs, including unchanged driver and package files; every changed HMI file is
covered by the verifier's separate Git-diff check.

| Run /seed | Complete views | Mapped samples | Maximum mapped effective age |
|---|---:|---:|---:|
| Profile 01 /8 | 31 | 92 | 392.880 ms |
| Profile 02 /7 | 31 | 84 | 484.124 ms |
| Profile 03 /9 | 31 | 91 | 453.639 ms |
| Debug 01 /8 | 0 | 2 | 799.913 ms; STALE at `after-overview` |

Each profile run covers all **seven modules and three bus nodes**, with both
read-only action refusals, no skipped view and no client write. These are three
consecutive passes below **700 ms** on the approved implementation. The debug
refusal is retained as the required comparison; it does not count as a profile
pass. The earlier provisional broader-policy runs are not reused.

The peer still serves capture SHA-256
`B0EBFBD06853FBAF1262C3B74549F88F99BD9AF37E1585844DC5B9A4291AFB4A`,
with the unchanged 10 ms counter and piecewise delay model. Requested versus
realized delays are checked in the retained samples; truncation flags remain
visible. These are synthetic-peer results, not native E7 or physical performance.

## Gates and next session

- **740 HMI tests pass /12 skipped**; analyzer, locked dependencies and Windows
  profile build pass on **Flutter 3.47.5 /Dart 3.13.4**,
  `C:/work/fraktal-toolchains/flutter-3.47.5`.
- **74 root tests**, AB spec/contracts, strict consistency and whitespace pass.
- The **373 PLC/gate source bindings** remain unchanged. **2,339 AB tests**, both
  v38 builds/read-backs and **65% Capacity** transfer by hash; they are not rerun.
  Candidate image remains `30315E6D…A3049A5`.
- Echo stays on genealogy; no download, mode/tag write, fault/TASK-counter
  clear, clock/power/vendor-state operation, commit or push occurs here.

The [payload manifest](AB_S4B_O8_CONFIGURATION_HEARTBEAT_2026-10-28/artifact_manifest.json)
binds exact logs, source snapshots, 93 completed profile captures, debug failure,
approval/inventory and the independent verifier. Failed launcher/tool checks are
retained. No credential, ACD/BAK or binary is archived.

Prepare WP4b.6/S4b-Q under standing Echo authorization O3. After the candidate
fixture, run the independent configuration comparison, idle equivalence,
generic acquisition, profile desktop and final timing in that order. Each
read-only stage records even if an earlier read-only stage fails. Native E1–E9,
including cumulative TASK maximum/overlaps and genealogy rollback with original
documents and 31 baseline cases, remain required together. S5/S6 and deferred
S7 are still pending. No S4b stage exit is claimed.
