# Corrected TC3 aggregate runtime — 2026-10-05

**215 tests / 45 suites, 215 successful, zero failures**, read independently from
TcUnit over ADS at the user-named isolated `192.168.1.6.1.1:851` (UmRT_Default).
This is aggregate acceptance only; separate Press rendition results follow.
It does not establish physical retention, browser/TF6100 commissioning or safety.

The first executed run returned 213/215. Its raw log and failing JUnit remain
in `2026-10-05_TC3_Handover_FirstAggregateFail.*`. Native reads identified:

- Pending `Access.ReqLogout` was consumed after the HMI request. Export therefore
  saw the old session generation and disclosed its continuation in the same scan.
  Header and continuation now refuse while logout is pending; normal operator
  activity/idle-timer ordering stays unchanged. The test also requires empty output.
- The OEE fixture called `CountNok(E_Reason.NONE)`, legitimately faulting the Unit
  with RESULT_RECORD_REJECTED / `std.error.nokReasonRequired`. The following BUSY
  creation test then could not Start. The fixture supplies the defined TEST_FAULT
  reason. Production's reason-required guard is unchanged.

All six XAE 3.1.4026.24 object checks pass after Core/Modules installation.
The corrected aggregate proves both fixes and the existing eighteen portable
handover tests, including actual BUSY creation, full capacity refusal, permissions,
immutable/no-replay exports, weekly migration/transactions/boundaries and history.
The earlier missing-logout-guard implementation is rejected by the native test;
the HMI tests separately kill omitted-token and missing-document-line mutants.

Once the user manually selected the aggregate project, its active DTE could stop,
log off, reopen and download the same project. `IsLoggedIn=True` was verified.
XAE's void Start call left the PLC stopped; the official ADS WriteControl(Run)
then started the verified test application. Actual ADS Run and complete TcUnit
results, rather than the void call's return, establish this pass.

Native download diagnostics report data area 347,674,272 bytes, highest used
289,728,560 and largest gap 57,945,712; code area 1,637,856 bytes, highest used
1,259,880 and gap 377,976. These are this aggregate's generated memory areas,
not production fit, licensing consumption or measured task stack/scan cost.
The two existing hidden-credential persistence warnings remain a separate defect.
