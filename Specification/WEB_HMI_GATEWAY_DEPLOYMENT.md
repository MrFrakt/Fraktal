# Fraktal Web HMI and Gateway Deployment Walkthrough

This walkthrough takes a deployed, TF6100-published Fraktal PLC from OPC UA to
a local or remote browser HMI. It covers the shipped Windows installer and the
Linux systemd package. Follow `FIRST_PROJECT_AGENT_GUIDE.md` through Phase E
first; this document does not replace PLC, TF6100, or functional-safety
commissioning.

## 1. Resulting topology

The gateway is the only component that talks OPC UA to the PLC. It also serves
the compiled Flutter Web HMI, so a separate static web server is not required.

```text
same-host browser
    http://127.0.0.1:8080/
              |
              v
Fraktal gateway on loopback ---- opc.tcp/SignAndEncrypt ---- TF6100 ---- PLC
    | static Web HMI
    | /fraktal WebSocket
    | /livez /readyz /healthz

remote browser
    https://hmi-cell-01.example/
              |
      authenticated TLS reverse proxy
              |
              v
    http://127.0.0.1:8080/ + ws://127.0.0.1:8080/fraktal
```

The gateway always binds to loopback. Remote access therefore has one explicit
security boundary: a same-host reverse proxy authenticates the browser,
terminates TLS, and forwards ordinary HTTP plus the WebSocket upgrade.

## 2. Choose a deployment path

| Target | Recommended path | Starts automatically | Web HMI included |
|---|---|---|---|
| Windows kiosk/engineering HMI user | `FraktalSetup.exe` | At that user's sign-in, as a tray application | Yes |
| Windows without an interactive login | Headless package + Task Scheduler under a dedicated account | At boot/task trigger | Yes |
| Linux IPC | Packaged gateway + supplied systemd unit | At boot | Yes |
| Development only | `flutter run -d chrome` + packaged/source gateway | No | Chrome debug server; gateway on port 8080 |

The tray installer is ideal for a dedicated kiosk or auto-logon account. Use a
service/task identity when the gateway must run before login or while nobody is
logged in.

## 3. Prerequisites and recorded inputs

Do not install the HMI layer until these checkpoints are known:

- PLC target identity, runtime name, ADS port, and active `Port_<ADS port>.tmc`;
- TF6100 initialized, licensed, and publishing the PLC Data Access namespace;
- authorized browse showing `PLC1/MAIN/<Root>/Status`, `HmiRequest`, and
  `HmiResponse`;
- chosen gateway profile and owner: `production`, `secure-anonymous`,
  `commissioning-anonymous`, or `isolated-anonymous`;
- exact root browse paths assigned to this gateway, for example
  `PLC1/MAIN/PneumaticPress`;
- production gateway application URI, client certificate/private key, server
  trust list, dedicated TF6100 username/password, and their provisioning owner;
- local-only or remote-browser URL and, for remote access, the reverse proxy's
  TLS certificate and authentication method.

Production shall use a trusted OPC UA client certificate, `SignAndEncrypt`, and
a dedicated TF6100 user. Anonymous/None is limited to bounded commissioning or
a documented physically isolated exception.

## 4. Build one gateway + Web HMI package

The packaging command builds the Flutter Web release first, then the native
gateway and bridge. It copies the exact Web output into the platform package.

```powershell
cd C:\Projects\Fraktal\FraktalCore\HMI
flutter pub get
flutter analyze
flutter test

cd gateway
dart pub get
dart run tool/build_gateway.dart --clean
```

Windows outputs:

```text
HMI\build\gateway\windows-x64\
  fraktal_gateway.exe
  fraktal_gateway_tray.exe
  fraktal_opcua.dll
  WEB_HMI_GATEWAY_DEPLOYMENT.md
  web\index.html
  ...

HMI\build\gateway\installer\FraktalSetup.exe  # includes verified Caddy
```

Linux outputs the equivalent `linux-x64` package with `fraktal_gateway`,
`libfraktal_opcua.so`, `web/`, the systemd unit, and environment example.
Build on the target operating system; the native gateway is not cross-compiled.

Sign the Windows installer and binaries with the organization's Authenticode
certificate before production distribution. Record release hashes with the
PLC/TMC and configuration exports.

## 5. Windows installer walkthrough

### 5.1 Install

