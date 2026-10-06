# Fraktal/AB — fully-licensed workstation handover prompt

Copy the text below into a new coding-agent chat opened at the cloned repository
root on the engineering PC that carries the complete, legitimately licensed
Rockwell toolchain. Written 2026-09-06; it supersedes the resume state in
`AB_IMPLEMENTATION_KICKSTART_PROMPT.md` and
`AB_STUDIO5000_IMPLEMENTATION_HANDOVER_PROMPT.md`, both of which describe the
programme as it stood at the R0–R1 / S1–S2 stage.

## Precondition on the previous host, before cloning here

Clone from `https://github.com/MrFrakt/Fraktal.git`. At the time of writing the
previous development host (`C:\Projects\Fraktal`, HEAD
`6989e09f7be17c218283bc47139baa8a98c85d75`) still holds **uncommitted** v38
exploratory work. Commit and push these five files first, or they will not
exist on the licensed PC:

1. `Specification/AllenBradley/Evidence/AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md` (new)
2. `FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s12_type_probe.py`
3. `FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_s12_type_probe.py`
4. `FraktalCore/PLC/Allen-Bradley/README.md`
5. `Specification/AllenBradley/AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md`

## Expected baseline on the licensed PC

| Item | Why it is required |
|---|---|
| Studio 5000 Logix Designer **v33** | matches the bench controller firmware 33.014; v33 regression gate and any online/upload work |
| Studio 5000 Logix Designer **v38** | v38 S12 acceptance cases and Studio Verify |
| **Logix Designer SDK** (2.02+) with an issued **`LDSDK.EXE`** activation feature | the single item that unblocks S15, R4, and the v38 acceptance rerun |
| Logix **Echo** (+ Echo SDK) — optional | R5 test execution on a soft controller instead of the bench |
| FactoryTalk Activation Manager, FactoryTalk Linx / RSLinx Enterprise | licence hosting; USB and browse routes |
| Python 3.10+, Git, PowerShell 5+ | the repository gates and probe tooling |
| Adapter on `192.168.100.0/24` (static, e.g. `192.168.100.99`) or USB | reaches the isolated bench controller |

Legitimate entitlements only. Gate evidence produced on cracked, grace-period,
or borrowed activations cannot be recorded — see the boundary in the prompt.

