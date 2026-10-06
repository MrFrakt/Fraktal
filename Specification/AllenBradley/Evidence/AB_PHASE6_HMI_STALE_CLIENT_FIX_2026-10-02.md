# Phase 6: stale served HMI login correction

Recorded 2026-10-02 in America/Bogota (observations 2026-10-03 UTC).
Logic source: `81cb32b`. Target: `192.168.100.89`, serial `7036B510`.
This is a deployment correction of the development HMI, with no source change
to the login implementation and no controller writes.

## Finding

The owner reports acceptable login time but a failure message before the
successful session appears. Serial-guarded, read-only observations found
the press62 public contract: hash `10AEDC3FFD6B5DC1`, revision `1093340`,
Access State schema 3 and the declared 256-hash gateway prefix. The PLC reports
`phase6_admin`, level 4, no pending login and no login failure. Result sequence
3 matches the accepted LOGIN audit entry and mailbox acknowledgement.
The task maximum is 5,013 microseconds against its 10,000-microsecond period;
overlaps, major fault bits and minor fault bits are all zero. The gateway's
snapshot and targeted read both expose the same successful session and sequence.
These observations do not measure a new login or prove the full access matrix.

The public Flutter application module served at `http://127.0.0.1:5555`
was the old implementation. Its `login` body awaits mailbox consumption,
delays, refreshes once and returns the then-current session comparison.
It has no `LoginBusy`, `LoginTimeoutMs` or `LoginResultSequence` handling.
It can therefore return false while the PLC is still authenticating; subsequent
background snapshots show the successful session while the dialog retains the
failure message. The committed source already contains the necessary waiting
and result correlation.

The inspected file is `packages/fraktal_hmi/data/opcua_repository.dart.lib.js`,
the application module. `main.dart.js` is only a debug loader and cannot establish
which login implementation is served. Port 9100 serves Flutter DevTools.

## Action and verification

The existing Flutter runner and listener on port 5555 were checked by process
identity, arguments and listener ownership. Only that HMI runner was stopped.
Flutter was restarted hidden from this repository's HMI directory, preserving
debug mode, `web-server`, host `127.0.0.1`, port `5555` and using `--no-pub`.
The gateway was not restarted and its configuration was not read or changed.

Before: 257,651 bytes, SHA-256
`91a10efc8de43a67b28c80b8a57b864bcb797f49b52655326379c3373c2d97e3`.
After: 326,035 bytes, SHA-256
`00728fa017943f126ba107d5ab0ad1c9de96f0224c375c13804f6c06926597ea`.
The newly served module includes pending-login, provider-budget and matching
result-sequence checks. Its listener is healthy on the same address and port.

Eight targeted HMI login regressions pass, including delayed authentication,
an older failure followed by the current success, wrong credentials and timeout
classification. The AB tool suite passes 1,417 tests; root consistency reports
zero errors and zero warnings; the root tool suite passes 33 tests.

Chrome must load the newly served code with a hard refresh (`Ctrl+Shift+R`).
No browser surface is available to this agent, so the owner must confirm the
dialog's behavior after that refresh. No new PIN attempt, policy/plant write,
counter or fault clear, download, mode change or gateway launch was performed.
The full access fixture, measured request timing and S9 remain owed. This record
does not advance the write-enabled security claim.

Machine-readable observations and gate results:
[JSON](AB_PHASE6_HMI_STALE_CLIENT_FIX_2026-10-02.json).