1. Sign or verify the supplied installer according to site policy.
2. Run `FraktalSetup.exe` as the Windows account that will own the tray.
3. In the wizard, select **Fraktal Gateway + Web HMI**. The installer asks the
   local TwinCAT router for its configured AMS Net ID and seeds
   `ads://<detected-AmsNetId>:851`. **Use the HMI / local PLC endpoint for the
   Gateway** is checked by default, so the Gateway endpoint mirrors that value
   and its duplicate field is disabled. Clear the checkbox only when the
   Gateway must use a different ADS runtime or an OPC UA endpoint. If router
   discovery is unavailable, the wizard visibly falls back to
   `ads://127.0.0.1.1.1:851`; confirm it before installation.
4. For a remote browser, leave **secure remote Web HMI** selected, confirm the
   suggested `https://<controller-IP>` origin, enter the proxy account/password,
   and allow the local-subnet Windows Firewall rule. For same-host-only use,
   clear that option.
5. The installer writes program files to
   `%LOCALAPPDATA%\Programs\Fraktal Gateway`, writes the endpoint as
   `--plc-endpoint`, normalizes the loopback `--port` to numeric `8080`, and,
   when selected, writes the exact public `--allow-origin` in `gateway.args`.
   It preserves site data under
   `%LOCALAPPDATA%\Fraktal\Gateway`, creates Start Menu and Startup shortcuts,
   starts the tray, and opens `gateway.args`.
6. The remote option configures the bundled, checksum-pinned Caddy executable
   at `%LOCALAPPDATA%\Fraktal\Gateway\proxy\Caddyfile`. It hashes the password
   through Caddy's stdin, stores only the Argon2id hash, generates an internal
   LAN CA, validates the Caddyfile before publishing it, and exposes only the
   selected HTTPS port from Domain/Private profiles and the local subnet. The
   checked **Trust this gateway CA** option installs the public root into the
   current Windows user's Root store on the gateway PC only. Accept Windows'
   visible certificate-security confirmation when prompted; the installer
   aborts that step after two minutes rather than waiting invisibly forever.
7. Upgrades replace binaries and the Web HMI but preserve `gateway.args`, proxy
   configuration/password hash, proxy CA, OPC UA PKI, and logs when both new
   password fields are left blank. Uninstall also preserves those site-owned
   files intentionally.

### 5.2 Configure `gateway.args`

The file uses one option or value per line. Environment variables are expanded.
The installed production template already includes the Web root:

```text
--plc-endpoint
opc.tcp://127.0.0.1:4840
--port
8080
--path
/fraktal
--web-root
%LOCALAPPDATA%\Programs\Fraktal Gateway\web
--allow-origin
https://192.168.100.126
--security-profile
production
--security-policy
http://opcfoundation.org/UA/SecurityPolicy#Basic256Sha256
--application-uri
urn:fraktal:gateway:CELL-01
--client-certificate
%LOCALAPPDATA%\Fraktal\Gateway\pki\own\certs\fraktal-gateway.der
--client-private-key
%LOCALAPPDATA%\Fraktal\Gateway\pki\own\private\fraktal-gateway.pem
--trust-list
%LOCALAPPDATA%\Fraktal\Gateway\pki\trusted\certs
--read-root
PLC1/MAIN/PneumaticPress
--write-root
PLC1/MAIN/PneumaticPress
```

Repeat `--read-root` and `--write-root` for a multi-root deployment. Add a
separate `--read-root` for standalone published data such as
`PLC1/GVL_PressFieldbus/Topology`. Without `--read-root`, the upstream OPC UA/ADS
identity remains the read boundary; without `--write-root`, the gateway is
deliberately read-only. Never use `--allow-all-root-mailboxes` as the production
scope.

Do not put passwords in `gateway.args`. Provision these for the gateway process
identity through the site's protected Windows credential/process-environment
mechanism:

```text
FRAKTAL_OPCUA_USERNAME
FRAKTAL_OPCUA_PASSWORD
FRAKTAL_OPCUA_PRIVATE_KEY_PASSWORD   # only for an encrypted private key
```

Restart the tray after changing process credentials. Use the tray menu to edit
gateway/proxy configuration, open logs, restart both supervised processes, open
the Web HMI, or inspect gateway health.

The reverse-proxy password is separate from
`FRAKTAL_OPCUA_PASSWORD`: one authenticates the browser at HTTPS/WSS; the other
authenticates the gateway to TF6100. Neither belongs in `gateway.args`.

### 5.3 Local acceptance

1. Restart the gateway from the tray.
2. Confirm the tray reaches **Ready**, not merely **Running - PLC unavailable**.
3. Open `http://127.0.0.1:8080/healthz`; expect protocol
   `fraktal.opcua.gateway.v1`, status `ready`, and `plcReady: true`.
