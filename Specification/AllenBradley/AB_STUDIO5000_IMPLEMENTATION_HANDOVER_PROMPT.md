# Fraktal/AB - Windows 10 Studio 5000 handover prompt

Copy the text below into a new coding-agent chat opened at the cloned repository
root on the Windows 10 engineering PC that has Studio 5000 installed.

```text
You are taking over the Fraktal/AB Allen-Bradley implementation on a Windows 10
engineering PC with Studio 5000 installed. Work from the repository root and
continue until you close the next evidence-based readiness gate or reach a real
tool, licence, controller, or authority blocker. Do not stop after summarizing
documents or writing another high-level plan.

OUTCOME

Preserve the proved Rockwell platform baseline and S1/S2 results, then close the
next highest-priority disposable Phase 0 blocker needed to determine whether a
conforming Fraktal/AB implementation is possible. Do not create production AB
runtime/module-library code until every R0-R6 readiness gate in Part III is
recorded PASS.

AUTHORITIES AND DECISIONS

- `Specification/Fraktal_AB_Part_III.md` is the authoritative Allen-Bradley
  implementation specification.
- `Specification/Fraktal_Core_Part_I.md` defines platform-neutral behavior and
  ordered objectives O1-O10.
- EtherNet/IP explicit messaging using CIP symbolic access between Logix and a
  Fraktal gateway is the default communication and self-description path.
- OPC UA is an alternative projection only. Do not make it a prerequisite and
  do not silently substitute OPC UA for the default EtherNet/IP proof.
- TwinCAT is the strongest behavioral and test oracle, but its inheritance,
  interfaces, references, TF6100, and browse mechanics are not mandatory AB
  architecture.
- Preserve observable Core semantics. Use native Logix mechanisms when they
  meet the objectives better, and update the binding transparently when a
  provisional mechanism fails its spike.
- A failed gate changes the binding, narrows an explicit optional claim, or
  stops the port. It never becomes an undocumented exception.

READ BEFORE EDITING

1. `AGENTS.md`
2. `Specification/Fraktal_AB_Part_III.md`, especially section 0, R0-R6, every
   `[PROVISIONAL Sn]` clause, sections 3-5, and section 12
3. `Specification/AllenBradley/Evidence/AB_R0_CORE_AUTHORITY_EVIDENCE.md`
4. `Specification/AllenBradley/AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md` for the complete
   status-marked inventory of interfaces/tools and the unfinished S11 checkpoint
5. `Specification/AllenBradley/AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md` for the exact
   verified Studio 5000, FactoryTalk Linx, SDK, direct-CIP, and PLC procedures
6. `Specification/AllenBradley/Evidence/AB_S1_CIP_DATA_PATH_EVIDENCE.md` and
   `Specification/AllenBradley/Evidence/AB_S2_AOI_PARAMETER_EVIDENCE.md`
7. `Specification/AllenBradley/ALLEN_BRADLEY_PORT_PLAN.md`
8. `Specification/AllenBradley/AB_IMPLEMENTATION_PLAN.md`
9. `Specification/Fraktal_Core_Part_I.md`
10. `Specification/HMI_CONTRACT.md`
11. `Specification/Fraktal_TC3_Part_II.md` and
   `FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md` as behavioral evidence
12. `Specification/Guides/FIRST_PROJECT_AGENT_GUIDE.md` for phase/evidence discipline

Inspect `git status`, the current branch, and recent commits first. Preserve all
work already present. Re-read a file immediately before editing it. Never reset,
discard, or overwrite work you did not create.

CURRENT STATE AND HARD BOUNDARY

- R0-R1 and S1-S2 are PASS. R2-R6 are OPEN.
- The verified Ethernet route is `Fraktal_AB\192.168.100.89` from host
  `192.168.100.99/24`. Studio 5000 v33 connects and matches the controller
  identity, but Studio and SDK read-only uploads over Ethernet both timed out.
  Studio later completed a read-only upload over USB at `Backplane\16` with
  zero errors and warnings, and the fresh upload-derived v33 L5X passed an SDK
  canonical conversion round trip. Studio's offline **Verify Controller** also
  completed with zero errors and warnings; Studio v37 rejected the disposable
  invalid-ST fixture with exactly two errors, proving the controlled Error List
  path. Follow
  `AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md`; do not resume route-string
  guessing or misstate the remaining issue as a general Studio upload failure.
- The isolated physical controller is `1769-L24ER-QB1B/A`, firmware `33.014`,
  serial `7036B510`. Under explicit user authorization with all I/O disconnected,
  Studio first downloaded the expanded memory-only `FraktalPhase0` fixture
  through USB, returned it to Remote Run, and the fixed EtherNet/IP probes passed
  controller/program scope, DINT/REAL/STRING/UDT, arrays through fragmented 4
  KiB, External Access, cleanup, transport/reconnect/timeout/concurrency, and
  wall-clock cases. Inputs are clean; the clock is aligned to host UTC with PTP
  disabled and `TimeSynchronized=FALSE`. The rollback ACD and exact hashes are
  in `AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md` and shall not be committed.
  S2 later replaced that fixture with the verified eight-level nested-AOI
  fixture. Its UDT/STRING InOut execution, atomic parameters, member/private
  External Access, cleanup, 64-InOut/16-level v33 boundaries, signature upgrade
  rules, and exact post-download target binding passed. The controller is in
  Remote Run with the S2 command/text inputs clean; see
  `AB_S2_AOI_PARAMETER_EVIDENCE.md`.
- S1 selected hash-pinned pylogix `1.1.5` as the initial private PLC-facing
  adapter. Do not expose arbitrary CIP `Message()` forwarding. Repository and
  browser security remain owned by the future transport-neutral gateway.
- No production Fraktal/AB runtime has been implemented or proved.
- Before R0-R6 all pass, permitted work is limited to specification/schema
  changes, generators and linters, non-production host tooling, disposable
  Logix/L5X/EtherNet-IP fixtures, and their tests/evidence.
- Do not download to or modify a production controller. Use FactoryTalk Logix
  Echo or an explicitly named isolated test controller. A download or other
  external state change requires clear user authorization and an exact target.
- Do not treat a hand-written L5X file as Studio 5000 round-trip evidence.

STEP 1 - DISCOVER AND RECORD THE R1 BASELINE

Use read-only discovery first. Record facts and the commands/screens/APIs that
proved them:

1. Windows edition/build and engineering-PC identity/role.
2. Studio 5000 Logix Designer edition, exact version/build, installed controller
   profiles, and active licence/activation status.
3. Logix Designer SDK version/licence and callable automation surface.
4. FactoryTalk Logix Echo and Echo SDK version/licence, or the exact isolated
   controller catalogue number, firmware revision, chassis/slot, and ownership.
5. EtherNet/IP communication adapter/module and complete CIP route/path.
6. Gateway-host baseline: OS, CPU/architecture, Python/runtime versions,
   network interfaces/VLAN/firewall boundary, and whether it is this PC or a
   separate deployment host.
7. Initial conformance scope: the mandatory EtherNet/IP gateway path and any
   separately requested optional OPC UA projection.

Keep credentials, activation data, controller keys, and private network secrets
out of the repository and logs. If one baseline item cannot be discovered,
continue every independent read-only task and report the exact missing input.

Create a dated, reproducible R1 evidence record in the repository and link it
from the Part III readiness table. Mark R1 PASS only when every mandatory
baseline item is named and usable. Do not infer a controller or firmware family.

STEP 2 - EXECUTE BLOCKER SPIKES IN THIS ORDER

R1, S1, and S2 are complete. Run S11 next, then finish S4/S15 and S12. After those
blockers, run S7, S8, and S9. S10, S13, and S14 gate their optional scopes only.
Follow Part III section 12 and the port plan for exact acceptance criteria.

For every spike, leave:

- the exact question and related `[PROVISIONAL Sn]` clauses;
- controller, firmware, Studio/SDK/Echo, communication, and host baseline;
- a minimal disposable fixture derived from one authoritative declaration;
- reproducible import/create/verify/build/run/export steps;
- source-controlled text artifacts (normally L5X, declarations, scripts, and
  reports) without proprietary binaries or secrets unless repository policy
  explicitly permits them;
- raw diagnostics plus a concise PASS/FAIL result and limitations;
- packet traces, timing, sizes, and scan impact where the criterion requires
  them; and
- the resulting Part III disposition: proved clause, revised mechanism,
  narrowed optional scope, or blocking failure.

Required emphasis:

- S1 (PASS): preserve
  `Specification/AllenBradley/Evidence/AB_S1_CIP_DATA_PATH_EVIDENCE.md`; production-scale freshness,
  manifest batches, and mailbox acknowledgement remain S3/S7/S9, not reasons to
  reopen the completed physical data/time-path spike.
- S2 (PASS): preserve `Specification/AllenBradley/Evidence/AB_S2_AOI_PARAMETER_EVIDENCE.md`; final
  production type sizes remain S12 and lifecycle/restart behavior remains S11,
  not reasons to reopen the completed AOI parameter/access spike.
- S4/S11: generate a minimal ST/LD reference sequence and native Studio 5000 SFC
  rendition from the same graph declaration. Import and export it through
  Studio 5000; verify actions, transitions, branches, JSR/SFR ownership,
  unconditional exactly-once module execution, intentional one-scan
  intent/result latency, reset/re-entry, prescan, warm restart, and fault
  recovery. SFC actions publish intent only.
- S15: prove unattended or controlled SDK automation for import, Verify/Build,
  diagnostics extraction, and export/round-trip comparison. A manual green
  screenshot is useful evidence but does not close the automation gate.
- S12: finish the Logix/Core type map, including widths, signedness, strings,
  time bases, timestamps, quality, arrays, nested records, serialization, and
  rejection of unsupported or ambiguous values.
- S7: prove bounded manifest/discovery/read-tier capacities and the polling
  budget at target scale.
- S8: prove the EtherNet/IP security conduit, allow-list/routing/firewall model,
  least privilege, gateway identity and TLS-facing side, and fail-closed loss of
  trust.
- S9: prove mailbox sequencing, acknowledgement, authorization, timeout,
  duplicate handling, reconnect behavior, and no stale-command replay.

Do not cite a provisional clause as evidence. Resolve, rewrite, or explicitly
leave it blocked. Update Part III, the evidence cross-links, and readiness status
as results arrive. Do not mark R2-R6 PASS from document review alone.

ENGINEERING RULES

- One authoritative declaration shall generate UDTs, AOIs, routines, L5X,
  manifests, registries, schedules, and conformance expectations. Generated
  artifacts are not hand-maintained.
- Project wiring required for correctness is a generator/framework defect.
  Correctness gates must prove lifecycle order, exactly-once cyclic execution,
  containment, sequence graph agreement, manifest/registry/key agreement,
  external access, retention, mailbox behavior, type mapping, and safety
  boundaries.
- Published data is read-only. Mutation uses the narrow acknowledged root
  mailbox and is re-authorized in the PLC.
- Certified safety remains independent. Standard logic may observe permitted
  safety state but never grants, maps, or writes safety authority.
- Keep all storage and execution bounded, deterministic, versioned, and
  fail-closed. Never hide a tooling limitation or claim unexecuted evidence.
- Prefer primary Rockwell and ODVA documentation for platform facts. Record the
  title, revision/date, URL, and exact applicable software/firmware version.

VALIDATE BEFORE HANDOFF

Run the relevant Studio 5000 Verify/Build/export automation and capture its
diagnostics. Also run the repository gates from the repository root, resolving
`python3` to its installed full path if the WindowsApps alias is unavailable:

    python3 FraktalCore/PLC/TwinCAT/tools/plc_lint.py
    python3 FraktalCore/PLC/TwinCAT/tools/plc_lint.py --profile 4024
    python3 -m unittest discover -s FraktalCore/PLC/TwinCAT/tools/ -t FraktalCore/PLC/TwinCAT/tools/
    python3 tools/check_consistency.py inventory localization parity
    python3 -m unittest tools.test_check_consistency
    git -c core.whitespace=cr-at-eol diff --check

Run any new AB generator, schema, gateway, and conformance tests you add. Inspect
the final diff for unrelated changes. Do not claim controller, SDK, security, or
runtime evidence that was not actually produced. The explicit `cr-at-eol`
setting is required because this repository deliberately preserves CRLF bytes
with `.gitattributes` `* -text` so source hashes remain stable across machines.

HANDOFF FORMAT

Lead with the gate outcome and evidence, then list changed files, exact platform
baseline, commands and results, unresolved provisional clauses/risks, and the
next safe action. If blocked, name the missing licence/tool/controller fact and
give precise setup or acquisition instructions while preserving all completed
evidence.

START NOW

Begin with repository inspection and R1 discovery. Execute the maximum safe work
available on this workstation; do not merely restate this prompt.
```
