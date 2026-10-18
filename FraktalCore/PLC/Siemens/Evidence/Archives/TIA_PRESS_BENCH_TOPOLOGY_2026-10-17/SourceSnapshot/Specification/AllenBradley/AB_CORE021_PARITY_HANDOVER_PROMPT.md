# Fraktal/AB — Core 0.21 parity handover prompt

Copy the fenced text below into a coding-agent chat opened at the cloned repository
root on the AB bench workstation (the PC that reaches `192.168.100.89` and has
Studio 5000 v33 and the Flutter SDK). Written 2026-09-28.

Between 2026-09-24 and 2026-09-28 the TwinCAT binding moved from Core 0.14 to
**Core 0.21.0.0**. Fraktal/AB was not touched. This prompt brings it level for
the **read-only** claim: bind what applies, record the rest as not claimed with a
reason, and prove on the bench that the unmodified HMI still renders the press.

## State at handover

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, firmware `33.014`, serial `7036B510`, `192.168.100.89:44818` |
| Loaded build | `ContentHash 71448732E842290F` / `ConfigRevision 7423111` — [`Evidence/AB_WRITE_SURFACE_CLOSED_2026-09-23.md`](Evidence/AB_WRITE_SURFACE_CLOSED_2026-09-23.md); unchanged by [`Evidence/AB_BROWSER_COMMAND_2026-09-24.md`](Evidence/AB_BROWSER_COMMAND_2026-09-24.md) |
| AB tool suite | 695 tests, `python -m unittest discover -s FraktalCore/PLC/Allen-Bradley/tools -t FraktalCore/PLC/Allen-Bradley/tools` |
| Repo | `main` at `2db798c` or later; HMI 413 tests |
| Decisions already recorded | **Read-only** (2026-09-28, audit §9, G3 B). **Line profile not claimed** (Core §1.5, G3 C). Baseline **v33 legacy zone-and-conduit**. |

## Prerequisites

* Python 3.10+ with a venv **outside the repo** holding `pylogix==1.1.5` and
  `tools/requirements-gateway.txt`; Flutter 3.47.5 (`flutter pub get --enforce-lockfile`).
* Studio 5000 v33 on a logged-in desktop for Verify.
* Network reach to `192.168.100.89`.

---