4. Open `http://127.0.0.1:8080/`. The Web HMI and WebSocket now share one origin.
5. On first run, select languages and Units. A release Web build derives
   `ws://127.0.0.1:8080/fraktal` from that page automatically. The endpoint
   remains editable for diagnostics.

For an expiring local commissioning session, explicitly change the profile to
`commissioning-anonymous` and add `--commissioning-ttl-minutes 120`. A clean TTL
shutdown remains stopped; tray supervision does not restart it. Restore the
production profile and remove temporary TF6100 Anonymous rights afterward.

## 6. Linux systemd walkthrough

Build the package on Linux, then install it using a dedicated non-login account:

```sh
sudo useradd --system --home /nonexistent --shell /usr/sbin/nologin fraktal-gateway
sudo install -d -o root -g fraktal-gateway -m 0750 /opt/fraktal-gateway
sudo cp -a build/gateway/linux-x64/. /opt/fraktal-gateway/
sudo chown -R root:fraktal-gateway /opt/fraktal-gateway
sudo chmod 0750 /opt/fraktal-gateway/fraktal_gateway

sudo install -d -o root -g fraktal-gateway -m 0750 /etc/fraktal
sudo install -m 0600 -o root -g root \
  /opt/fraktal-gateway/fraktal-gateway.env.example \
  /etc/fraktal/fraktal-gateway.env
sudo install -m 0644 /opt/fraktal-gateway/fraktal-gateway.service \
  /etc/systemd/system/fraktal-gateway.service
```

Edit `/etc/fraktal/fraktal-gateway.env`, replace every placeholder, and protect
the private key/trust material with the service account's ACLs. Edit the unit's
`--plc-endpoint`, add one `--read-root` per assigned Unit/shared data subtree,
and add one `--write-root` per assigned Unit. The supplied unit
already serves `/opt/fraktal-gateway/web`.

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now fraktal-gateway
systemctl status fraktal-gateway --no-pager
curl --fail http://127.0.0.1:8080/livez
curl --fail http://127.0.0.1:8080/readyz
```

Open `http://127.0.0.1:8080/` locally or add the remote reverse proxy described
next. The bundled proxy installation is currently Windows-only; Linux uses the
site proxy/service policy. systemd restarts process failures; OPC UA/WebSocket
reconnect is handled inside the application and never replays an HMI write.

## 7. Remote HTTPS/WSS browser deployment

Use one public origin, for example `https://192.168.100.126` or
`https://hmi-cell-01.example`. Add that exact origin to the gateway
configuration:

```text
--allow-origin
https://hmi-cell-01.example
```

On Windows, select **secure remote Web HMI** in `FraktalSetup.exe`; the wizard
performs this configuration and writes the corresponding `--allow-origin`.
It also creates these site-owned artifacts:

```text
%LOCALAPPDATA%\Fraktal\Gateway\proxy\Caddyfile
%LOCALAPPDATA%\Fraktal\Gateway\proxy\public-origin.txt
%LOCALAPPDATA%\Fraktal\Gateway\proxy\FraktalGatewayRootCA.crt
%LOCALAPPDATA%\Fraktal\Gateway\proxy\storage\   # includes the private CA key
```

Copy `FraktalGatewayRootCA.crt` through the commissioning trust channel and
install it as a trusted root on every authorized remote HMI device. For example,
on a managed Windows HMI account:

```powershell
certutil -user -addstore -f Root .\FraktalGatewayRootCA.crt
```

Trust on the gateway PC does not propagate over the network. A browser opened
on an engineering laptop, panel PC, or mobile device remains untrusted until
that same public root is installed through the site's managed trust process.
The installer log distinguishes **exported** from **trusted** so creation of a
certificate is never mistaken for client trust.

Do not distribute anything below `proxy\storage`; it contains the CA private
key. A site PKI certificate may replace `tls internal` in the Caddyfile, in
which case every client must trust that site chain instead. Restart the tray
after a reviewed manual Caddyfile change.

Linux or a site-managed Windows proxy shall equivalently:

- listen on HTTPS with a certificate trusted by every HMI device;
- authenticate access to both the static HMI and the WebSocket upgrade;
- proxy ordinary HTTP paths to `http://127.0.0.1:8080`;
- proxy `/fraktal` as WebSocket to `ws://127.0.0.1:8080/fraktal`;
- preserve `Origin` and WebSocket upgrade headers/control frames;
- use an idle timeout comfortably above the 2 s heartbeat;
- apply connection/rate limits and audit access;
- avoid publicly exposing health endpoints unless an authenticated monitoring
  policy requires them.

