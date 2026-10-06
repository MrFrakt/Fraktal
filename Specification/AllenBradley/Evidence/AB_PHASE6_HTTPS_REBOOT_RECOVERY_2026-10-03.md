# Fraktal/AB HTTPS HMI recovery after Windows reboot

**Date:** 2026-10-03, America/Bogota. **Parent:** `4ce985d`.
**Scope:** restore the existing local HTTPS proxy and its Windows sign-in
startup. No PLC read/write, download, fixture, gateway restart, credential
change, certificate installation or Web release deployment was performed.
The companion [JSON](AB_PHASE6_HTTPS_REBOOT_RECOVERY_2026-10-03.json) binds
configuration/binary/launcher hashes, Web resources and endpoint checks.

## Finding and recovery

The owner reported `https://press.localhost/` unavailable after reboot and
showed the AB gateway listening on `ws://127.0.0.1:8099/fraktal`. The observed
gateway PID was 19324, listening on loopback port 8099. Caddy had no process,
no port 443 listener, no service/task and no Startup shortcut. An HTTPS
connection to the loopback address was refused. The existing release files
were present.

`C:\work\caddy\Caddyfile` validates with the existing Caddy v2.11.4. Its public
routes serve `FraktalCore/HMI/build/web` and proxy the gateway to 127.0.0.1:8099.
Authentication, upstream bearer and internal TLS configuration were preserved;
neither configuration nor credential values were printed. Configuration SHA-256
before and after is `D96E4D0DC4A64AF3C30080B9D669462CAC81B005808D227E1957282DFBCD5BE7`.

The local deployment launcher `C:\work\caddy\Start-WebProxy.ps1` starts Caddy
with the existing Caddyfile under the current Windows account, preserving its
certificate storage. It checks for an existing process with the same executable
and config path, hides the child window and writes stdout/stderr to uniquely
named files under `C:\work\caddy\logs`. Caddy started as PID 14944 and listens
on 443. No service account or global execution-policy setting changed.

The current user's Startup folder now contains `Fraktal Press HTTPS.lnk`,
targeting Windows PowerShell with `-NoProfile -ExecutionPolicy Bypass
-WindowStyle Hidden -File "C:\work\caddy\Start-WebProxy.ps1"`. Its working
directory is `C:\work\caddy`. This starts Caddy at **Windows sign-in**, not
before a user signs in. The AB gateway remains owner-started separately.

## Verification and limits

- The saved shortcut's exact action was invoked hidden and exited zero.
  Both that action and a direct second launcher invocation reported the same
  existing PID 14944; there is exactly one Caddy process. An actual new
  Windows sign-in/reboot was not performed.
- `/`, `/main.dart.js` and `/version.json` each return **HTTP 401 Unauthorized**
  over TLS 1.3 with hostname and certificate trust verified. These requests
  contain no credentials; 401 confirms that the restored site retains its
  authentication gate, not that an authenticated browser rendered the HMI.
- Windows curl's initial certificate check could not obtain revocation
  information for the internal certificate. A curl probe with only revocation
  checking disabled returned 401. Independent Python SSL probes using the
  default trust store, `CERT_REQUIRED` and hostname verification also returned
  401. No trust bypass or certificate-store change was made.
- All **42** deployed Web resources match `C:\work\press64_hmi_web` by SHA-256.
  `main.dart.js` remains
  `6CD7739CA101CE1054244FB26FFABA57ABBE39374D296315AF773F06A4DD2D7F`.
  Gateway PID 19324 remains the port-8099 listener.
- Only deployment documentation/evidence is changed in the repository. No PLC,
  HMI or gateway production source changed, so their already-tested builds are
  reused. Repository consistency passes with zero errors and warnings.

The owner can reload the HTTPS tab and use the existing proxy credentials if
prompted. The gateway's plaintext warning describes the loopback upstream;
browser traffic uses Caddy's HTTPS endpoint. The press67 controller deployment
and subsequent Phase 6 hardware gate remain unconfirmed by this recovery.