```text
You are resuming the Fraktal/AB (Allen-Bradley Logix) implementation on a
fully-licensed engineering PC. Work from the repository root and continue until
you close the next evidence-based readiness gate or reach a real tool, licence,
controller, or authority blocker. Do not stop after summarizing documents or
writing another high-level plan.

MISSION

This PC exists to remove the one blocker the previous hosts could not: the
Logix Designer SDK licence. Close, in this order:

1. the v38 S12 acceptance rerun (its six required steps are in
   Specification/AllenBradley/Evidence/AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md
   section 7);
2. S15, the unattended build gate, which also closes R4;
3. then R5 (Echo reference suite, if Echo is licensed) and the S8/S9
   remainders that need no new deliberation.

Do not create production Fraktal/AB runtime or module-library code until every
R0-R6 readiness gate in Part III records PASS.

AUTHORITIES AND STANDING DECISIONS

- Specification/Fraktal_AB_Part_III.md is the authoritative AB specification;
  its section 0 readiness table and section 12 spike register define the gates.
- Specification/Fraktal_Core_Part_I.md defines neutral behavior and objectives
  O1-O10. TwinCAT is the behavioral oracle, not a mandatory architecture.
- EtherNet/IP explicit messaging (CIP symbolic access) through a Fraktal
  gateway is the default self-description path; OPC UA is an optional
  projection, never a prerequisite.
- The initial claim is READ-ONLY
  (Specification/AllenBradley/Evidence/AB_S8_S9_DECISION_RECORD.md, S8 D2).
  Enabling
  writes is a gateway configuration decision that arms Core section 14 in
  full; it shall be asked of the user explicitly and recorded, never decided
  by an agent.
- The accepted type-map baseline is the frozen v33 contract in
  Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json. The v38 result is
  exploratory until the
  acceptance rerun completes; a passing rerun adds a SECOND versioned baseline
  alongside v33 and never edits the v33 baseline in place.
- A failed gate changes the binding, narrows an optional claim, or stops the
  port. It never becomes an undocumented exception.

READ BEFORE EDITING

1. AGENTS.md, especially section 3a (Allen-Bradley boundaries)
2. FraktalCore/PLC/Allen-Bradley/README.md (current status narrative)
3. Specification/Fraktal_AB_Part_III.md sections 0 and 12
4. Specification/AllenBradley/Evidence/AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md
5. Specification/AllenBradley/Evidence/AB_S12_V38_PREFLIGHT_BLOCKER_2026-08-26.md
6. Specification/AllenBradley/Evidence/AB_S8_S9_DECISION_RECORD.md
7. Specification/AllenBradley/AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md
8. Specification/AllenBradley/AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md
9. Specification/AllenBradley/AB_IMPLEMENTATION_PLAN.md
10. FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/README.md

Inspect git status, branch, and recent commits first. Preserve all work
already present; never reset or overwrite work you did not create. Re-read a
file immediately before editing it.

CURRENT STATE (verified read-only on 2026-09-02)

- R0, R1, R2, R3: PASS. R4, R5, R6: OPEN.
- S1, S2, S4, S7, S11, S12: PASS. S8 and S9: decided, partly evidenced. S15:
  OPEN, blocked exactly on the SDK licence this PC provides.
- The isolated bench controller is 1769-L24ER-QB1B/A LOGIX5324ER, firmware
  33.014, serial 7036B510, at 192.168.100.89:44818. It is in Remote Run
  holding the clean S9 coherence fixture (FRK_S9_* tags readable); the clock
  is UTC with PTP disabled. Earlier README sentences saying an S12 or S7
  fixture is resident are stale - S9 replaced it on 2026-08-14.
- Studio v38 cannot go online with this v33 controller. All v33 online work
  needs Studio v33; all v38 work is offline project engineering until v38
  hardware exists.
- The five v38 exploratory files listed in this document's wrapper must be
  present in the clone; if they are missing, stop and report instead of
  regenerating history.

HARD BOUNDARIES

- Never perform a controller-changing operation - download, mode change, tag
  write, fault clear, clock set, firmware, network configuration - without
  CURRENT explicit user authorization and an exact target identity check
  (serial 7036B510, firmware 33.014) immediately before use. Prior
  authorization is historical and shall not be inferred.
- Use only the repository's fixed-vector tools against the controller. Their
  narrow write surfaces, serial guards, and fixture fingerprints are safety
  properties, not boilerplate; do not widen them.
- Do not use pirated, cracked, grace-period, or otherwise illegitimately
  activated tooling for any gate work, and do not record evidence from it.
  If an entitlement is missing, name it exactly and stop that leg.
- Evidence files under Specification/AllenBradley/Evidence/ are append-only
  and dated; never edit a past record to match today.
- No hand-authored production L5X. Generated artifacts are imported, verified,
  exported, and compared through Studio/SDK with hashes recorded.
- Do not cite a [PROVISIONAL Sn] clause as conformance evidence.

STEP 0 - RECONCILE AND RUN THE REPOSITORY GATES

Run from the repository root (resolve python to its full path if the
WindowsApps alias interferes):

    python -m unittest discover -s FraktalCore/PLC/Allen-Bradley/tools -t FraktalCore/PLC/Allen-Bradley/tools
    python tools/check_ab_contracts.py
    python FraktalCore/PLC/TwinCAT/tools/plc_lint.py
    python FraktalCore/PLC/TwinCAT/tools/plc_lint.py --profile 4024
    python tools/check_consistency.py inventory localization parity
    python -m unittest tools.test_check_consistency
    git -c core.whitespace=cr-at-eol diff --check

Expected: 162+ AB tool tests OK, contract gate clean, lint clean in both
profiles. For live read-only probes, install hash-pinned pylogix 1.1.5 from
FraktalCore/PLC/Allen-Bradley/tools/requirements-phase0.txt into a venv
OUTSIDE the repository. Report facts, not assumptions.

STEP 1 - RECORD THIS WORKSTATION AS A NEW BASELINE ADDENDUM

R1 is already PASS for the previous workstation; this PC needs its own dated
addendum before any evidence it produces is citable. Record, read-only first:
Windows build; Studio v33 and v38 editions, exact versions, and activation
state; SDK version plus positive proof the LDSDK.EXE feature is issued (the
recorded harmless proof is an offline ACD open/export through the SDK -
Fraktal.Ab.OfflineProbe); Linx/RSLinx version; the 192.168.100.x adapter or
USB route; Python and Git versions. Link the addendum from the tool catalog
and note it in the next evidence record's baseline section.

STEP 2 - EXECUTE THE V38 S12 ACCEPTANCE RERUN

Follow
Specification/AllenBradley/Evidence/AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md
section 7 exactly:

1. Run the unchanged v33 Phase 0 regression gate
   (FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_phase0_gate.py; add
   --verify only with a logged-in desktop session) and require every stage
   green. Create the v33 seed through the SDK --create-seed path so the chain
   regenerates from this checkout.
2. Regenerate the v38 seed and all 32 cases through the approved workflow:
   python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s12_type_probe.py
   <v38-seed.L5X> <output-dir> --profile v38-5380-exploratory
   With the SDK licensed, create the 5069-L310ER revision 38 seed through
   the SDK rather than by hand.
3. SDK-import every case and record warnings and errors through
   tools/fraktal_ab_sdk_log_gate.py; a bare exit code is not an import gate.
4. Studio-Verify every imported case while proving the input ACD unchanged
   (tools/fraktal_ab_studio_verify.ps1 proves the hash; it refuses
   repository-contained ACDs and pre-existing Studio sessions).
5. Rerun all four typed-literal and matched-operand duration supplements.
6. Write the dated acceptance evidence record. Only if every stage is green:
   add a second VERSIONED frozen baseline alongside v33 in
   Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json (versioned addition,
   never an in-place edit), update
   Part III section 12, the AB README, and the tool catalog. If any stage
   fails, record the failure and its diagnostic verbatim; do not narrow the
   acceptance criteria to fit the result.

STEP 3 - CLOSE S15 AND R4

S15 requires unattended or controlled SDK automation for import, Verify/Build,
diagnostics extraction, export and round-trip comparison, from a clean
checkout. The regeneration gate
(FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_phase0_gate.py) is its
backbone; extend automation only where a stage is still manual, and keep every
generated-vs-exported census and canonical comparison in the run. Also retry
the open Ethernet question on this PC (Studio upload over
Fraktal_AB\192.168.100.89 previously timed out; USB worked) - a clean
Ethernet upload here closes the last S15 scope question. Any download leg
against the bench needs fresh authorization and the exact target check.

STEP 4 - R5 AND THE S8/S9 REMAINDERS

- R5: a disposable reference AOI suite through Logix Echo (if licensed) or
  the named isolated bench, emitting machine-readable results. LogixEmulate
  (classic) is NOT Echo; substituting it is a binding change, not a shortcut.
- S8: if a v37+ CIP Security-capable controller is available, demonstrate the
  CIP Security configuration and record it. Otherwise draft the legacy
  zone-and-conduit posture and declared Security Level for the v33 bench -
  that is documentation against existing measurements and needs no hardware.
- S9: declare the reference station's freshness thresholds and poll budgets
  from S7's measured costs. The shared repository contract suite and the
  mailbox matrix are adapter/implementation work gated behind R0-R6.

ENGINEERING RULES

- One authoritative declaration generates UDTs, AOIs, routines, L5X,
  manifests, registries and schedules. Generated artifacts are never
  hand-maintained, and generated files are never committed without their
  generator.
- Keep secrets, activation data, credentials and proprietary binaries out of
  the repository and out of logs.
- Bounded, deterministic, fail-closed everywhere; never hide a tooling
  limitation or claim unexecuted evidence.
- Prefer primary Rockwell/ODVA documentation for platform facts; record
  title, revision, URL and the exact software/firmware it applies to.

VALIDATE BEFORE HANDOFF

Run every repository gate from STEP 0 again, plus any new AB generator,
schema or conformance tests added during the session. Inspect the final diff
for unrelated changes. The explicit cr-at-eol setting honors the repository's
byte-preserving CRLF policy (.gitattributes * -text) so hashes stay stable
across machines.

HANDOFF FORMAT

Lead with the gate outcome and its evidence, then changed files, the exact
workstation baseline, commands and results, unresolved provisional clauses
and risks, and the next safe action or the exact user assistance needed. If
blocked, name the missing licence/tool/controller fact precisely while
preserving all completed evidence.

START NOW

Begin with STEP 0 and execute the maximum safe work available. Do not merely
restate this prompt.
```
