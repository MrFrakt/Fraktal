# Fraktal OPC UA WebSocket gateway

This headless Windows/Linux service owns one native PLC session and exposes
the versioned `fraktal.opcua.gateway.v1` protocol on loopback at `/fraktal`.
With `--web-root`, the same listener also serves the compiled Flutter Web HMI;
the page and WebSocket therefore share one origin and do not need a separate
static server. Flutter Web, Windows, Linux, and Android clients can use the same
`ws://` or `wss://` endpoint. The gateway does not replace functional safety:
HMI and standard-PLC requests remain untrusted; only TwinSAFE/certified safety
logic may grant safe motion, reset, unlock, muting, bridging, or safe outputs.

**PLC transport.** `--plc-endpoint` selects one of two transports (both emit the
same gateway protocol to browsers, so the Web HMI is identical either way):

- `opc.tcp://<host>:4840` — TF6100 / multi-brand OPC UA, governed by the security
  profile below (certificates, trust, credentials).
- `ads://<AmsNetId>:851` — native TwinCAT ADS (Windows only), the same fast path
  the desktop HMI uses. Requires `fraktal_ads.dll` beside the gateway exe (bundled
  by the installer when built with the TwinCAT ADS SDK) and an AMS route to the
  target. The **AMS route is the trust boundary**, so the OPC UA security profile,
  certificates, and `FRAKTAL_OPCUA_USERNAME`/`PASSWORD` **do not apply** to ADS.

For the complete Windows installer and Linux systemd walkthrough, acceptance
evidence, upgrades, and remote-browser topology, see
`../../../Specification/WEB_HMI_GATEWAY_DEPLOYMENT.md`. The same walkthrough is
copied beside the binaries in every platform package.

## Security profiles

The selected profile is printed at startup and reused unchanged after every OPC
UA reconnect. A failed secure connection never falls back to Anonymous or
`SecurityPolicy=None`.

| Profile | OPC UA channel | User token | Intended use |
|---|---|---|---|
| `production` (default) | trusted certificate, `SignAndEncrypt` | dedicated TF6100 user | Every network-connected production deployment |
| `secure-anonymous` | trusted certificate, `SignAndEncrypt` | Anonymous | Short commissioning where encryption and application trust are ready but the user mapping is not |
| `commissioning-anonymous` | `SecurityPolicy=None` | Anonymous | Troubleshooting/initial commissioning; conspicuous warning and automatic stop after 120 minutes by default |
| `isolated-anonymous` | `SecurityPolicy=None` | Anonymous | Explicit permanent exception for one physically isolated, unrouted PLC/HMI cell |

`commissioning-anonymous` accepts `--commissioning-ttl-minutes 1..1440`.
`isolated-anonymous` has no timer, so its required controls are physical: no
route to a plant/office/public network, restricted switch/ports, local service
access, and a documented exception owner. Neither profile may carry a password.

## Build

Build on the target operating system; this is not a cross-compiler.

```text
cd FraktalCore/HMI
flutter pub get
cd gateway
dart pub get
dart run tool/build_gateway.dart --clean
```

The command first runs `flutter build web --release --no-pub` and copies that
exact output into the platform package. Output is written to
`FraktalCore/HMI/build/gateway/windows-x64` or `linux-x64`. Windows contains
`fraktal_gateway.exe`, `fraktal_gateway_tray.exe`, `fraktal_opcua.dll`, and
`web/`; Linux contains `fraktal_gateway`, `libfraktal_opcua.so`, and `web/`.

The Windows build also creates
`build/gateway/installer/FraktalSetup.exe`. It is a per-user, self-extracting
installer (built with IExpress + a PowerShell WinForms wizard) that installs
either or both components:

- **Fraktal HMI** — the native desktop app, which connects **ADS-direct** to the
  PLC on a TwinCAT host. Installed to `%LOCALAPPDATA%\Programs\Fraktal HMI` with
  a Start Menu shortcut (no autorun — it is an on-demand GUI).
- **Fraktal Gateway + Web HMI** — the browser-access path over OPC UA. Installed
  to `%LOCALAPPDATA%\Programs\Fraktal Gateway`; the tray starts immediately and a
  Startup shortcut starts it at future sign-ins.

The wizard requires at least one component and asks for a per-component PLC
endpoint: the HMI's `ads://<AmsNetId>:<port>` (default
`ads://127.0.0.1.1.1:851`) and the gateway's `opc.tcp://<host>:<port>` (default
`opc.tcp://127.0.0.1:4840`). The two components are independent — the HMI does
not talk to the gateway. On first install the HMI endpoint is seeded into
`%APPDATA%\Fraktal\HMI\connection.json` (the app still runs its own
language/unit wizard on first launch, with the endpoint pre-filled) and the
gateway endpoint is written as `--plc-endpoint` in
`%LOCALAPPDATA%\Fraktal\Gateway\gateway.args`. Existing configuration, PKI
files, logs, and the HMI connection settings are preserved across upgrades and
uninstall. A silent path exists for Group-Policy/AppLocker hosts:

