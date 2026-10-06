# Fraktal/AB S16 — command handshake and mode execution: declaration and import package

**Spike:** S16 command-handshake and mode execution on Logix (new)

**Result:** **DECLARED AND GENERATED, NOT YET EXECUTED. The Core §6.1 handshake
and the §6.2 mode chain are expressible on Logix with no runtime base structure
invented — the whole contract fits one UDT and two AOIs using only types S12
proved. The generator, its executor and 46 unit tests are in the repository and
the AB suite is green at 208. Nothing is proved on a controller yet: import,
Studio v33 Verify and execution all require the licensed v33 workstation.**

**Date:** 2026-09-06

**Repository revision at start:** `493a495`

## 1. What this is, and what it is not

This is a **disposable Phase 0 fixture**, not the press demo application and not
a runtime base. It is press-*shaped* — one module-shaped AOI, a mode owner with
two chains, a plant simulated entirely in controller tags — because that shape
is what exercises §6.1. It is not press logic.

**Deliberately excluded, and enforced by a test** (`test_scope_excludes_runtime_base_structure`):
recipes, release reports, part traceability, the HMI contract, the
mailbox/registry/manifest contracts, a reusable module library, and production
naming. The test fails the build if the string `Recipe`, `ParCfg`, `Manifest`,
`Registry`, `Mailbox`, `Traceability` or `ReleaseReport` appears in the
generated L5X.

**No control-power or Control On circuit exists.** Task output updates are
disabled, the embedded `Discrete_IO` module is inhibited, the generator refuses
any `Local:`/`Discrete_IO:` operand, and the plant is arithmetic on controller
tags. Nothing electrical is represented — the same posture as the S1, S2, S9
and S11 fixtures.

**No Rockwell licensed tool was used.** This workstation has no Studio v33 and
its Studio/SDK entitlement is not established
([`AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md`](AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md)).
Everything here is Python generation and unit test.

**Controller-changing operations this session: none.** The bench still holds the
S9 coherence fixture.

## 2. The headline finding, available before execution

**The §6.1 handshake did not require inventing runtime base structure.** That
was the stated stop condition — "if the handshake cannot be expressed WITHOUT
inventing runtime base structure, stop at the declaration and record that as the
finding". It can be expressed, so the spike proceeds to an import package.

The entire contract fits:

- **one UDT**, `FRK_T_S16Ctx`, 39 `DINT` members grouped by Core §3.12 role —
  `Par_*`, `ParCmd_*`, `OutCmd_*`, `OutImm_*`, the PLCopen signals, and the
  evidence counters the fixture uses to measure itself;
- **two AOIs** — `FRK_S16_Axis` (the module, owning the handshake and the
  simulated plant) and `FRK_S16_Mode` (the mode owner, owning the two chains);
- **one program, one routine, one task.**

Three consequences worth carrying into Phase 3:

1. **Every scalar is a `DINT`, including the booleans.** S12 removed `TIME`,
   `TIME32` and `LREAL` from this baseline and made `LINT` transport-only, so
   `Par_TimeoutMs` and `ElapsedMs` are range-checked `DINT` milliseconds
   integrated from the task rate (AB §3.8). The handshake booleans are carried
   as 0/1 `DINT` to stay inside the UDT layout S12 actually measured. A
   production binding may prefer `BOOL` members; **that layout is not yet
   measured**, and this record does not claim it.
2. **`ExecState` and `Held` are separate members, not one enumeration.** Core
   §6.1 is explicit that `Held` is *not* an `E_ExecState` ordinal and those
   ordinals shall not be renumbered. The fixture keeps `OutImm_ExecState` on the
   fixed 0–4 ordinals and `OutImm_Held` beside it.
3. **The ordering rule is structural, not conventional.** The module AOI is
   called unconditionally at the top of the main routine and the mode owner
   second; the mode owner then *checks* that the module already ran this scan
   and increments `OrderFail` if it did not. The fixture detects its own
   ordering violation rather than relying on the author having got the call
   order right.

