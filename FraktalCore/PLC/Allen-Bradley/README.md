# Fraktal/AB

This tree is reserved for the Allen-Bradley Logix binding. The authoritative
implementation specification is
[`Specification/Fraktal_AB_Part_III.md`](../../../Specification/Fraktal_AB_Part_III.md).

Current status: **R0 PASS; R1-R6 OPEN**. No production AB runtime or module
library is authorized until every readiness gate in Part III records PASS.
Before that point, this tree may contain only disposable Phase 0 fixtures and
the evidence, generator, lint, or host tooling needed to close the gates.

The default controller communication path is EtherNet/IP explicit messaging
(CIP symbolic access) through the Fraktal gateway. OPC UA is an alternative
projection, not a prerequisite for base Fraktal/AB conformance.

Start with:

- [`Specification/AB_STUDIO5000_IMPLEMENTATION_HANDOVER_PROMPT.md`](../../../Specification/AB_STUDIO5000_IMPLEMENTATION_HANDOVER_PROMPT.md)
  on the Windows 10 Studio 5000 workstation;
- [`Specification/AB_R0_CORE_AUTHORITY_EVIDENCE.md`](../../../Specification/AB_R0_CORE_AUTHORITY_EVIDENCE.md)
  for the completed R0 decision record; and
- [`Specification/ALLEN_BRADLEY_PORT_PLAN.md`](../../../Specification/ALLEN_BRADLEY_PORT_PLAN.md)
  plus [`Specification/AB_IMPLEMENTATION_PLAN.md`](../../../Specification/AB_IMPLEMENTATION_PLAN.md)
  for spike and phase order.

Do not hand-author production L5X. Generated artifacts must be imported,
verified, exported, and compared through Studio 5000, with the exact software,
firmware, controller, and communication baseline recorded as evidence.
