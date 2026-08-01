# Second review of `OBJECTIVES_AUDIT.md`

Review date: **2026-07-31**. Scope: verify the audit's findings, its gap closures,
and its own verification claims. Method: re-run every check the audit says it ran,
re-run the ones it says it could not, and independently sample the `DONE` claims.

**Headline.** The audit's *factual* claims are accurate — every number I could
check reproduced exactly. Its *process* claim is not: it states the conformance
linter "could not run on this workstation", and on that basis marks G9 `DONE`.
Python 3.14.6 is installed and the linter runs. When run, it reports **6
violations**, all of which are false positives in rules the same pass authored.
So the gate that was declared complete has never been executed against the
codebase it is meant to gate, and in its current state it would **fail CI**.

Nothing here contradicts the audit's central conclusion: the repository is not
entitled to a conformance claim until the P0 items close. The corrections below
change *which* items are open, not that verdict.

---

## 1. Verification of the audit's own claims

| Audit claim | Result | Evidence |
|---|---|---|
| Flutter suite green, 161 passed / 4 skipped | ✅ reproduced | 163 passed / 4 skipped (163 includes 2 contrast guards added after the snapshot) |
| HMI/gateway/client static analysis clean | ✅ reproduced | `flutter analyze` — no issues |
| 264 PLC XML documents parse | ✅ exact | 264 parsed, 0 failures |
| 260 `<Compile Include>` paths resolve | ✅ exact | 260 items, 0 unresolved |
| Reason catalog `--check` green | ✅ reproduced | exit 0 |
| Force capability defaults false, no app enables it | ✅ verified | only `M_SetForceable`'s own return assigns `TRUE` |
| "no Python runtime available" → G9 `DONE` | ❌ **false** | Python 3.14.6 present; linter runs; **6 violations** |
| 28 TcUnit suites / 89 `TEST(...)` | 🟡 slightly off | **27** suites / **86** `TEST(...)`; all 27 registered in the runner, none orphaned |

The counting discrepancy is immaterial to conformance. The Python claim is not:
it is the difference between a gate that is *written* and a gate that *works*.

---

## 2. Primary finding — G9 is not `DONE`

`tools/plc_lint.py` runs in both profiles and reports the same 6 violations:

```
[D1] FB_Iv3VisionCM   lacks contract member(s): ParCfg, ParCmd, OutCmd, OutImm
[D1] FB_Matrix220CM   lacks contract member(s): ParCfg, ParCmd, OutCmd, OutImm
[C5] FB_SequenceBase:58  CASE has no ELSE fail-safe reaction
[S1] FB_PressDemoChangeover  6 step branches but only 5 M_Advance calls
[S1] FB_PressDemoHome        3 step branches but only 2 M_Advance calls
[S1] FB_PressDemoLoadPosition 4 step branches but only 3 M_Advance calls
```

I inspected all six. **All are false positives**, and each one contradicts a
principle the audit itself asserts:

- **D1 ×2.** `FB_Iv3VisionCM EXTENDS FB_TcpVisionCM`; the contract members are
  *inherited*. The rule does not follow `EXTENDS` (`grep EXTENDS tools/plc_lint.py`
  → 1 hit, unused for this check). This contradicts §2.2 — behaviour written once
  at the owning level and inherited — which is the framework's core premise. The
  audit's own §4 bullet claims it "restored the physical four-structure contract";
  the rule as written would forbid inheriting it.
- **C5 ×1.** `M_Advance` sets `target := -1` *before* the `CASE` and guards with
  `IF target >= 0`. That is a semantic fail-safe. The audit explicitly reconciled
  this in §4: *"guard returns are valid, empty `ELSE` noise is not required"* —
  its linter enforces the opposite.
- **S1 ×3.** The uncounted branch is the **terminal** step (`999:` → `M_Complete()`
  / `Done := TRUE`), which must not advance. The rule has no notion of a terminal
  step, so every correct finite chain trips it.

**Why this matters beyond three bad rules.** The fixture suite
(`tools/test_plc_lint.py`) passes — 9 tests, green — because it exercises only
synthetic snippets. A gate validated exclusively against its own fixtures, never
against the tree it guards, cannot detect that its rules encode the wrong
invariant. This is the same class of error as a unit test that asserts the
implementation rather than the requirement.