## 3. A real ambiguity in Core §6.1 that this fixture had to resolve

**Core §6.1 does not say what happens when a command is HELD past its timeout.**
Two clauses in the same section pull opposite ways:

- the timeout clause: "On timeout the module raises `Error` and promotes that
  diagnostic to `ErrorID`";
- the Held clause: while held a module "**shall not** raise `Error`" and
  "progress resumes on its own when the condition returns".

A command held longer than its timeout satisfies the precondition of both.

**The fixture freezes the elapsed-time accumulator while Held**, so a held
command never times out, and a test (`test_timeout_does_not_accumulate_while_held`)
enforces that the `ElapsedMs` update is absent from the held branch. The reason:
Held exists precisely to distinguish "the operator let go of the enabling
device" from "the machine is broken", and a hold that silently matures into a
fault destroys that distinction — the operator would be shown a fault for having
done the designed thing.

**This is a fixture decision, not a Core amendment.** It is recorded here because
**Phase 3 must settle it in Core §6.1 explicitly**, one way or the other. If Core
decides a held command *should* eventually time out, the fixture is wrong and
cheap to change; what is not acceptable is leaving each binding to guess.

## 4. Generated declaration

| Item | Value |
|---|---|
| Context UDT | `FRK_T_S16Ctx`, 39 members, all `DINT` |
| Module AOI | `FRK_S16_Axis` (`Ctx` InOut, `Scan`/`Hold`/`Fault` Inputs) |
| Mode owner AOI | `FRK_S16_Mode` (`Ctx` InOut, `Scan`/`Sel`/`Run` Inputs) |
| Program / routines / tasks | 1 / 1 / 1 |
| Task | `FRK_S16Task`, PERIODIC, 10 ms, watchdog 500, `DisableUpdateOutputs="true"` |
| AUTO chain steps | `N000` init, `N100` move A, `N110` move B, `N999` finish → loops (Core §6.2/§6.5) |
| MANUAL behavior | one command per request, no cycling |
| `E_ExecState` ordinals | READY 0, BUSY 1, DONE 2, ERROR 3, ABORTED 4 |
| Reason codes (fixture-scoped) | held permissive 6101, device fault 6102, timeout 6103, abort request 6104 |
| Severity | held = LOW (0); fault/abort = HIGH (2) |
| Plant | position 0–100, 25 units/scan → 4 scans per move; default timeout 500 ms |
| Physical I/O references | **0** |
| Embedded I/O | **inhibited** |

The reason codes are deliberately **fixture-scoped numbers, not `E_Reason`
entries**. A disposable fixture must not add members to a Core enumeration.

## 5. Bounded write surface

The executor may write exactly five controller tags and writes nothing else. A
test asserts that the whole vector's writes are a subset of this set, and
`_write()` raises `AssertionError` on any tag outside it:

`FRK_S16_Command`, `FRK_S16_Abort`, `FRK_S16_ModeSelect`,
`FRK_S16_HoldRequest`, `FRK_S16_FaultRequest`

All five are restored to zero by `_disarm()`, which runs in a `finally` block so
it executes even when a phase raises, and reports `FAILED` per tag rather than
hiding a failed restore.

The executor additionally requires `--expect-serial`, an explicit
`--execute-fixture` arm flag, and a fixture fingerprint (`SchemaVersion`,
`Par_Speed`, `Par_TimeoutMs`, and a running scan counter) that must pass
**before the first write**. A fingerprint miss reports `"wrote": false`.

## 6. Artifacts and hashes

