# Final TC3 handover acceptance â€” 2026-10-05

The final native aggregate passes **215/215 tests in 45 suites**. Separate
PressTests passes **9/9 in two suites for each of ST, SFC and LD** on the
user-authorized isolated `192.168.1.6.1.1:851` / UmRT_Default. Results were read
independently over ADS and validated for exact runner, totals and suites.
All six XAE 3.1.4026.24 object checks pass with installed Core 0.23.0.0 and
Modules 0.11.0.0. The final source selects Ladder; temporary selectors and
XAE-generated test wrappers were restored before committing.

## What the native runs establish

- The eighteen added handover tests pass: bounded inactive model creation,
  permissions and refusal, immutable current exports and interruption/no replay,
  weekly V1/V2 migration, five-row calendar/target transactions, boundaries,
  unscheduled counts, history and manual OEE reset. See the initial dated report
  for the explicit root-model-region ownership and storage bounds.
- Press acceptance checks two complete AUTO cycles with fresh per-cylinder
  completed-stroke counts and end positions, plus the five hold/fault/recovery
  cases. Changeover alone no longer requires air at Start; AUTO/HOME and motion
  pressure permits retain their guards. All HAL channels here are simulated.
- SFC's parallel ram cursor required a branch-aware fixture. That exposed the
  native graph restart defect: resetting shared `_step` alone left the graph
  latched after a fault. The sequence base now owns the inherited Reset pulse,
  consumed through mandatory `M_Step`; chart metadata enables the inherited flag.
  The serialized graph is unchanged and its read-back accompanies this report.
- Disabling only SFC Reset/Use returns **5/9**, with four recovery failures.
  Restoration returns **9/9**. Earlier failed attempts are retained separately;
  an earlier mutation against an already-failing fixture is not a claimed kill.
  The pending-logout race and its native failed/corrected results are recorded in
  `2026-10-05_TC3_Handover_AggregateCorrected.md`. Earlier HMI export mutants kill
  omitted document tokens and missing continuation lines.

## Other checks and measurement scope

Modern and 4024 lint, tool discovery, strict root consistency and its tests are
recorded alongside the final commit. Earlier shared-HMI validation remains valid:
Flutter 3.47.5 / Dart 3.13.4, 533 tests pass with seven skips, analyzer clean,
release web build successful. No HMI changes followed those checks. The generated
asset hash is in `2026-10-05_TC3_Handover.md`; no served-browser claim is made.

One hundred post-suite Press task point samples reported maximum execution
158 Ã— 100 ns, with
0 sampled CycleTimeExceeded and
0 sampled RTViolation flags. The authored task period
is 10 ms. These are idle scans after completion, not the peak test-execution or
production scan cost; point samples cannot establish a zero-overlap count.
Compiled peak task stack remains unmeasured. Native aggregate memory areas were
recorded at their exact artifact in the earlier aggregate report; no production
station fit is inferred from this deliberately large regression application.

## Remaining boundaries and restoration

This handover establishes the compiled implementation and isolated native
regression scope above. Browser/TF6100/gateway commissioning, physical I/O/safety,
mirror/shared-root transport and power/restart/download retention remain separate
acceptance. Model creation refuses composite multi-record recipe banks; it does
not advertise unsupported atomic cloning. The existing hidden-credential
persistence defect remains documented in IMPLEMENTATION_NOTES Â§154; symbol
exclusion was kept and no credential-retention success is claimed.

The final isolated test PLC was verified **STOP**, with boot Autostart **off**;
the handover solution was logged off and closed. The pre-test Boot directory
remains backed up in the original checkout's
`artifacts/tc3-target-before-tests-2026-10-05/Boot`. Its original configuration
was itself an isolated library wrapper with no physical I/O. No machine program
was replaced, test autostart was never enabled, and original local edits were
kept outside the validated snapshot. The requested fresh public AGPL repository
is prepared from this canonical snapshot after these gates, with one root commit
and preserved legacy/third-party notices; historical evidence is append-only.
