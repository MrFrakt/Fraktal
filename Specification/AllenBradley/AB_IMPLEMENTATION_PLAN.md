# Fraktal/AB — Implementation Plan
*How to start the Allen-Bradley port from where the documents now stand*

**Status:** working plan — **R0–R3 PASS; S1, S2, S4, S7, S11 and S12 complete; R4–R6 open** — derived from `ALLEN_BRADLEY_PORT_PLAN.md` (the *why* and
the phase structure) and `Fraktal_AB_Part_III.md` (the *binding* and its readiness
gates). Those two are authoritative; where this plan disagrees with them, they win
and this file is wrong.

---

## 1. Where the port actually stands

No production runtime exists in `FraktalCore/PLC/Allen-Bradley/`. Only
disposable Phase 0 fixtures and their generators/probes exist. Under explicit
authorization with all I/O disconnected, the verified memory-only v33 fixture
and its expanded revision were downloaded to and executed on the isolated controller; this is R2
evidence, not runtime code. The authority-only R0 phase and the R1 platform
baseline are complete:

- Part III records **R0–R1 PASS** and remains **spike-ready, not
  implementation-ready**. Runtime and library code **shall not** begin until all
  R0–R6 gates record PASS. Only disposable Phase 0 fixtures are permitted before then.
- The spike list grew from S1–S10 to **S1–S15**. The new ones are not
  refinements; two of them invalidate design decisions the previous draft had
  already made.
- The base-port blocker set is **S1, S2, S4, S7, S8, S9, S11, S12, S15**.
  **S1, S2, S4, S7, S11 and S12 are PASS**, which closes **R2** and gives
  **R3** its resolved capacities. S8, S9 and S15 remain unresolved.

**The next executable steps are S8, S9 and S15.** The design decisions for S8
and S9 are now settled and recorded in
[`AB_S8_S9_DECISION_RECORD.md`](Evidence/AB_S8_S9_DECISION_RECORD.md) — CIP Security on
v37+ recommended with zone/conduit as the legacy posture, a read-only initial
claim whose write switch arms Core §14 in full, TC3's tier model, parity as the
shared repository contract suite rather than an A/B rig, a mailbox payload
bounded to one unfragmented write, crash testing scoped to five replay-capable
boundaries, and redundancy out of scope. What remains for both is **evidence,
not deliberation**, and some of it is already in:
[`AB_S8_SECURITY_EVIDENCE.md`](Evidence/AB_S8_SECURITY_EVIDENCE.md) records that the
Phase 0 controller implements none of the CIP Security object classes and that
the required allow-list audit now runs, while
[`AB_S9_COHERENCE_EVIDENCE.md`](Evidence/AB_S9_COHERENCE_EVIDENCE.md) records that the
retry-until-stable guard never accepts a torn snapshot and converges whenever
the mutation interval exceeds the guarded read window. S15 is the unattended
build gate and still needs its decision. The completed Core amendments and TC3 compatibility audit are
recorded in [`AB_R0_CORE_AUTHORITY_EVIDENCE.md`](Evidence/AB_R0_CORE_AUTHORITY_EVIDENCE.md);
the named platform baseline is in
[`AB_R1_PLATFORM_BASELINE_EVIDENCE.md`](Evidence/AB_R1_PLATFORM_BASELINE_EVIDENCE.md).

### 1.1 Two design corrections worth reading before anything else

The documentation review corrected two things the earlier drafts got wrong.
Both change what gets built, so they are not editorial:

Both were subsequently confirmed by evidence rather than left as assertions:
S11 executed the two-form design on the physical controller, and the safety
adapter direction is unchanged by it.

**Native SFC is supported, but not inside an AOI.** Studio 5000 supports SFC as
a main or JSR-called program routine. The real call-boundary restriction is that
an AOI cannot `JSR` a project Routine and its primary logic cannot be SFC. Part
III therefore defines two forms: a reusable generated ST/LD sequence AOI, and a
program-owned native-SFC Unit/EM chain with one stateful routine/tag set per
deployed owner, called by a generated JSR/SFR wrapper. The SFC writes sequence
intent only; the root/module AOIs still execute unconditionally once and consume
that intent on the next scan. **S4** had to prove the chart's L5X round trip and
**S11** the ordering, the intentional one-scan command/result loop,
reset/re-entry, prescan/restart and branch parity. **Both now pass** for ST and
native SFC on the pinned v33 baseline — the two forms measured scan-for-scan
identical — so SFC is enabled within that proved surface; see
[`AB_S11_SEQUENCE_EXECUTION_EVIDENCE.md`](Evidence/AB_S11_SEQUENCE_EXECUTION_EVIDENCE.md).
Generated Ladder, alternative branches and the abort/hold/mode-exit edges are
not covered by it.

