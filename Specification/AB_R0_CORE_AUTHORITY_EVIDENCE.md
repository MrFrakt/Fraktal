# Fraktal/AB R0 — Core Authority Evidence

**Gate:** R0 Core authority

**Result:** **PASS**

**Date:** 2026-08-10

**Scope:** specification authority only; this is not Rockwell compile, download,
controller-runtime, gateway, security, or conformance evidence.

## 1. Decision

Fraktal Core now states the lifecycle and self-description obligations without
requiring TwinCAT OOP or OPC UA as their implementation mechanisms:

- one binding-owned lifecycle implements the Core command/state behavior in a
  fixed order and is reused by every concrete module;
- bindings may prove that reuse with inheritance or with machine-checked generated
  composition; project authors do not reproduce correctness wiring;
- lifecycle extensions have binding-neutral ordering and one-shot semantics;
- the Fraktal Self-Description Service defines live hierarchy, typed values,
  quality/freshness/timestamps, bounded read tiers, acknowledged mutation,
  version negotiation, canonical identity and conduit-appropriate endpoint security independently of
  a wire protocol; and
- transport and companion-model claims are binding-qualified. A missing optional
  OPC UA projection does not invalidate base Core conformance.

`Fraktal_AB_Part_III.md` is the Allen-Bradley implementation specification. It
binds the neutral authority as follows:

- **default:** EtherNet/IP explicit messaging (CIP symbolic access) between the
  Logix controller and one Fraktal gateway, then the versioned Fraktal repository
  protocol to the generic HMI;
- **alternative:** OPC UA, embedded or gateway-projected, only where the named
  deployment proves it; and
- **lifecycle mechanism:** generated AOI/routine/UDT composition with structural
  gates, not inheritance.

## 2. Normative crosswalk

| Authority surface | Core obligation after R0 | TC3 binding | AB binding |
|---|---|---|---|
| Core §1.1/§1.5 | deterministic cyclic behavior; mechanism-neutral base conformance; binding-qualified projections | `Fraktal/TC3`; optional projections named in the claim | `Fraktal/AB`; optional OPC UA/companion projections named in the claim |
| Core §2.2 | one authoritative fixed-order lifecycle; no project correctness wiring | base-FB inheritance and `Cyclic()` | generated `Begin`/dispatch/`End` composition |
| Core §3.2 | logical capabilities; bounded, fail-closed lookup | IEC interfaces and `__QUERYINTERFACE` | registry indices and capability bits |
| Core §3.10 | transport-neutral Self-Description Service | TF6100 OPC UA namespace rooted at deployed instances | `FRK_Manifest`/registry/value services over EtherNet/IP through the gateway |
| Core §3.11 | exactly-once, order-safe setup owned by framework/generation | `FB_init` plus one-shot `Setup` for child ordering | generated first-scan setup routine |
| Core §3.14 | fixed lifecycle-extension catalogue and ordering; `OnModeExit` exception | protected virtual methods; `SUPER^` first except staged `OnModeExit` | generated optional callouts; framework phase first except staged `OnModeExit` cancel phase |
| Core §4.8 | one local hierarchy segment and one dotted canonical identity across projections | TF6100 browse segment plus `Status.Name` | manifest local-name/canonical-path keys |
| Core §5.5/§5.7 | binding-defined framework language; observable behavior and generation are tested | ST/OOP framework plus TcUnit | AOI/routine/UDT generation plus controller-resident harness (pending R2–R5) |
| Core §7.7/§11 | application authorization above secured transport; acknowledged, no-replay mutation | TF6100 session/security plus Unit mailbox | controlled CIP conduit plus gateway identity/TLS and root mailbox (pending S8/S9) |

## 3. TC3 compatibility audit

The amendment does not remove or relax the TC3 mechanism:

- `Fraktal_TC3_Part_II.md` continues to require TwinCAT OOP for the TC3 framework.
- TC3 §3.14 now explicitly binds Core's neutral lifecycle to base-FB inheritance,
  protected virtual extensions, `SUPER^` ordering and the staged `OnModeExit`
  exception.
- TC3 §3.10/§11.1 continues to bind the Self-Description Service to TF6100,
  deployed-root DA markers, TMC symbol publication, filtered browsing and the
  acknowledged root mailbox.
- The existing `FB_ModuleBase` implementation was inspected as the observable
  lifecycle oracle. The Core order preserves its command edge/reset,
  initialization, cyclic/rollup, abort, BUSY dispatch, held/timing/terminal,
  diagnostic/publication and one-shot-release responsibilities.

This is a specification compatibility audit, not a new TwinCAT build claim.

