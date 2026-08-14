# Fraktal/AB implementation — fresh-chat kickstart prompt

Copy the prompt below into a new chat opened at the repository root. It is
deliberately an execution prompt, not merely a request for another plan.

```text
You are taking over the Fraktal/AB (Allen-Bradley Logix) implementation in:

C:\Users\Rockwell Automation\Fraktal

Work as the lead implementation and specification agent. Continue until the
next evidence-based phase exit or a real authority/tooling blocker. Do not stop
after summarizing the documents or proposing another high-level plan.

PRIMARY DECISION RULE

The ordered Fraktal Core objectives are the architecture authority. Getting as
close as possible to O1–O10 is more important than reproducing TwinCAT's exact
classes, call graph, OOP structure, OPC UA mechanics, or folder layout.

TwinCAT is:

- the first binding and the strongest behavioral/test oracle currently present;
- evidence for required observable semantics, edge cases, recovery and operator
  experience; and
- a source of reusable ideas where they suit Logix.

TwinCAT is not:

- a mandatory implementation architecture for Allen-Bradley;
- authority for carrying `EXTENDS`, `SUPER^`, interfaces, references, TF6100 or
  TwinCAT browse mechanics into platform-neutral Core; or
- justification for rejecting a native Logix mechanism that meets the Core
  objectives better.

When requirements, objectives and platform mechanics conflict, use this rule:

1. Preserve the objective and observable Core behavior.
2. Do not silently violate a normative `shall`. If a purportedly neutral Core
   clause actually mandates a TwinCAT mechanism, amend Core explicitly first and
   bind the obligation separately in TC3 and AB.
3. Prefer the simplest native Logix mechanism that satisfies the behavior.
4. Change AB Part III when the binding mechanism is wrong; change implementation
   when code is wrong; change Core only when the neutral obligation is wrong or
   mechanism-specific; use a novel mechanism when neither existing answer meets
   the objectives.
5. Record the objective impact, trade-off, compatibility effect and evidence.
   Never weaken an objective merely to declare the port complete.

OBJECTIVE ORDER

Use the full normative wording in `Specification/Fraktal_Core_Part_I.md` §1.1.
The working order is:

O1  low development and maintenance effort;
O2  easy to learn from any PLC background and free sequence-language choice;
O3  diagnosable by construction;
O4  reusable, recursive and scalable structurally and at runtime;
O5  flexible data and connectivity;
O6  simulatable without changing module logic;
O7  safe, with certified safety independent and read-only to standard logic;
O8  portable through a neutral Core plus platform bindings;
O9  good engineering: one authority per fact, minimum surface, versioning and
    continuous machine-enforced conformance;
O10 industrial robustness: validation, bounded deterministic storage, fail-closed
    behavior, no stale-command replay, warning-clean builds and honest evidence.

If two solutions are otherwise conforming, choose the one that better serves the
earlier objective. O9/O10 remain cross-cutting constraints, not permission to
damage O1–O8.

READ FIRST — CURRENT SOURCES OF TRUTH

Read these files before changing anything, in this order:

1. `AGENTS.md`
2. `Specification/Fraktal_Core_Part_I.md`, especially §1.1, §1.5, §2.2,
   §3.10–§3.14, §5.5–§5.7, §6, §7.7–§7.8, §8, §9, §10 and §11
3. `Specification/ALLEN_BRADLEY_PORT_PLAN.md`
4. `Specification/Fraktal_AB_Part_III.md`, especially AB §0, R0–R6, every
   `[PROVISIONAL Sn]` clause, AB §3.1–§3.5, §5 and §12
5. `Specification/AB_IMPLEMENTATION_PLAN.md`
6. `Specification/AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md`
7. `Specification/AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md`
8. `Specification/AB_S1_CIP_DATA_PATH_EVIDENCE.md`,
   `Specification/AB_S2_AOI_PARAMETER_EVIDENCE.md`, and
   `Specification/AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md`
9. `Specification/HMI_CONTRACT.md`
10. `Specification/Fraktal_TC3_Part_II.md` and
   `FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md` as behavioral/reference
   evidence—not as mandatory AB structure
11. `Specification/FIRST_PROJECT_AGENT_GUIDE.md` for phase/evidence discipline

Inspect `git status` first. The worktree may contain changes made outside the
chat. Preserve them, do not reset them, and do not overwrite overlapping work.
Re-read files immediately before editing because external changes can arrive
while you work.

CURRENT STATUS AND HARD GATE

Fraktal/AB is draft, **R0-R1 and S1-S2 complete**, and not
runtime-implementation-ready. R2-R6 remain OPEN. Preserve the exact named
workstation/controller evidence and recheck live identity before physical work;
do not redo completed acquisition merely because a new chat started.

Only these are authorized before R0–R6 pass:

- specification/Core-binding amendments;
- generators, linters and non-production host tooling needed to establish the
  gates;
- disposable Phase 0 Logix/L5X/EtherNet-IP test fixtures; and
- tests/evidence supporting those items.

Do not begin or present production runtime/module-library code as conforming
until Part III R0–R6 are all recorded PASS. A failed spike changes the binding,
narrows an explicit optional claim, or stops the port; it never becomes an
undocumented exception.

BEHAVIOR TO PRESERVE; MECHANISMS FREE TO CHANGE

Preserve the Fraktal semantics and operator outcome:

- recursive Unit / Equipment Module / Control Module model and legal containment;
- `ParCfg` / `ParCmd` / `OutCmd` / `OutImm` contract;
- PLCopen command handshake, Execute-drop reset, abort, held/recoverable state,
  one-reset recovery and no unsafe self-resume;
- mode ownership/cascade and sequence semantics;
- precise pending-step, awaited-child, first-out and alarm/event diagnostics;
- PLC-authoritative release/access/act-or-explain behavior;
- recipe prepare/commit/abort and migrate-or-fault behavior;
- traceability, bounded history, time/quality semantics and reason-code authority;
- HAL-based real/simulation equivalence;
- independent certified safety boundary;
- live self-description and the same generic HMI domain/UI behavior without
  station-specific or module-type screens; and
- bounded, deterministic, fail-closed execution and connectivity.

You are free to replace TwinCAT mechanisms such as inheritance, interfaces,
references, methods, constructor injection, TF6100 browse inheritance and OPC UA
transport with generated composition, UDT contexts, numeric handles, bounded
registries/manifests, native Logix routines/AOIs or a better proved design.

KEY AB DECISIONS ALREADY MADE — VERIFY, DO NOT BLINDLY ASSUME

- EtherNet/IP explicit messaging plus a Fraktal gateway is the default HMI/
  self-description path. OPC UA is an optional projection, not a prerequisite.
- S1 selected hash-pinned pylogix `1.1.5` as the initial private PLC-facing
  adapter. It passed the named v33 target's symbolic type, fragmentation,
  External Access, transport/recovery/concurrency, and time matrix. The gateway
  boundary remains versioned and allow-listed; arbitrary CIP `Message()` is not
  exposed.
- S2 proved one public UDT `Ctx` InOut through eight physically executing nested
  AOIs, complex STRING and atomic parameter classes, private/member External
  Access, cleanup, and signature-upgrade behavior. The pinned v33 hard limits
  are 64 InOuts and 16 invocation levels; Fraktal's generated nesting ceiling is
  eight. Production contract sizes remain S12.
- Controller event time comes from WallClockTime with TimeSynchronize quality.
  The current disposable fixture is PTP-disabled/unsynchronized, so publish
  `TimeSynchronized=FALSE` and retain gateway reception time separately.
- Native Studio 5000 SFC is supported. It is not an AOI primary routine and an
  AOI cannot `JSR`/`SFR`; Part III therefore proposes program-owned SFC routines
  with generated JSR/SFR runners and one stateful chart/tag set per deployed
  owner. ST/LD AOI sequences remain the reusable reference form.
- SFC actions publish sequence intent/services only; all module AOIs still run
  unconditionally exactly once. S4/S11 must prove L5X fidelity, ordering,
  one-scan intent/result latency, reset/re-entry, branches and restart behavior.
- Safety Tag Mapping is standard-to-safety, not safety-to-standard. The proposed
  standard-task adapter reads permitted controller-scoped safety state and never
  writes safety authority.
- The flat registry, manifest and numeric keys are candidate AB mechanisms and
  potential Core improvements, not sacred designs. Replace them if evidence
  finds a solution that better meets the objectives.

FIRST EXECUTION ORDER

1. Reconcile current reality.
   - Inspect the worktree and the Allen-Bradley tree.
   - Audit Core/Part III/port/implementation plans for drift, including the full
     O1–O10 set and every provisional-spike/register reference.
   - Discover installed Rockwell tooling, licensed SDK/Echo availability and any
     named isolated controller information without modifying a controller.
   - Report facts, not assumptions.

2. Verify that the recorded R0, R1, S1, and S2 PASS evidence still agrees with Part
   III. Repair only real drift; do not repeat the completed baseline, physical
   matrix, AOI/access matrix, or clock set. The isolated controller currently
   holds the eight-level memory-only S2 nested-AOI fixture in Remote Run with
   its command/text inputs cleaned. Use
   the runbook for its serial, USB path, Ethernet route, rollback hash, and
   current authorization boundary.

3. Freeze only the logical Phase 2 contracts that do not require invented
   hardware numbers: manifest, registry identity, root request/ack mailbox,
   HostEvents and repository-protocol negotiation. Leave capacities, layouts and
   budgets explicitly provisional until their spikes provide evidence.

4. Run the remaining Phase 0 blocker spikes in evidence-driven order. Start with
   S11, then finish S4/S15 and S12, followed by S7/S8/S9. Include a minimal
   ST/SFC parity chain generated from one graph declaration. Do not hand-author
   L5X and call it round-trip evidence.

5. Update Part III provisional clauses and R0–R6 with exact evidence. Only after
   all readiness gates pass, proceed through port-plan Phases 3–8: communication
   vertical slice, runtime base, generator/gates, reusable modules, AB integration
   bench/generic-HMI proof, and final clause/objective audit.

IMPLEMENTATION DISCIPLINE

- Use primary Rockwell/ODVA documentation for platform claims; record exact
  publication, software/firmware/controller versions and URLs.
- Derive generated AOIs, UDTs, L5X, manifests, registries and schedules from one
  authoritative declaration. Generated artifacts are never hand-maintained.
- A project call needed for correctness is a framework/generator defect. Remove
  repeated wiring instead of documenting it.
- Add the machine-checkable gate with the feature: lifecycle ordering,
  exactly-once cyclic calls, containment, registry/manifest agreement, keys,
  external access, mailbox, sequence/SFC graph, retention, safety and type map.
- Keep public/external access minimal: published data read-only, private state
  inaccessible, mutation through the narrow acknowledged root mailbox and always
  re-authorized by the PLC.
- Build simulation and automated tests with each behavior. Verify observable
  parity against Core/TC3 tests where relevant, not implementation shape parity.
- Never download to, alter or discover-select a production controller. Use only
  an explicitly named isolated target and obtain user authorization before any
  download or external state change.
- If required hardware/tooling/licensing is unavailable, exhaust read-only local
  discovery, then give the user exact acquisition/setup/run instructions and
  continue every useful non-hardware task. Do not fabricate PASS evidence.
- Keep documentation synchronized as decisions change. Distinguish proven,
  provisional, excluded and failed claims explicitly.

VALIDATION AND PHASE HANDOFF

For each phase or material decision, leave:

- changed files and authoritative-source rationale;
- Core clauses and O1–O10 impact;
- exact commands/tool versions/controller identity;
- build/lint/test results and captured diagnostics;
- provisional assumptions still open;
- regression/compatibility/security implications; and
- the next safe action or exact user assistance needed.

Before finishing any turn, run the relevant repository consistency tests and
`git -c core.whitespace=cr-at-eol diff --check`, inspect the final diff for
unrelated changes, and do not claim compilation/runtime evidence that was not
actually produced. The explicit whitespace setting honors the repository's
intentional byte-preserving CRLF policy (`.gitattributes` `* -text`).

START NOW

Begin with step 1 and then execute the maximum safe work currently possible.
Do not merely restate this prompt. Lead with what you discovered and changed.
```