```text
You are continuing the Fraktal/AB implementation. Objective: bring Fraktal/AB level
with Fraktal Core 0.21.0.0 for the READ-ONLY claim - bind what applies, record the rest
as not claimed with a reason, and prove on the bench that the unmodified generic HMI
still renders the AB press. Do not widen the claim.

READ FIRST, IN THIS ORDER
1. AGENTS.md §3a (the AB rules) and FraktalCore/PLC/Allen-Bradley/README.md.
2. Specification/Fraktal_AB_Part_III.md - the claim table and the "not claimed" list.
3. Specification/Reports/OBJECTIVES_AUDIT_2026-09-28.md §8, §8.1 and §9.
4. FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md §145-§151 (what changed in Core).
5. Specification/HMI_CONTRACT.md (the HMI side of the same changes).

STANDING RULES (NOT NEGOTIABLE)
* One committed declaration is the source; the L5X is output. Never hand-edit L5X or
  ladder. Regenerate, then Studio Verify 0/0 and the tool suite green.
* Read-only was decided on 2026-09-28 and is recorded. Do not add a write root,
  a writable mailbox kind, or an access-policy path. If a task seems to need one,
  stop and ask.
* Never download, change mode or keyswitch, write a tag, clear a fault, set the clock,
  or touch firmware or network configuration without CURRENT explicit authorization
  from the user in this session, and check serial 7036B510 at 192.168.100.89
  immediately before the operation. Prior authorization is historical.
* Controller reads are allowed with the serial guard every tool already applies.
* Evidence is append-only: new dated files under Specification/AllenBradley/Evidence/,
  never edits to old ones.
* Version steps follow the soft rules in Part II §2.2 by analogy: minor = a consumer
  must act, patch = additive/compatible but observable, revision = nothing observable.
  AB identifies builds by ContentHash/ConfigRevision; do not invent a second scheme -
  if AB has no version for something, say so.

WHAT CHANGED IN CORE, AND THE EXPECTED AB OUTCOME (verify each, do not assume)
* §145 line out of the Unit tree, §3.8e line data, §8.5.2 shifts -> the optional Line
  profile (Core §1.5). AB does not claim it. Confirm the projection publishes no line
  or shift leaf, and that check_consistency's AB_ABSENT records both with the reason.
* §146 principles sweep, applied to the TwinCAT press:
  - P2: Start is asked unconditionally and the release report is the only predicate.
  - P8: air loss is each cylinder's own condition and HOLDS, resuming on its own.
  - P9: the Unit base restarts attached chains on first scan, mode change and abort.
  - P6: the press OutImm carries derived facts only - no copies of child flags.
  - P4/P11: library types raise std.* keys only; project.* keys belong to the project.
  For each: is the AB press declaration equivalent? Use fraktal_ab_press_parity.py and
  read the declaration. A difference is either a declaration change (regenerate) or a
  recorded deliberate deviation with a reason.
* §148 one published diagnostic: Status.Diagnostic only; no Diagnostic member in any
  OutImm UDT and no write to one. Confirm the generated UDTs and the projection.
* §149/§151 model data for every model, and §3.8b set delete / §3.8d data classes:
  AB refuses QUERY_CONFIG/WRITE_CONFIG (no config manifest), has no recipes and no
  access enforcement. Record all as not claimed, each with its reason. The HMI must
  degrade cleanly: no configuration cards, no model picker, no error. Verify that on
  the bench (below), do not assume it.
* §150 local PINs as salted hashes: AB refuses LOGIN (access not enforced), so no
  PIN table exists on the controller. Confirm nothing on the controller or in the
  gateway retains a readable secret (the gateway/proxy credentials are the §14
  surface; check they are stored hashed as the installer intends). Record the result.
* HMI-only changes (split configuration cards, empty tabs hidden outside edit mode,
  grid container, bound icon/rotation/opacity/layer visibility, read budget, Process
  Grey default for new installs) need no AB code. They are verified through the
  gateway.

TASKS
1. Offline audit. For every item above, classify BOUND / NOT CLAIMED (reason) / GAP,
   with the file and line that proves it. Run the AB tool suite and
   `python tools/check_consistency.py --strict` from the repo root. Write the
   classification into a new evidence record,
   Specification/AllenBradley/Evidence/AB_CORE021_PARITY_<date>.md.
2. Close every GAP that the read-only claim covers, in the declaration and generator
   only, each with a test in the AB suite. Regenerate; SDK import 0/0; Studio v33
   Verify 0/0; suite green; rendition gate still proves ST/SFC/LD graph equality.
3. If the regenerated build differs from the loaded ContentHash, STOP and ask the
   user for authorization to download. Only after an explicit yes: check the serial,
   download, read the manifest back, confirm the new ContentHash/ConfigRevision.
4. Bench HMI pass, read-only: run the gateway without a write root, serve the Web HMI,
   and record screenshots or observations for: module tree, press Overview, empty tabs
   hidden (and shown in edit mode as ADMIN on the HMI side), no configuration cards,
   no model picker, a type-scoped faceplate on the press cylinders, a custom tab with
   a grid, and that every operator command is refused by the gateway before the
   controller sees it. Controller traffic in this pass is reads only.
5. Update Fraktal_AB_Part_III.md (claim table and not-claimed list, naming Core 0.21),
   FraktalCore/PLC/Allen-Bradley/README.md status, and add a closing line to the audit's
   §9 table. Keep the wording factual: what was proved, on which build, and what was
   not attempted.
6. Commit in small steps with the evidence. Do not push unless asked.

REPORT BACK
A short table: item, classification, proof (file:line or evidence section), and
whether a download was needed and authorized. List anything you could not verify and
why. Never write "not tested" into a commit or record as a caveat for work that could
have been run; if a gate could not run, say exactly why.
```