**Safety Tag Mapping was the wrong mechanism.** The old draft called it a
"one-way safety → standard" publication path and praised it as a closer fit to
Core §9 than TwinCAT's convention. It is the opposite direction: Tag Mapping maps
*standard* tags into *safety* tags for safety logic. The correct path is a
generated standard-task adapter that **reads controller-scoped safety tags
directly** — Logix permits standard logic to read but not write them. A binding
that shipped on the old sentence would have been describing a mechanism that does
not exist.

Both corrections are the spike programme working as intended, before code rather
than after.

---

## 2. What can start now, and what cannot

| Work | Blocked by | Needs Rockwell? |
|---|---|---|
| **Phase 1 Core amendments** (R0) | **complete** | no |
| Manifest / mailbox / HostEvents **logical** schemas (R3) | **complete** | no |
| Gateway protocol negotiation design (AB §11.3) | **complete** as a frozen field/order contract; wire encoding is implementation work | no |
| Capacity resolution and polling budgets | S7 / S9 | **yes** |
| Everything else | R4–R6 | **yes** |

The 2026-08-12–13 audit found Studio 5000 Logix Designer v21–v37 and
Logix Designer SDK 2.00 installed, with the SDK service running. It identified
an authorized isolated `1769-L24ER-QB1B/A` at firmware `33.014` over USB and
proved SDK activation with a harmless offline ACD open/export. The named Phase 0
host adapter is `192.168.100.99/24`; its direct EtherNet/IP route reaches the
same controller at `192.168.100.89:44818` and matches the USB serial identity.
The completed baseline and the remaining out-of-scope production-conduit work
are recorded in
[`AB_R1_PLATFORM_BASELINE_EVIDENCE.md`](Evidence/AB_R1_PLATFORM_BASELINE_EVIDENCE.md).
R1, S1, and S2 are PASS. S1 proved identity, namespace, controller/program scope,
structured, STRING, array and fragmented reads/writes, External Access,
cleanup, conservative connection/concurrency/reconnect/timeout budgets, and
wall-clock quality on the downloaded memory-only fixture. The initial
PLC-facing adapter is hash-pinned pylogix `1.1.5`; see
[`AB_S1_CIP_DATA_PATH_EVIDENCE.md`](Evidence/AB_S1_CIP_DATA_PATH_EVIDENCE.md).
S2 then proved the one-UDT-`InOut` public contract through eight physically
executing nested AOIs, complex STRING and atomic parameter classes, private
instance/local visibility, member External Access, signature upgrade behavior,
and the v33 64-InOut/16-invocation hard boundaries. Fraktal freezes its
generated nesting ceiling at eight; see
[`AB_S2_AOI_PARAMETER_EVIDENCE.md`](Evidence/AB_S2_AOI_PARAMETER_EVIDENCE.md).
Studio 5000 v33 also positively connected through the confirmed FactoryTalk
Linx Ethernet path, while Studio and SDK Ethernet uploads timed out. Studio
subsequently completed a read-only upload through USB at `Backplane\16` with
zero errors and warnings, and the upload-derived v33 project passed a canonical
SDK conversion round trip plus Studio's offline **Verify Controller** with zero
errors and warnings. The exact fresh-chat access workflow and remaining
Ethernet/SDK limitation are in
[`AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md`](AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md).
Studio v37 also rejected the disposable invalid-ST fixture with two errors,
proving the controlled Error List path fails closed where SDK Build did not.
Studio v33 then imported, verified, and downloaded the generated fixture over
USB with zero errors or warnings; its cyclic results and memory-tag matrix
passed over EtherNet/IP, and all writable inputs were cleaned. The exact
rollback/artifact hashes and controller state are in
[`AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md`](Evidence/AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md).
**Do not attempt to fake a spike with a hand-written L5X
file** — S4 exists precisely because L5X round-trip fidelity is unproven, and a
file this repo generates without an import/export cycle proves nothing.

---

## 3. The plan

### Step A — Phase 1 Core amendments — COMPLETE (R0)

The two authority amendments are complete. Their normative crosswalk, TC3 audit,
tooling audit and O1–O10 review are in `AB_R0_CORE_AUTHORITY_EVIDENCE.md`.

