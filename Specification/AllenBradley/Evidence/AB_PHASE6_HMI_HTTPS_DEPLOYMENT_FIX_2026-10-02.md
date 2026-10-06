# Phase 6: deploy the corrected login client to the HTTPS HMI

Recorded 2026-10-02 in America/Bogota (observations 2026-10-03 UTC).
Source parent: `7e51d4c`; HMI logic: `81cb32b`.
This is a static Web HMI deployment correction. No source code or PLC artifact
changed, and no controller write or gateway restart was performed.

## Finding

The owner again reported a login-failure dialog over a successfully logged-in
application, then identified the actual Chrome URL as `https://press.localhost/`.
The earlier [development-server correction](AB_PHASE6_HMI_STALE_CLIENT_FIX_2026-10-02.md)
updated Flutter on port 5555. It did not update the owner's HTTPS release.

The HTTPS site's public serving directive points to
`C:\Users\Rockwell Automation\repos\Fraktal\FraktalCore\HMI\build\web`.
That directory still held the September 29 release. Its `main.dart.js` contained
none of `LoginBusy`, `LoginTimeoutMs` or `LoginResultSequence`. The tested final
release in `C:\work\press62_hmi_web_final` contains all three checks and waits
for the current login result before reporting credential failure.

A serial-guarded read-only observation of `192.168.100.89`, serial `7036B510`,
found the press62 public contract (`10AEDC3FFD6B5DC1`, revision `1093340`),
authenticated admin level 4, no pending login and no login failure. Completed
result sequence 131 matches the accepted LOGIN audit and mailbox acknowledgement.
Maximum task scan is 5,218 microseconds against the 10,000-microsecond period;
overlaps and major/minor fault bits are zero. These reads diagnose the existing
session; they do not measure another login or prove the browser dialog.

## Deployment and verification

All 42 resources were copied from the tested final artifact into a staging
directory and compared by SHA-256. The old served directory was retained at
`C:\work\phase6_hmi_https_backup_20261003_024143`, and the stage was moved into
the original static root. A second complete comparison of the deployed files
passes. Caddy configuration and gateway processes were unchanged.

| Main application | Bytes | SHA-256 |
|---|---:|---|
| Previous HTTPS release | 4,464,691 | `2259762a3d50cea5436a9eb5e932662c474b8255e212643a6db790c086b53b5f` |
| Deployed corrected release | 4,468,492 | `5ec6112ad0e7b6bf490d2e46149724607837df0c74b1c0dbf6d9d07c689e415f` |

Unauthenticated HTTPS requests to `/`, `/main.dart.js` and `/version.json`
return 401 using the correct `press.localhost` TLS server name. This confirms
the site continues to require authentication; it does not validate PKI or
authenticated content delivery. No credentials or upstream token were printed
and authentication was not bypassed.

The reused release passed 439 HMI tests with six skipped, clean Flutter analysis,
and the release Web build. HMI source has not changed since that artifact's
validation. Fresh mandatory gates pass: 1,422 AB tool tests, 33 root tool tests,
and consistency with zero errors and zero warnings. No new compile or controller
download is needed for this static deployment.

The owner must hard-refresh the HTTPS tab with `Ctrl+Shift+R` and confirm that
a successful login closes the dialog. No browser surface is accessible to the
agent, so that visible behavior remains unverified. No login attempt, policy or
plant write, fault/counter clear, mode change or gateway launch was made during
this correction. S9 and physical retention remain owed; this deployment does
not advance the write-enabled claim.

Machine-readable deployment, complete file hashes, read-only controller
observation and gate results:
[JSON](AB_PHASE6_HMI_HTTPS_DEPLOYMENT_FIX_2026-10-02.json).
