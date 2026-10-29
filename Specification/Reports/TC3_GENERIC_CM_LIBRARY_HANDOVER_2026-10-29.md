# Handover prompt — generic control-module library, remaining work (TC3)

Paste everything below the line into a fresh session started in `C:\Projects\Fraktal`.

---

You are continuing the **generic control-module library** work in the Fraktal repository
(`C:\Projects\Fraktal`, branch `feature/generic-cm-phase0`, pushed to `origin`). Phase 0
(digital-input debounce, analog channel unit codes), Phase 1 (cylinder valve timing) and the
Unit's NOK-part limit are implemented, gated on the real runtime and committed. Your job is the
remaining **library-only** packages, one at a time, each fully gated before you commit it.

## Read first, in this order
1. `AGENTS.md` — repository rules. They override defaults.
2. `Specification/Reports/TC3_GENERIC_CM_LIBRARY_PLAN_2026-10-29.md` — **the plan**: scope
   decisions, the rules for every package (§1), the order and version steps (§2), and the
   file-level design of each package (§3–§10). It is authoritative for scope and design; if the
   code proves a design wrong, stop and say so rather than improvising.
3. `FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md` §164–§167 — what was just built and why.
4. `Specification/Guides/TWINCAT_XAE_WORKFLOW.md` — before any XAE or runtime work.

## Standing owner decisions
- **Library only.** Develop `Fraktal_Core`, `Fraktal_Modules` and the generic HMI. Do not implement
  anything in `FraktalCore/PLC/TwinCAT/Examples/` (the Press bench has no analog I/O and is not a
  consumer); only the version pins listed in plan §1.5 change there.
- The "first consuming station" rule is **waived**: each commit says *"no station consumer (owner
  waiver 2026-10-29); consumers: TcUnit suite, generic HMI"*.
- Out of scope: native TCP channel, EL6001, PartFeed NC, RFID/MES/historian adapters.
- TIA's candidate ABI is frozen (V2 is current). Never change a frozen Core record or `E_Reason`
  without asking — that would need an owner-reviewed V3.
- The local usermode runtime **UmRT_Default 192.168.1.6.1.1:851** is designated for TcUnit gates
  and may be left on the test configuration. No other controller may be touched.

## Do this first
1. `git status` and `git log --oneline -6` — expect head `289630901` (NOK limit) on
   `feature/generic-cm-phase0` and only `.vscode/settings.json` locally modified (not yours; never
   commit it).
2. Ask the owner **Q1** (plan §0): keep or remove the NOK-policy wiring that commit `289630901`
   added to the Press `MAIN`. Act on the answer as plan §0 describes.
3. Read `<ExpireTime>` in
   `C:\ProgramData\Beckhoff\TwinCAT\3.1\Runtimes\UmRT_Default\3.1\Target\License\TrialLicense.tclrs`.
   The trial runs to **2026-11-04T00:00**. If it has expired, ask the owner to renew it (an
   interactive captcha — never automate it) before any runtime gate.
4. Start **L1** (`FB_AnalogInputCM`, plan §3). Then L2, L3, L4, L5, L6 in order. **L7** waits for
   the owner's answer to **Q2** (plan §9); **L8** is paper only.

## For every package
- Implement exactly the plan's files, members, defaults, method signatures, reasons and texts.
- Run the gates of plan §1.3 and §1.4 in order: lint (both profiles), tool tests, strict
  consistency, the repository gate tests, **every AB/TIA check and replay**, the Siemens tool tests,
  the reason-catalog generator `--check`, HMI analyze/test; then the library install, the six
  `CheckAllObjects`, and both TcUnit runtime gates from an isolated worktree.
- Write the IMPLEMENTATION_NOTES section, the evidence record with its SHA-256 receipt, the
  version lines, the AB/TIA census rows; commit one package per commit, then push.

## Traps that have already cost time here
- **Bytes, not text.** `* -text` is pinned and files mix CRLF/LF inside one file. Measure endings in
  Python, give inserted lines the anchor line's terminator, assert one match, check `git diff --stat`.
  Never `sed -i`. Write edit scripts to files; heredocs mangle backslashes.
- **The TIA generator hashes TC3 Core DUTs, `E_Reason`, `PL_Fraktal` and `PL_ModuleReasons` —
  even a comment.** After touching any, regenerate both TIA packages (plan §1.3) or TIA CI breaks.
  Pinned counts move with it: `test_s12_type_map.py` (struct fields), `reason_catalog_test.dart`
  (generated reasons), and the CI/workflow test inventory.
- **No NC licence** on this host: axis rows test only what happens before an `MC_*` call. Say so.
- **TcUnit runs a suite's rows side by side**: one instance per multi-scan row, a done flag per row,
  timing asserted with elapsed `TIME()`. A probe Unit is ~350 KB — share one across single-scan rows
  only when each row starts from a clean slate.
- `_M_State` is called unconditionally every scan; a CASE always has an `ELSE`; the 4024 profile has
  no defaulted method inputs, so every caller passes every input.
- **Flutter:** only 3.44.6 exists here. Never run a plain `flutter pub get`; confirm
  `FraktalCore/HMI/pubspec.lock` is unchanged and record the SDK actually used.
- **Hidden XAE hang during a runtime gate** = a visible modal. Find it with `EnumWindows`, close it
  with `PostMessage(dlg, WM_COMMAND, <button control id>, <button hwnd>)`; the gate then cleans up.
- The AB tool suite has 8 native-connection errors that predate this work and are not a CI gate.
- Tracked files stay vendor-neutral; the reference-material folder listed in `.gitignore` is
  ignored working material and is never committed or quoted.

## Stop and ask the owner when
- a plan design does not fit the code as it is;
- a frozen TIA record or `E_Reason` would change, or a new CM reason block is needed (all CM
  blocks are allocated once L1/L2/L5 reserve 10700/10800/10900);
- a published or persistent member would be renamed or removed (a consumer would have to act);
- a gate cannot run (say exactly why — never commit ST behind a "not compiled" disclaimer);
- anything would touch a controller other than the designated UmRT, or download/activate on it
  outside the TcUnit gate script.

## Report at the end of each package
What was built (one paragraph), any departure from the plan and its reason, the gate results with
numbers (tests/suites, solutions, HMI counts), what was not run and why, the commit hash, and the
next open question.