```cmd
install_fraktal.cmd -Components HMI,Gateway -HmiEndpoint ads://192.168.1.6.1.1:851 -GatewayEndpoint opc.tcp://192.168.1.6:4840
```

The installer is intentionally unsigned in a developer build; sign it with the
organization's Authenticode certificate before production distribution.

Windows needs Visual Studio C++ Build Tools and CMake. Linux needs a C/C++
toolchain, CMake, and the Dart SDK. Pinned open62541 and Mbed TLS sources are
built locally; the gateway does not require the Flutter engine.

## Production provisioning

Provision each gateway as its own OPC UA application:

1. Issue a unique client certificate and private key. Its application URI must
   be stable and must exactly equal `--application-uri`.
2. Put the TF6100 server certificate or its issuing CA in the gateway trust-list
   file/directory. Add CRLs with `--revocation-list` when the plant PKI uses
   revocation. Do not enable automatic trust in production.
3. Trust the gateway client certificate in TF6100.
4. Create a dedicated TF6100 data-access user. Grant namespace Browse,
   ReadAttribute, and ReadValue; grant Write only to the assigned root Unit
   `HmiRequest` subtree. Do not use the Configurator administrator account.
5. Enable a matching TF6100 `SignAndEncrypt` endpoint. The gateway defaults to
   `Basic256Sha256`; another supported policy can be passed explicitly.
6. Protect the private key and credentials with the service account's OS ACLs.
   Never put the password on the command line or in HMI settings.

Windows defaults to this security-material layout:

```text
%ProgramData%\Fraktal\Gateway\pki\own\certs\fraktal-gateway.der
%ProgramData%\Fraktal\Gateway\pki\own\private\fraktal-gateway.pem
%ProgramData%\Fraktal\Gateway\pki\trusted\certs\
```

Set credentials in the dedicated process account, then run from the package
directory. The certificate URI must match the wrapper's default
`urn:fraktal:gateway:<COMPUTERNAME>` or be supplied explicitly.

```powershell
$env:FRAKTAL_OPCUA_USERNAME = 'fraktal_gateway'
$env:FRAKTAL_OPCUA_PASSWORD = '<from protected deployment secret>'
# Optional for an encrypted PEM key:
$env:FRAKTAL_OPCUA_PRIVATE_KEY_PASSWORD = '<from protected deployment secret>'
.\run_gateway.ps1 `
  -SecurityProfile production `
  -PlcEndpoint opc.tcp://plc-cell-01:4840 `
  -ApplicationUri urn:fraktal:gateway:cell-01 `
  -WriteRoot PLC1/MAIN/PneumaticPress
```

For Linux, install the supplied systemd unit and environment example as
described below. Production is also the raw executable's default, so missing
certificate paths, trust material, username, or password stop startup.

## Anonymous exception workflows

Secure Anonymous still requires the application certificate, private key,
server trust list, matching `SignAndEncrypt` endpoint, and an enabled TF6100
Anonymous token:

```powershell
.\run_gateway.ps1 -SecurityProfile secure-anonymous `
  -PlcEndpoint opc.tcp://plc-cell-01:4840 `
  -ApplicationUri urn:fraktal:gateway:cell-01 `
  -WriteRoot PLC1/MAIN/PneumaticPress
```

For local commissioning/troubleshooting, explicitly select the expiring
insecure profile:

```powershell
.\run_gateway.ps1 -SecurityProfile commissioning-anonymous `
  -CommissioningTtlMinutes 120 `
  -WriteRoot PLC1/MAIN/PneumaticPress
```

```sh
./run_gateway.sh --security-profile commissioning-anonymous \
  --commissioning-ttl-minutes 120 \
  --plc-endpoint opc.tcp://127.0.0.1:4840 \
  --write-root PLC1/MAIN/PneumaticPress
```

Use `isolated-anonymous` only after recording and verifying the physical-isolation
exception:

```powershell
.\run_gateway.ps1 -SecurityProfile isolated-anonymous `
  -WriteRoot PLC1/MAIN/PneumaticPress
```

All insecure profiles emit `stage=security-warning`. Remove temporary Anonymous
namespace/write rights after commissioning if the PLC is network-connected.

## HMI endpoint and write scope

With the packaged Web root, the local page is `http://127.0.0.1:8080/` and the
gateway endpoint is `ws://127.0.0.1:8080/fraktal`. A release Web HMI derives
that endpoint from its page origin automatically; Chrome debug uses the
explicit loopback endpoint. Health endpoints are:

- `/livez`: process liveness, for restart supervision;
- `/readyz`: HTTP 200 when the most recently observed OPC UA operation worked,
  or 503 when PLC access is degraded;
- `/healthz`: backward-compatible JSON status.

Local `http://localhost:*` and
`http://127.0.0.1:*` browser origins are accepted automatically. A native HMI
may also use this endpoint; it no longer needs a direct raw OPC UA session.

Gateway writes are limited to published `HmiRequest` fields and are read-only
until at least one root is assigned:

```text
--write-root PLC1/MAIN/PneumaticPress
```

