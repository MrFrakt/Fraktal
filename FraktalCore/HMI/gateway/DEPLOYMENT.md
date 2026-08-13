# Fraktal OPC UA WebSocket gateway

This headless Windows/Linux service owns one native PLC session and exposes
the versioned `fraktal.opcua.gateway.v1` protocol on loopback at `/fraktal`.
A host that serves several controllers runs **one instance per PLC** — see
[Instances: one gateway per PLC](#instances-one-gateway-per-plc).
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

## Instances: one gateway per PLC

One process owns one PLC session, so a host serving several controllers runs
several instances. Isolation is the point: a stalled ADS router, an unreachable
controller, or a native-bridge fault takes down that PLC's gateway and nothing
else, and each instance keeps its own AMS/OPC UA session, write scope, log, and
restart backoff.

An instance is a folder, and its arguments file is the only place its settings
live:

```text
%LOCALAPPDATA%\Fraktal\Gateway\instances\<name>\gateway.args
%LOCALAPPDATA%\Fraktal\Gateway\logs\<name>\gateway.log
```

The folder name is the instance name (1–32 letters, digits, `.`, `_`, `-`); it
is passed as `--instance-name`, reported by `/healthz`, and printed in every log
line. There is no separate index file to keep in step — discovery is "every
subfolder that has a `gateway.args`", implemented once for the scripts in
`deploy/windows/fraktal_instances.ps1` and once in the tray.

The wizard also asks, per instance, whether the **browser** may command that
PLC, and writes the answer as `--write-root`. An instance with no write root is
a read-only viewer: the Web HMI displays everything the PLC publishes and the
gateway refuses every operator command — mode changes, start/stop, manual
commands — before it reaches the PLC. That is a supported deployment, not a
fault, and the wizard confirms it rather than letting it happen by default:
`--write-root` is where the read-only decision for the web path lives.

The scope's shape follows the transport, and the installer cannot infer it: over
ADS a root Unit is `PneumaticPress`, over TF6100 OPC UA the same Unit is
`PLC1/MAIN/PneumaticPress`. Comma-separate several roots for a multi-root HMI.
The native desktop HMI talks to the PLC directly and is unaffected either way,
and the PLC re-checks its own §7.6/§7.7 release and access gates regardless —
the gateway scope only ever *narrows* what a browser may attempt.

Two rules the installer enforces, because breaking either fails silently:

- **Every instance needs its own `--port`.** Two instances on one port leave one
  PLC permanently unreachable behind a listener that belongs to the other.
- **Every published instance needs its own origin** (`https://host[:port]`). A
  release Web HMI derives its WebSocket endpoint from the page origin, so PLCs
  cannot share one origin under different paths.

The tray supervises every instance it finds: per-instance Start/Stop/Restart,
configuration, logs, Web HMI, and health, plus Start/Stop/Restart all and
**Reload instances** after the set changes. Its icon and tooltip aggregate —
failure is the headline, so one unreachable PLC out of three never reads as
"Ready". A single-instance installation keeps the flat menu it always had.

An installation that predates instances keeps one `gateway.args` in the data
root; the tray still runs it, and the next install migrates that exact file
(site write roots, read scoping, and certificate paths included) into
`instances\<first>\gateway.args`, leaving `gateway.args.migrated` behind.
Removing an instance in the wizard retires it as `gateway.args.removed` rather
than deleting hand-written scope; re-adding the same name restores it.

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
`web/`; its installer also contains checksum-verified Caddy for optional secure
remote access. Linux contains `fraktal_gateway`, `libfraktal_opcua.so`, and
`web/`.

The Windows build also creates
`build/gateway/installer/FraktalSetup.exe`. It is a per-user, self-extracting
installer (built with IExpress + a PowerShell WinForms wizard) that installs
either or both components:

- **Fraktal HMI** — the native desktop app, which connects **ADS-direct** to the
  PLC on a TwinCAT host. Installed to `%LOCALAPPDATA%\Programs\Fraktal HMI` with
  a Start Menu shortcut (no autorun — it is an on-demand GUI).
- **Fraktal Gateway + Web HMI** — the browser-access path over ADS or OPC UA.
  Installed to `%LOCALAPPDATA%\Programs\Fraktal Gateway`; the tray starts
  immediately and a Startup shortcut starts it at future sign-ins.

The wizard requires at least one component. It asks the local TwinCAT router for
the configured AMS Net ID and seeds the HMI/local endpoint as
`ads://<AmsNetId>:851`; when detection is unavailable it visibly falls back to
`ads://127.0.0.1.1.1:851`.

The Gateway page carries a **list of instances, one per PLC**, prefilled from
the installation already on the PC (or with a single `default` instance on port
8080). **Add PLC…** appends one with the next free port and a suggested origin;
**Edit…** and **Remove** work on the selection. **Use the HMI / local PLC
endpoint for the first Gateway instance** is checked by default, so instance one
mirrors the HMI/local value; clear it to give it a different ADS runtime or
`opc.tcp://<host>:<port>`. The wizard refuses duplicate names, ports, and
origins before anything is written. The two components remain independent at
runtime — the HMI does not talk to the gateway.

On first install the HMI endpoint is seeded into
`%APPDATA%\Fraktal\HMI\connection.json` (the app still runs its own
language/unit wizard on first launch, with the endpoint pre-filled) and each
gateway instance gets its own `instances\<name>\gateway.args`. Existing
configuration, PKI files, logs, and the HMI connection settings are preserved
across upgrades and uninstall. When **secure remote Web HMI** is selected, the
wizard collects one proxy account for the whole host, publishes each instance
that has an origin as its own HTTPS site, writes the matching `--allow-origin`
into that instance only, generates a private LAN CA, stores only an Argon2id
password hash, and can add a Domain/Private local-subnet firewall rule covering
every published port. A separately visible, checked-by-default option trusts
that CA for the installing Windows user on the gateway PC only; each remote
browser device still needs the exported public root installed through the
commissioning trust channel. Windows may show a visible root trust confirmation;
it is bounded to two minutes so a blocked prompt cannot freeze the installer.
The installer always rewrites the installer-owned `--port` of each instance,
repairing malformed legacy values such as `8080\`.

The proxy Caddyfile, CA, and account hash live below
`%LOCALAPPDATA%\Fraktal\Gateway\proxy`. Leave both password fields blank during
an upgrade to preserve the account: the Caddyfile is regenerated from the
current instance set and the stored hash, so a PLC can be added without knowing
the browser password. A silent path exists for Group-Policy/AppLocker hosts:

```cmd
install_fraktal.cmd -Components HMI,Gateway -HmiEndpoint ads://192.168.1.6.1.1:851 -GatewayEndpoint opc.tcp://192.168.1.6:4840
```

Pass one repeatable `-GatewayInstance` spec per PLC instead of
`-GatewayEndpoint` for a multi-PLC host. Only `endpoint` is required; `name`
defaults to `default`, `instance2`, … and `port` to 8080, 8081, …:

```cmd
install_fraktal.cmd -Components Gateway ^
  -GatewayInstance "name=press;endpoint=ads://192.168.1.6.1.1:851;port=8080;writeroot=PneumaticPress" ^
  -GatewayInstance "name=oven;endpoint=opc.tcp://192.168.1.9:4840;port=8081"
```

`writeroot=` is what makes an instance commandable; omit it (as `oven` does
above) to install a read-only viewer. `-WriteRoot` is the single-instance
shorthand alongside `-GatewayEndpoint`.

For silent secure remote access, place the password only in the installing
process environment and give every published instance an `origin=`:

```powershell
$env:FRAKTAL_PROXY_PASSWORD = '<from protected deployment secret>'
.\install_fraktal.cmd -Components Gateway `
  -GatewayInstance "name=press;endpoint=ads://192.168.1.6.1.1:851;port=8080;origin=https://192.168.100.126" `
  -GatewayInstance "name=oven;endpoint=opc.tcp://192.168.1.9:4840;port=8081;origin=https://192.168.100.126:8443" `
  -EnableRemoteAccess -ProxyUsername fraktal `
  -ConfigureFirewall -TrustProxyCaForCurrentUser
Remove-Item Env:FRAKTAL_PROXY_PASSWORD
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
  -ReadRoot PLC1/MAIN/PneumaticPress `
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
On a multi-PLC host each instance answers on its own port — `:8080`, `:8081`, …
— so the local page, the WebSocket, and the health endpoints of one PLC are all
found under that PLC's port. `/healthz` reports `instance` so a reply can never
be attributed to the wrong controller.

Gateway reads may be limited independently; without `--read-root`, the upstream
OPC UA/ADS identity remains the read boundary. Gateway writes are limited to
published `HmiRequest` fields and are read-only until at least one write root is
assigned:

```text
--read-root PLC1/MAIN/PneumaticPress
--write-root PLC1/MAIN/PneumaticPress
```

Repeat the options for a multi-root HMI. Add another `--read-root` for any
standalone published data subtree (for example a fieldbus topology) the assigned
Units consume. `--allow-all-root-mailboxes` is an explicit commissioning
override, not a production scope. The PLC still applies its access and release
checks.

After the first discovery snapshot, the HMI sends compact path-index tiers. The
gateway omits on-demand rings/topology from cyclic reads and serves them through
bounded targeted reads only while their view is open. With multiple browsers, a
path is slowed or omitted only when every connected browser agrees, so opening a
new client cannot starve an existing one.

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

The Windows installer automates this same-host profile with bundled Caddy. It
supervises every gateway instance plus the one proxy from the tray, configures
Basic authentication inside TLS, and exports only the public LAN-CA certificate
as:

```text
%LOCALAPPDATA%\Fraktal\Gateway\proxy\FraktalGatewayRootCA.crt
```

Install that certificate as a trusted root on each authorized browser device
before opening the HTTPS URL. Never copy `proxy\storage`, which contains the CA
private key. One Caddyfile carries one site block per published instance, all
sharing the single browser account in `proxy\basic-auth.txt` (account name plus
Argon2id hash — the same pair the Caddyfile already contains, kept so the
routing can be regenerated when a PLC is added without re-entering the
password). Linux, enterprise SSO, and managed mTLS proxy policies remain
site-owned adapters.

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
select the **Gateway + Web HMI** component in the wizard (with one instance per
PLC). The tray menu exposes Ready/PLC unavailable/stopped state plus Start,
Stop, Restart, **Open Web HMI**, configuration, logs, and health — per instance
once there is more than one, under a submenu named after it, alongside Start/
Stop/Restart all, **Reload instances**, the proxy configuration, and the
deployment guide. It supervises unexpected gateway and proxy exits with capped
restart backoff, independently per instance, so one PLC's crash loop never
delays another's recovery. A clean exit from the expiring commissioning profile
remains stopped so the tray cannot defeat the commissioning TTL.

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

For several PLCs, use the templated unit instead: install
`fraktal-gateway@.service`, copy `fraktal-gateway-instance.env.example` to
`/etc/fraktal/instances/<instance>.env` once per controller with that PLC's
`FRAKTAL_PLC_ENDPOINT` and its own `FRAKTAL_GATEWAY_PORT`, then
`systemctl enable --now fraktal-gateway@<instance>`. Shared credentials and PKI
stay in `/etc/fraktal/fraktal-gateway.env`, which the template reads first. Do
not enable both the plain and templated unit for the same PLC. The site reverse
proxy publishes one origin per instance; the bundled proxy remains Windows-only.

For Windows unattended startup, use Task Scheduler under a dedicated
least-privilege account whether or not a user is logged on. Secure that account's
private-key directory and deployment environment; do not embed its OPC UA
password in task arguments.
