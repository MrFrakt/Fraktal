# S11 — SCL startup and local errors on the physical 1214C

Disposable test extension to S2. Sources are ASCII, LF. `build_1214c.plan` keeps
the existing `FrkSpikeS2` station project/certificates, imports S2 plus this
extension, compiles software and hardware separately and exports for inspection.
Use S2's download plan after `s7_probe.py ident`; its exact-target guard remains.

`OB100` observes startup requests and HAL coils **before** cyclic code, rather
than clearing them for the test. OB124 records `Initial_Call`, waits for S2's
17 rows, then adds cases 29 (safe startup) and 30 (local invalid-index error).
`GET_ERR_ID` is deliberately in the offending FC: it activates local handling
and returns 16#2522 while the CPU continues. This is detection evidence; the
runtime library must still fault and withdraw outputs on an unexpected error.

Physical 1214C V4.7.3: **19/19** after download/start and direct native web
STOP→RUN, and after two code-only downloads in RUN. Records:
[`semantics`](../../../../../Specification/Siemens/Evidence/TIA_S11_SEMANTICS_2026-10-09.md)
and [`native restart/download`](../../../../../Specification/Siemens/Evidence/TIA_S11_NATIVE_2026-10-09.md).
The latter preserves DB data, the OB100 timestamp and mailbox sequence/ack
across marker 1101→1102. Only the cycle OB was loaded; no type/layout changed.
This is an idle fixture result, not an active-command or GRAPH update test.

`build_code_change.plan` imports only `20_` sources, compiles and exports;
`download_changes_1214c.plan` selects `--changes-only`. The completed-state
branch in OB124 sets the code marker and increments existing `Samples[1]`,
with a persistent sentinel in existing `Samples[0]`; it adds no DB members.
`check_native.py` checks archived snapshots, DB interfaces and exact JUnit IDs.

`web_mode.py` reads the authenticated native mode form, identifies/confirms
the fixed bench immediately before its single POST, then verifies mode via
SZL. It checks the existing TLS pin on every connection and logs out. Secrets
come from `FRAKTAL_TIA_DIAG_PASSWORD` / `FRAKTAL_TIA_WEB_PASSWORD` only.
SZL states observed here: 3 STOP, 6 startup, 8 RUN; state 4 is also STOP.

`mode_right_1214c.plan` with `mode_right=,WebChangeOperatingMode` temporarily
grants diagnostics-mode control; `mode_right=` restores diagnostics-only.
Both use `--user-management update` and `--keep-password`, preserving existing
passwords and gateway rights. **Cleanup PASS:** the owner-whitelisted
`bin/candidate_s11_enumeration` driver enumerates assigned identifiers directly,
verifies the requested set and restores diagnostics-only. Hardware compile and
UMAC download 0/0; authenticated mode forms absent; gateway reads and 19/19 pass.
The V20 SDK IList enumerated two valid objects but `.ToList()` produced one
null entry. See [record](../../../../../Specification/Siemens/Evidence/TIA_S11_ENUMERATION_2026-10-09.md).
`web_mode.py inspect --diagnostics-only` checks the authenticated native page
without issuing a mode command. Preserve every previously approved binary.