| File | SHA-256 |
|---|---|
| `tools/fraktal_ab_s16_fixture.py` | `F9579BE24AD20A124BDF027F5A9BD55968608856A7B06F80062646D00E06F86C` |
| `tools/fraktal_ab_s16_execute.py` | `19A50E0287B110D207F396A2122796F3A2D61688FC35981A6BBC6269F7A7216B` |
| `tools/test_fraktal_ab_s16_fixture.py` | `B96296543AFB4FBB700906C5BE5A1590DA8919F3581901D856CCC0BFED26E379` |
| `tools/test_fraktal_ab_s16_execute.py` | `3BB2EAACFF5B0176A95C261D42A0C525FB976B2C779C524277D44A83C563EE3B` |

**The generated L5X is deliberately not hashed here.** It is a function of the
seed it is generated from, and the real seed can only be created through the
SDK `--create-seed` path on a licensed workstation. A structural dry run against
a hand-written stub seed produced a well-formed L5X with 2 AOI definitions, 39
context members, 1 routine and 0 physical-I/O references, which proves the
generator runs end to end — **it is not the artifact that gets imported**, and
its hash would be misleading. The v33 workstation records the real hash.

## 7. Import package for the licensed v33 workstation

Run every step on the Studio v33 workstation, per
[`AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md`](../AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md).
**Do not attempt any of it on the 2026-09-06 VM.**

### 7.1 Create the seed and generate the fixture

```powershell
# 1. Seed, through the SDK - never hand-authored
bin\Debug\net10.0\win-x86\Fraktal.Ab.OfflineProbe.exe `
  --create-seed 1769-L24ER-QB1B 33 FraktalPhase0 C:\work\seed_v33.ACD `
  --export C:\work\seed_v33.L5X

# 2. Generate the S16 fixture from that seed
python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_s16_fixture.py `
  C:\work\seed_v33.L5X C:\work\s16_fixture.L5X
```

Record the emitted JSON. `PhysicalIoReferences` shall be `0`,
`EmbeddedIoInhibited` and `TaskOutputUpdatesDisabled` shall both be `true`.

### 7.2 Import and Verify

```powershell
# 3. SDK import, with the log gate - a bare exit code is not an import gate
python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_sdk_log_gate.py <import-log>

# 4. Studio v33 Verify Controller, proving the input ACD unchanged
FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_studio_verify.ps1
```

### 7.3 Verify acceptance criteria

| Check | Required result |
|---|---|
| SDK import | `Warnings="0" Errors="0"` |
| Studio v33 **Verify Controller** | **0 errors, 0 warnings** |
| Dead code | no "routine not referenced" warning — the fixture has exactly one routine, reached as `MainRoutineName` |
| Canonical round trip | export and compare with `fraktal_ab_l5x_compare.py`; structurally identical |
| Construct census | `fraktal_ab_l5x_inventory.py` reports 2 AOI definitions, 1 UDT, 1 program, 1 routine, 1 task |
| Physical I/O | zero `Local:`/`Discrete_IO:` operands in the exported file |

Studio Verify is the semantic gate. **SDK `BuildAsync` alone is not semantic
verification** and shall not be recorded as one.

### 7.4 Download — only under fresh authorization

The bench currently holds the **S9 coherence fixture**, and its rollback path is
recorded in [`AB_S9_COHERENCE_EVIDENCE.md`](AB_S9_COHERENCE_EVIDENCE.md).
**Preserve the ability to return to it.** A download requires the user's fresh
explicit authorization and an exact target check immediately before use —
serial `7036B510`, firmware `33.014` — with all I/O disconnected. Prior
authorization is historical and shall not be inferred.

## 8. Execution matrix — defined, not yet run

Run with the repository's fixed probe and hash-pinned `pylogix 1.1.5` in a venv
**outside** the repository:

```
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s16_execute.py 192.168.100.89 \
    --expect-serial 7036B510 --execute-fixture