**CI impact.** `.github/workflows/ci.yml:51` runs the linter over
`FraktalCore/PLC/TwinCAT` for both profiles. On the first run after the untracked
tree is committed, `plc-lint` **fails**. The `plc-compile` job is already a
deliberate `exit 1` stub, so CI has never been green; that has masked this.

*(One correction to an inference I made mid-review: CI line 53's
`python -m unittest tools/test_plc_lint.py` does work — Python accepts the path
form. Only a bare `python tools/test_plc_lint.py` fails, and CI does not use it.)*

---

## 3. Second finding — G10 severity is understated

The audit rates G10 "not releaseable" and assigns it P0, which is right. The
magnitude is worth stating plainly, because it governs every other item:

- **275 untracked files** under `FraktalCore/PLC`
- **253 deletions** staged against the former paths
- **303 untracked files** repo-wide

The entire PLC framework — Core, Modules, all 27 test suites — exists **only in
this working tree**. A clean clone today yields a repository with no PLC source.
Every `DONE` in §5 that rests on PLC code is therefore unreproducible by anyone
else, including the compile/TcUnit evidence P0 asks for. This is not merely
"hygiene": it is the precondition for all remaining evidence.

---

## 4. Assessment of the audit's judgement calls

Independently sampled; I agree with these and note them so they are not re-opened:

- **Scoring O3/O4/O5/O7/O9/O10 as 🟡 rather than ✅** is correct and
  appropriately conservative given no compile/TcUnit run.
- **Treating the Press Demo as an internal fixture, not a conformance target,**
  is a sound scope call. Cabinet constants are commissioning evidence.
- **The `ALARM_HISTORY` boundary note** (§2, last paragraph) is honest: a UI
  policy cannot secure a raw OPC UA browse, and it says so rather than claiming
  a confidentiality property it does not have.
- **Fail-closed `Forceable`** — verified. Suppressing an unfinished force path by
  capability rather than by UI is the right shape.
- **Refusing an unqualified conformance claim** despite many closures.

One judgement I would tighten: §5 uses `DONE` for items whose exit evidence is
explicitly deferred ("execution remains part of P0"). `DONE` and "source-complete,
unverified" are different states, and G9 shows the risk of conflating them — it
was marked `DONE` while both unrun *and* wrong. Recommend a distinct `SOURCE-ONLY`
status so the scoreboard cannot overstate readiness.

---

## 5. Remediation plan

Ordered by whether the item blocks other evidence.

### R0 — unblock the gate — ✅ **COMPLETED 2026-07-31**

All five items are done. Result: `plc_lint` reports **255 files clean in both
profiles**, the fixture suite is **16 tests green**, and the CI lint step passes
as written. Details and one notable discovery are recorded after the table.

| # | Action | File | Exit evidence |
|---|---|---|---|
| R0.1 | **D1: follow `EXTENDS`.** Resolve the base chain and treat a contract member as satisfied when declared on any ancestor. If the base is outside the scanned set, skip rather than fail. | `tools/plc_lint.py` | `FB_Iv3VisionCM`/`FB_Matrix220CM` clean; a genuinely contract-less CM still fails (add negative fixture) |
| R0.2 | **C5: accept semantic fail-safes.** Suppress when the `CASE` is preceded by a defaulted target and followed by a guard, or every branch assigns a variable checked immediately after. Align the rule text with §4's reconciliation. | `tools/plc_lint.py` | `FB_SequenceBase` clean; a `CASE` with no default and no guard still fails |
| R0.3 | **S1: model terminal steps.** Exclude branches that call `M_Complete()` / set `Done := TRUE` from the `M_Advance` count. | `tools/plc_lint.py` | 3 Press chains clean; a non-terminal step missing `M_Advance` still fails |
| R0.4 | **Run the linter against the real tree in the fixture suite.** Add a test that asserts `plc_lint` returns 0 violations over `FraktalCore/PLC` — so fixtures can never again pass while the codebase fails. | `tools/test_plc_lint.py` | Suite fails if any rule regresses against real source |
| R0.5 | Re-run both profiles; confirm 0 violations. | — | `plc_lint: N file(s) clean` ×2 |

R0.1–R0.3 are rule corrections, **not** relaxations: each keeps a negative
fixture proving the rule still catches the violation it was written for.