Repeat the option for a multi-root HMI. `--allow-all-root-mailboxes` is an
explicit commissioning override, not a production scope. The PLC still applies
its access and release checks.

## Remote HMI and WSS

The gateway intentionally cannot bind to a LAN interface. Put an authenticated
TLS reverse proxy on the same host. Proxy ordinary HTTPS requests to
`http://127.0.0.1:8080` and the external `wss://hmi.example.com/fraktal` route
to `ws://127.0.0.1:8080/fraktal`. The proxy must:

- authenticate every WebSocket upgrade;
- terminate TLS with a certificate trusted by each HMI device;
- preserve WebSocket upgrade headers and the `Origin` header;
- apply connection/rate limits and audit access;
- expose the static HMI and `/fraktal`; expose a health endpoint only when an
  authenticated monitoring policy requires it;
- leave WebSocket control frames intact and use an idle timeout comfortably
  above the gateway's 2 s heartbeat interval.

Add the exact Web origin, for example `--allow-origin
https://hmi.example.com`. Origin checking is a second browser boundary, not
authentication. Native Windows/Linux/Android HMI clients validate WSS through
the platform trust store and can present an mTLS client identity provisioned by
the device manager:

```text
FRAKTAL_WSS_CLIENT_CERTIFICATE=/protected/device/client-chain.pem
FRAKTAL_WSS_CLIENT_PRIVATE_KEY=/protected/device/client-key.pem
FRAKTAL_WSS_CLIENT_KEY_PASSWORD=<optional protected secret>
FRAKTAL_WSS_TRUSTED_CA=/protected/device/plant-web-ca.pem
```

The custom CA is optional when the proxy certificate chains to the platform
trust store. A protected `FRAKTAL_GATEWAY_BEARER_TOKEN` is supported where mTLS
is unavailable. Client certificates/keys, custom trust, and bearer tokens are
rejected on `ws://`; they require `wss://`. Browser HMI authentication is
handled by the browser/reverse proxy (for example an interactive session or
managed browser client certificate). These secrets are never stored in the
Fraktal connection-settings JSON.

## Disconnect and command behavior

The gateway and native non-browser clients use a 2 s WebSocket Ping/Pong
heartbeat. The gateway heartbeat also covers browser clients, whose API does not
expose Ping/Pong. A dead link closes promptly, snapshots reconnect with jittered
exponential backoff from 250 ms to 5 s, and a cold HMI start retries from 500 ms
to 5 s. The operator shell is removed on the first stale snapshot and returns
only after fresh PLC data reaches `LIVE`.

Writes are attempted exactly once. They are not queued while reconnecting and
are never replayed after an ambiguous disconnect. Each HMI mailbox command is
one globally serialized, commit-last batch; the gateway rejects standalone,
duplicate, or skipped `Sequence` commits. The operator must reissue a command
after the connection is proven live.

## Windows tray deployment

Run `FraktalSetup.exe` as the Windows user that operates the local HMI and
select the **Gateway + Web HMI** component in the wizard (with the PLC endpoint).
The tray menu exposes Ready/PLC unavailable/stopped state plus Start, Stop,
Restart, **Open Web HMI**, configuration, logs, health, and the deployment
guide. It supervises unexpected gateway exits with capped restart backoff. A
clean exit from the expiring commissioning profile remains stopped so the tray
cannot defeat the commissioning TTL.

Tray autorun occurs at user sign-in. For a dedicated kiosk or auto-logon HMI
this is the plug-and-produce option. If the gateway must run before login or
while nobody is logged in, deploy the headless executable through Task Scheduler
under a dedicated least-privilege account instead; the tray installer is not a
Windows service. Do not put the OPC UA password in `gateway.args`—provision
`FRAKTAL_OPCUA_USERNAME` and `FRAKTAL_OPCUA_PASSWORD` for the gateway identity
through the site's protected credential/process environment mechanism.

## Linux systemd service

Create a non-login `fraktal-gateway` user, copy the complete platform package
(including `web/`) to `/opt/fraktal-gateway`, and install
`fraktal-gateway.service` in
`/etc/systemd/system`. Copy `fraktal-gateway.env.example` to
`/etc/fraktal/fraktal-gateway.env`, replace every placeholder, make it
root-owned mode `0600`, and keep the private key root-owned with group
`fraktal-gateway` and mode `0640`. The trust/certificate directories should be
readable only by that service identity. Set
`FRAKTAL_OPCUA_PRIVATE_KEY_PASSWORD` in the protected environment file only
when the PEM key is encrypted.

The supplied unit starts in `production` and serves
`/opt/fraktal-gateway/web`. Use a deliberate systemd override for either
temporary anonymous profile instead of weakening the shipped unit. Reload
systemd, enable, start, and verify `/livez`, `/readyz`, `/`, `/fraktal`
discovery, and an acknowledged mailbox request separately.

For Windows unattended startup, use Task Scheduler under a dedicated
least-privilege account whether or not a user is logged on. Secure that account's
private-key directory and deployment environment; do not embed its OPC UA
password in task arguments.