```

| # | Phase | Expectation |
|---|---|---|
| 1 | `auto_cycle` | AUTO chain reaches `CycleCount >= 1` with no Error and no Aborted |
| 2 | `abort_no_resume` | `Aborted` raised, ABORTED state, `Busy` stays clear afterwards — **no self-resume** |
| 3 | `execute_drop_ready` | dropping Execute mid-BUSY returns `ExecState` to READY with `Busy` clear |
| 4 | `held_low_reason` | BUSY + `Held` + reason `6101` at severity LOW + **`Error` clear** |
| 5 | `held_auto_resume` | clearing the condition resumes progress **with no re-issue** |
| 6 | `fault_error_id` | `Error` + `ErrorID = 6102` + ERROR state |
| 7 | `restart_by_reissue` | a fresh Execute edge restarts the command after the fault |
| 8 | `mode_switch_midcycle` | mode change observed, chain stands down to its init step |
| 9 | `ordering_and_latency` | `OrderFail = 0` and `LatencyBad = 0` across the whole run |

Every phase reports `elapsed_ms` and the observed context. Values are reported as
status and shape; the record carries `values_redacted: true`.

Phase 9 is the S11 ordering rule restated for commands: the module AOI ran
unconditionally ahead of sequence intent on **every** scan, and the interval
between the chain raising Execute and the module accepting the edge was
**exactly one scan** every time.

## 9. Test coverage

46 new unit tests; the whole AB suite is green at **208** (was 162).

| Suite | Tests | Covers |
|---|---:|---|
| `test_fraktal_ab_s16_fixture.py` | 21 | well-formed XML; exactly two AOIs; only S12-proved types; duration as `DINT` ms; module called before mode owner; ordering self-check present; Execute-drop reset; latch on rising edge only; held is BUSY + LOW + no Error; timeout frozen while held; abort terminal; fault carries ErrorID; all five ExecStates reachable; no physical I/O; I/O inhibited and output updates disabled; single reachable routine; write surface; **scope exclusion**; overwrite refusal; wrong-source rejection; hashes |
| `test_fraktal_ab_s16_execute.py` | 25 | serial normalization and rejection; arm flag required; bounded settle; write surface is the five tags; writing outside it raises; vector never writes outside it; disarm clears everything; disarm reports failure; fingerprint accept/reject/stopped-controller/unreadable; all nine phases run; good run passes; ordering violation fails; bad latency fails; **held-that-errors fails**; held at wrong severity fails; reads failing mid-vector fail closed |

The negative tests matter more than the positive ones here: a probe that cannot
fail is not evidence. `test_held_that_raises_error_fails_the_vector` is the one
that would catch a binding quietly turning a hold into a fault.

## 10. What this means for the Phase 3 runtime design

1. **The handshake needs no base class and no framework object.** One context
   UDT passed as a single `InOut`, plus generated composition, carries the whole
   §6.1 contract. That supports AB §3.14's "composition plus generation" claim
   against Part II's inheritance, at least for the command lifecycle.
2. **Ordering must be generated and checked, not documented.** The fixture
   detects its own violation in one line. Phase 3's generator should emit the
   same self-check rather than rely on a lint rule about call order.
3. **The duration decision propagates further than S12 stated.** Every timeout,
   elapsed time and watchdog in the runtime is a `DINT` of milliseconds
   integrated from a known task rate. That means **the task rate becomes part of
   the contract**: a fixture or module moved to a task of a different period
   silently changes its own timeouts. Phase 3 needs an explicit rule here.
4. **Core §6.1 owes an answer on held-plus-timeout** (§3 above).
5. **The `BOOL`-member UDT layout is unmeasured.** If Phase 3 wants real `BOOL`
   members in a public contract UDT, that is an S12 rerun, not an assumption.

## 11. Status

| Item | State |
|---|---|
| S16 declaration and generator | **complete, tested, in the repository** |
| S16 import package | **complete; needs the licensed v33 workstation** |
| S16 execution matrix | **defined; not run** |
| S16 spike | **OPEN** |
| R0–R6 | unchanged; **no gate state changes on this record** |

No conformance claim is made. No production Fraktal/AB runtime or module-library
code was written, and none is authorized until every R0–R6 gate records PASS.