## 4. O1–O10 objective audit

| Objective | R0 effect |
|---|---|
| O1 low effort | Common lifecycle remains written once; generated composition prevents repeated project wiring. |
| O2 approachable/language choice | Core no longer makes OOP literacy a cross-platform prerequisite; each binding may use its native reviewable forms. |
| O3 diagnosable | First-out, step, quality/freshness and canonical-path semantics are unchanged and now explicitly part of the transport-neutral service. |
| O4 scalable | Bounded discovery/read tiers remain mandatory; AB may publish only declared manifest/capability rows rather than a broad controller tag tree. |
| O5 flexible connectivity | EtherNet/IP is the AB default, OPC UA remains an alternative, and both feed one repository contract. |
| O6 simulatable | HAL and behavior contracts are unchanged; AB simulation evidence remains gated by S5/R5. |
| O7 safe | Certified safety authority remains independent; transport/gateway changes do not grant safety authority. |
| O8 portable | Core now specifies obligations separately from TC3 and AB mechanisms, making the second binding structurally permissible. |
| O9 engineering discipline | Core, TC3 and AB each own one level of fact; generated artifacts derive from one declaration and require agreement gates. |
| O10 robustness | Bounded storage, fail-closed schema/handle validation, acknowledged mutation, explicit data quality and no reconnect replay remain mandatory. |

No objective is weakened to pass R0. The AB generation/gateway proposals remain
unproved until their named spikes and readiness gates pass.

## 5. Local tooling and platform audit

Read-only discovery on the current host found no usable Rockwell baseline:

- no Studio 5000/Logix Designer, RSLogix 5000, FactoryTalk Logix Echo, Logix/Echo
  SDK executable, FactoryTalk Activation Manager or RSLinx executable on `PATH`;
- no standard Rockwell Automation/FactoryTalk install roots under Program Files
  or ProgramData;
- no matching installed-product registry entry, service or running process; and
- no `.ACD`, `.L5X`, `.L5K` or other controller project/baseline artifact in the
  workspace.

Therefore R1–R6 remain **OPEN** and no S1–S15 result is claimed. A hand-authored
L5X file would not close any gate because import/export fidelity and unattended
Verify/Build are themselves provisional evidence questions.

## 6. Next blocking acquisition (R1)

Before a Phase 0 spike can produce valid platform evidence, record and provision:

1. controller family and exact catalogue number;
2. controller firmware revision;
3. Studio 5000 Logix Designer edition, exact version/build and licence;
4. Logix Designer SDK and FactoryTalk Logix Echo/SDK versions and licences, or a
   named isolated hardware CI runner;
5. EtherNet/IP communication module/path and the gateway-host OS/runtime/network
   baseline; and
6. whether the initial claim includes only the default EtherNet/IP gateway path or
   also an optional OPC UA projection.

Until R1 is complete, the repository may advance specification, schema, generator,
lint and disposable-fixture work only. Production AB runtime/module-library code
remains prohibited by Part III R0–R6.

## 7. Validation performed

- Targeted `git -c core.whitespace=cr-at-eol diff --check` passed for the tracked
  R0 specification files.
- Trailing-whitespace checks passed for the new/untracked R0 plan and evidence
  files.
- Every local Markdown link added or used by the changed R0 documents resolves.
- Part III contains exactly seven readiness rows (`R0`–`R6`), and every
  `[PROVISIONAL S1]`–`[PROVISIONAL S15]` marker is represented in AB §12 with no
  unregistered spike.
- The user's interactive terminal reports Python 3.14.6. The managed repository
  shell cannot resolve its `python3` WindowsApps alias, so the gates were executed
  explicitly with the installed `C:\ProgramData\spyder-6\python.exe` (Python
  3.11.13).
- `tools/check_consistency.py inventory localization parity` passed with **0
  errors** and 52 non-failing, pre-existing missing-localization warnings. The
  current no-argument CLI form rejects an empty check list, so all three declared
  checks were named explicitly.
- `python -m unittest tools.test_check_consistency` passed: **12 tests**.
- Both PLC lint profiles passed: **283 files clean** under `modern` and `4024`.
- The combined documented unit gate passed: **84 tests** across
  `tools.test_plc_lint`, `tools.test_tcunit_to_junit`,
  `tools.test_ld_rung_gen`, and `tools.test_check_consistency`.

The repository-wide `git -c core.whitespace=cr-at-eol diff --check` also passes.
The explicit setting is required because `.gitattributes` deliberately uses
`* -text` to preserve CRLF bytes for evidence-hash fidelity; plain
`git diff --check` otherwise misclassifies the retained carriage returns as
trailing whitespace.