The bundled Windows profile uses HTTP Basic authentication only inside TLS.
Managed-browser SSO, mTLS client identity, centralized account lifecycle, and
cross-host/load-balanced proxying remain site deployment adapters; replace the
generated Caddy authentication block when those policies are required.

Do not bind the Fraktal gateway directly to a LAN interface and do not treat
Origin checking as authentication. Expose only the reverse proxy's HTTPS port
through the host/network firewall.

For scripted Windows installation, provide the password only in the child
process environment; it is consumed and cleared after hashing:

```powershell
$env:FRAKTAL_PROXY_PASSWORD = '<from protected deployment secret>'
.\install_fraktal.cmd `
  -Components Gateway `
  -GatewayEndpoint opc.tcp://127.0.0.1:4840 `
  -EnableRemoteAccess `
  -PublicOrigin https://192.168.100.126 `
  -ProxyUsername fraktal `
  -ConfigureFirewall `
  -TrustProxyCaForCurrentUser
Remove-Item Env:FRAKTAL_PROXY_PASSWORD
```

When opened from HTTPS, a release Web HMI automatically derives
`wss://hmi-cell-01.example/fraktal`. Changing the public origin creates a new
browser storage origin, so language/Unit assignment must be commissioned again
or migrated deliberately.

## 8. Layered acceptance evidence

Record each checkpoint separately:

| Checkpoint | Command/observation | Pass evidence |
|---|---|---|
| Process | `GET /livez` | HTTP 200, `status: live` |
| PLC readiness | `GET /readyz` | HTTP 200 after an observed good OPC UA operation |
| Static HMI | `GET /` | Flutter page loads from the intended origin |
| WebSocket | Browser connection log | channel opens at same-origin `/fraktal` |
| Fraktal discovery | Unit selector | expected root paths; no truncation/aliases presented as roots |
| Scope | saved Unit assignment | only approved roots visible/writable |
| Mailbox commit | HMI request log | one commit-last batch, new sequence |
| PLC acknowledgement | `HmiResponse` | matching `AckSequence`, `Accepted`, `Diagnostic` |
| State effect | published contract | expected mode/status changes |
| Link loss | unplug/stop proxy/gateway | shell disappears immediately; no write queued/replayed |
| Recovery | restore path | fresh snapshot returns `LIVE`; operator reissues command |

`/healthz` is a compatibility summary. `/livez` is for process supervision;
`/readyz` is for PLC availability and returns 503 after an observed OPC UA
failure. A successful process or TCP probe is not a successful Fraktal session.

## 9. Upgrade, rollback, and backup

Before an upgrade, record hashes and back up:

- Windows: `%LOCALAPPDATA%\Fraktal\Gateway`;
- Linux: `/etc/fraktal`, PKI paths, unit overrides, and the current
  `/opt/fraktal-gateway` release;
- reverse-proxy configuration/certificates;
- browser URL and assigned Unit paths;
- PLC/TMC, TF6100 export, and gateway/HMI version.

The Windows installer stops the existing tray/gateway, atomically replaces the
compiled Web directory, preserves site data, and restarts the tray. On Linux,
stage the new package in a versioned directory or backup the old package before
copying, then restart and repeat all acceptance checkpoints. Rollback restores
the matching gateway + Web HMI pair; do not mix arbitrary UI and gateway
protocol versions.

## 10. Fast troubleshooting

| Symptom | First check |
|---|---|
| Browser cannot load `/` | Gateway/tray process, `--web-root`, `web/index.html`, then reverse-proxy HTTP route |
| Page loads but stays Connecting | Browser developer console and `/fraktal` upgrade; check exact `--allow-origin` and proxy WebSocket support |
| Local works, remote fails | HTTPS certificate/authentication, firewall, proxy upgrade headers, public origin |
| `/livez` works, `/readyz` is 503 | OPC UA endpoint/profile/certificate/user, then TF6100 namespace authorization |
| Unit selector empty | Namespace URI/browse rights, TMC root marker, truncated snapshot—not static hosting |
| Control rejected | `HmiResponse.AckSequence`, `Accepted`, and `Diagnostic`; do not restart at ping |
| Browser reconnects but command did not repeat | Correct fail-safe behavior; commands are never replayed after an ambiguous disconnect |
| Installer tray is Running but not Ready | Open gateway log; production credentials/PKI or PLC access are incomplete |

For deeper PLC/TF6100 diagnosis, return to the layered table in
`FIRST_PROJECT_AGENT_GUIDE.md` Section 9.