#### R0 outcome

| Item | Result |
|---|---|
| R0.1 D1 follows `EXTENDS` | Done. Walks the ancestor chain, stopping at the tier bases (which deliberately do not declare the four). |
| R0.2 C5 accepts semantic fail-safes | Done via `_has_default_then_guard`: recognised only when a variable is defaulted immediately before the `CASE`, written by its branches, and tested in an `IF` immediately after. A `CASE` with no default or no guard still fails. |
| R0.3 S1 excludes terminal steps | Done. Branches are split per step; those calling `M_Complete()` or setting `Done := TRUE` are not required to advance. |
| R0.4 real-tree guard | Done — `test_linter_is_clean_against_the_real_repository` runs both profiles over `FraktalCore/PLC`, mirroring `main()` (per-file rules take the profile, cross-file rules do not). |
| R0.5 verification | `plc_lint`: 255 clean ×2 profiles. Fixtures: 16 green. CI step as written: clean. Flutter: 163 passed / 4 skipped, unchanged. |

**A latent hole surfaced while adding the negative fixtures.** The original D1
fixture asserted only that *some* `D1` finding appeared, and its
`ST_BadParCfg.TcDUT` triggered the schema-first branch — so the assertion passed
without the *contract* branch ever firing. Isolating a contract-less CM showed it
produced **no finding at all**: D1's four-structure check had never actually
caught anything in fixtures. The corrected rule now reports it, and reports it
through an intermediate base as well:

```
contract-less CM (direct base)  -> D1 shipping module FB_Bad lacks ...
contract-less via intermediate  -> D1 FB_Leaf ... + D1 FB_Middle ...
```

So R0.1 made D1 **strictly more capable**, not weaker — the opposite of the usual
risk when a rule is narrowed to clear false positives. It also reinforces the
review's central point: a fixture that asserts "some finding of this rule class"
can pass while the branch under test is dead. The new fixtures assert the
specific positive *and* negative case for each corrected rule.

### R1 — make the snapshot reproducible (P0, blocks everything downstream)

| # | Action | Exit evidence |
|---|---|---|
| R1.1 | Stage the `PLC/TwinCAT/{Framework,Tests and Examples}` move as a recorded rename + the 275 untracked sources; stage authored HMI/tool/test files. Exclude build output, `Dependancies`, XAE `.~u`, `.dart-*`, credentials. | `git status` clean except intended work |
| R1.2 | Verify from a **clean clone**: XML parse (264), compile-path resolve (260), `flutter analyze`, `flutter test`, reason-catalog `--check`, `plc_lint` both profiles. | All green in a fresh clone |

Until R1 lands, no other result is evidence — it cannot be reproduced.

### R2 — honest scoreboard (small, prevents recurrence)

| # | Action |
|---|---|
| R2.1 | Introduce `SOURCE-ONLY` status in §5; re-label every `DONE` whose exit evidence says "execution remains part of P0". |
| R2.2 | Correct §6 counts to 27 suites / 86 `TEST(...)`, and replace "no Python runtime available" with the linter's actual result. |
| R2.3 | Add a standing rule: a tool may not be marked complete until it has run against the real tree, not only fixtures. |

### R3 — unchanged from the audit

G1 (compile/TcUnit + real CI job), G4 (`FB_EcFieldbusScanner`), G8 (host-event +
§8.9 rationalization), and P1–P3 stand as written. I found no reason to re-scope
them, and no additional gap the audit missed.

---

## 6. What I did not verify

Stated so this review is not mistaken for evidence it cannot provide:

- **No TwinCAT compile, no TcUnit execution.** No compiler in this environment.
  Every PLC claim here is source-level, exactly as the audit says.
- **No live PLC, OPC UA, gateway, or hardware acceptance.**
- **Not every `DONE` was re-derived.** I sampled the highest-risk ones (G3
  manifest, G9 lint, reason catalog, force capability, access policy) and ran the
  suites backing them. G5 gateway and G6/G7 were checked by their tests passing,
  not by re-reading the protocol against §11.
- **The 6 linter violations were triaged by reading the flagged code**, which is
  sufficient to classify them as false positives, but the corrected rules must be
  re-run before R0 can be called closed.
