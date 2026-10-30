# S4b V6.10 Capacity precheck refusal — 2026-10-29

The first prepared session stopped before the download-attempt marker, project
open, Program mode or download. The SDK correctly refused its Capacity gate:
the authorization template retained the prior image's 2,066,212 used /
1,079,516 available / 3,145,728 Blocks, while this image's measured result is
2,077,924 / 1,067,804 / 3,145,728 (66%). The preparation failed to derive that
confirmation field from the new Capacity capture. The guard is unchanged.

Target, service/listener and idle/logout guards pass; MANUAL normalization
performs zero writes. Fresh backup upload, Save As audit and access audit pass.
Read-only TASK/CPU monitors stop cleanly, no dumps. `deploy_attempt.json` and
the pre-Run marker do not exist. The runner reports failure and consumes the
authorization; `genealogyRestored: false` means its rollback branch never ran,
because no deployment began. It does not mean the baseline was displaced.

Post-refusal identity/mode/fault checks and exact preflight verification pass:
Echo remains genealogy `6DEC4C1DC2F7F78A`, Run, not faulted, MANUAL/idle/logout,
with all five original host documents unchanged. Controller writes, mode
changes, downloads, fault/TASK clears, clock/power/vendor-state operations and
Echo hard kills are zero.

Workspace `C:/work/fraktal-ab-s4b-owner-20261029/session_01` and its failed logs
are retained. Credentials, binaries and ACD/BAK are excluded from the payload;
the private backup is preserved with its hash. No native ABI or S4b acceptance
is claimed. Next: derive confirmation values from the same pinned Capacity
result, test that equality before sealing, create a fresh session namespace,
and retry under standing O3. No PLC/HMI product source or image changes.