**A1. OOP-neutral lifecycle (Core §2.2 / §3.14 / §5.5) — complete.**
Core names the **obligation** — behavior is defined once and reused; a concrete
type supplies device logic only; the lifecycle runs in a fixed order — and Part II
binds it to inheritance while Part III binds it to generated composition.

The original surface included 9 occurrences of `EXTENDS`/`SUPER^` and an ST-only
framework rule. The amendment changed the owning semantics rather than merely
renaming tokens.

*Exit met:* Part I states required behavior without naming a platform mechanism;
Part II binds the TC3 mechanism; the TC3 conformance claim is re-audited and
unweakened.

**A2. Transport-neutral self-description (Core §3.10 / §4.8 / §7.7 / §11) — complete.**
Core defines the **Fraktal Self-Description Service** as a behavioral contract;
Part II binds TF6100/OPC UA, while Part III makes EtherNet/IP plus the Fraktal
gateway the default and OPC UA an alternative projection.

The original audit found **64** OPC UA mentions, including mandatory base-service
mechanics. The amendment retains OPC UA where it is a provider option or an
explicit binding-qualified profile and removes it as a base-service prerequisite.

*Exit met:* the TC3 mechanism remains bound in Part II; no base Core conformance
`shall` requires TF6100/OPC UA; the normative diff and O1–O10 impact are reviewed.

The R0 exit is recorded in Part III's readiness table. It authorizes spikes and
Phase 2 contract work, not production runtime/library implementation.

### Step B — Phase 2 documentation gates that need no hardware — COMPLETE (R3)

The **logical** schemas are frozen: registry, manifest tables, root mailbox
request/response, value envelope, protocol negotiation and the HostEvents ring,
each at version 1 in
[`AB_FROZEN_CONTRACTS_V1.json`](AB_FROZEN_CONTRACTS_V1.json). Part III's prose
remains normative; `tools/check_ab_contracts.py` fails the build when the two
disagree, when a field uses a type the baseline records as unavailable, or when
a capacity claims to be resolved without a value and its evidence.

S7 has since resolved eight of the nine `FRK_MAX_*` capacities at measured
sizes; `FRK_MAX_MAILBOX_ARGUMENTS` remains S9's. Five further holes name S3, S7,
S9 and S12. A generator shall refuse to emit a deployable artifact while a
symbol it needs is unresolved.

Still explicitly **not** frozen: final physical UDT layout beyond the S12-measured
type map and stride rule, capacities, and production forest polling budgets.
Those are S3/S7/S9 outputs; S1's 500-byte/four-reader ceiling is only the
conservative transport baseline for those later proofs. The exit is recorded in
[`AB_R3_FROZEN_CONTRACTS.md`](AB_R3_FROZEN_CONTRACTS.md).

### Step C — Phase 0 spikes (needs the platform)

Run in blocker order. S1/S2/S4/S7/S11/S12 are complete and R2/R3 are closed, so
proceed **S8, S9 and S15** before any gateway or runtime library work. The
minimal ST/SFC parity chain the S4/S11 fixtures were required to carry exists
and passed; the rule that produced it still stands for every later chart —
generate both forms from one graph declaration and do not start with a
production-sized chart.

Prerequisite before any spike runs — R1: a named controller catalogue number,
firmware revision, Studio 5000 edition and version, communication module, and
gateway-host baseline. "A ControlLogix" is not a baseline.

### Step D — everything after

Phases 3–8 as written in the port plan. They do not need re-planning here; they
need R0–R6 to be PASS first.

---

## 4. What this plan does not decide

- **Whether the port should happen.** That is a go/no-go at the Phase 0 exit, and
  it is a real decision — S4 (L5X fidelity) and S15 (automatable Verify/Build)
  can each end the port as drafted.
- **Which controller family.** R1, and it constrains everything downstream.
- **Whether motion, connectors, or OPC UA projection are in scope.** S13/S14/S10
  gate only their own optional families; none blocks the base port.

---

## 5. Working rules for whoever picks this up

1. **Never cite a `[PROVISIONAL Sn]` clause as evidence.** Part III says this in
   AB §0 and it is the single easiest rule to break by accident.
2. **A failed gate changes the binding or stops the port.** It does not become an
   undocumented implementation exception.
3. **Do not write runtime or library code before R0–R6 are PASS.** Disposable
   Phase 0 fixtures are the only exception, and they are disposable — do not let
   one graduate into the base by being useful.
4. **The documents are the source of truth.** This plan summarises; it does not
   override. Read AB §0 and the port plan's §7 phase list directly.
