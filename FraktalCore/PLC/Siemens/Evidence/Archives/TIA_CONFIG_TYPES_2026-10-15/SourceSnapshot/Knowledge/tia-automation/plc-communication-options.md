# Talking to an S7-1200 / S7-1500 from a host without a runtime licence

Written 2026-10-08 for the Fraktal/TIA transport decision (Part IV §1). Marks:
**[measured]** on the bench 1214C V4.7.3, **[manual]** Web server function
manual 109977246 (11/2025, `..\manuals\downloaded\WebServer_FunctionManual_109977246.txt`),
**[api]** `PublicAPI\V20\Siemens.Engineering.dll` reflection, **[sheet]** data sheet.

## Options compared

| Protocol | Licence | Symbolic / optimized DBs | Browse | Auth / security | Verdict for an HMI gateway |
|---|---|---|---|---|---|
| **Web API** (JSON-RPC 2.0, `POST /api/jsonrpc`, HTTPS) | none | yes — `"DB".Member.Sub[3]` names | `PlcProgram.Browse` | web-server users with per-right permissions, token in `X-Auth-Token`, TLS | **default choice**: licence-free, symbolic, browsable, authenticated |
| OPC UA server (embedded) | **runtime licence per CPU** (S7-1200 "Basic"; S7-1500 by size) | yes | yes, subscriptions | UA security policies, users | best protocol, but paid |
| S7comm PUT/GET (port 102) | none | **no** — absolute addresses in non-optimized DBs only | no | none | avoid; hardening guides say leave PUT/GET off; on S7-1200 the switch is not even reachable through Openness **[measured]** |
| S7CommPlus | none | yes | yes | TLS (V17+) | proprietary, undocumented — not a basis |
| Open user communication (TSEND_C / TRCV_C, TCP/UDP) | none | whatever you serialize | no | none unless you build it (Secure OUC with TLS exists on newer FW) | good for a fixed record (Fraktal test harvest, port 2000) **[measured]**; a full protocol is all yours to write |
| PROFINET IO (I-device) | none | no — fixed byte image | no | none | fieldbus, not a host protocol; ≤ 1,024 bytes each way on a 1200 I-device; host needs a PN controller stack |
| Modbus TCP (MB_SERVER) | none | no — flat registers | no | none | flat, no names |

## Web API facts that matter

- Endpoint `https://<cpu>/api/jsonrpc`, JSON-RPC 2.0; a JSON **array** of requests is
  a batch, answered in one HTTP response; each element has its own `id`/`error`. **[manual]**
- `Api.Login {user, password}` → `{token}`; send `X-Auth-Token: <token>`; tokens expire
  when idle (re-login on "Invalid token"). `Api.Ping`, `Api.Version`, `Api.Browse`
  (method list), `Api.GetQuantityStructures` (session/request limits) need no login. **[manual]**
- `PlcProgram.Browse {var?, mode: "var"|"children", type?}` → array of
  `{name, datatype, has_children?, db_number?, array_dimensions?[{start_index,count}],
  max_length?, read_only?, address?}`. Root browse = `{"mode":"children"}`. Needs
  `read_value`. **[manual]**
- `PlcProgram.Read {var, mode: "simple"|"raw"}` reads **one** tag; batch many reads in
  one array request. Errors: 200 address does not exist, 201 invalid address, 203
  invalid array index, 204 unsupported data type. **[manual]**
- `PlcProgram.Write {var, value, mode}` writes **one** tag; needs `write_value`. **[manual]**
- Exposure: the tag must have "Accessible from HMI/OPC UA/Web API" (and "Writable from
  …" for writes) — the same attributes OPC UA uses (`ExternalAccessible`,
  `ExternalWritable` in SCL source). **[manual]**
- The 11/2025 manual is written for S7-1500 and S7-1200 **G2**; the Siemens Web API
  client compatibility table lists S7-1200 FW 4.5/4.6/4.7 — the method set on a G1
  V4.7 must be read from `Api.Browse`, not assumed. **[manual]** (open: measure)

## Measured on the 1214C V4.7.3 (2026-10-08) [measured]

- `Api.Version` 1.473; 14 methods: `Api.Browse, ChangePassword, GetAuthenticationMode,
  GetCertificateUrl, GetPasswordPolicy, GetPermissions, Login, Logout, Ping, Version,
  PlcProgram.Browse, PlcProgram.Read, PlcProgram.Write, Syslog.Browse`.
  `Api.GetQuantityStructures` → `-32601` (not offered).
- Leaf-only reads: a struct or `DTL` read whole → `204 Unsupported address`; read members.
- Hidden member (`ExternalAccessible := 'False'`) → `200 Address does not exist`;
  `ExternalWritable := 'False'` → write `205 Address is read-only`; no token → `2 Permission
  denied`; second `Api.Login` with a live token → `101 Already Authenticated`.
- Cost ≈ 57 ms per request + ≈ 15 ms per leaf (10 leaves 205 ms; 126 leaves 2.13 s even in
  one batch). Poll a small fast tier, read the rest on demand.
- Browse of a 126-leaf instance DB: 19 calls, 2.56 s.
- **TLS handshake ≈ 2.75 s** on the 1214C (TCP connect 3–17 ms). The CPU closes an
  idle HTTPS connection after 1–2 s; the login token survives on a new connection.
  Keep ONE connection open and warm (`Api.Ping` < 1 s idle). Dart's `HttpClient`
  opened a new connection per request to this server (~2.8 s each) — use a raw
  persistent `SecureSocket` or another client that demonstrably reuses connections.
- The web server serves **one request at a time across sessions**: a large batch
  delays every other client. Keep batches small (~20 leaves).
- Web API polling cost the PLC ≈ +0.23 ms mean cycle (2.24 → 2.47 ms) at continuous
  full-tree reads; single-cycle samples unchanged.
- Expired token (2.5 min idle) → error `2`; re-login without sending the old token.

## Switching it on through Openness V20

- CPU attributes: `WebserverActivate` (Boolean), `WebserverHttpsOnly`,
  `WebserverCertificate` (Object), `WebserverEntryPage`, `WebserverAutomaticUpdate`,
  `WebserverUpdateInterval`; interface attribute `UseWebServerForInterface`
  ("Enable Web server using this interface", S7-1500 listing). **[api]** HW parameter doc
- Users: `cpu.GetService<WebserverUserManagement>().WebserverUsers.Create(name,
  WebserverUserPermissions, SecureString)`; permission bits: `DoDiagnosis=1,
  ReadTag=2, ModifyTag=4, ReadTagStatus=8, ModifyTagStatus=16, AcknowledgeMessages=32,
  …, ChangeOperatingMode=1024, WriteFirmware=4096, Backup=32768, Restore=65536`.
  `SimpleWebserverUserManagement` (permissions `ReadOnly`/`ReadWrite`, no `Create`) is
  a different, simpler family. **[api]**
- Certificate: the TIA editor makes one when you enable the web server; Openness
  does not. Same thing by API: `LocalCertificateManager` (a device-item service) →
  `.LocalCertificateStore.GetCertificateTemplate(CertificateUsage.WebServer)` →
  `.Certificates.Create(template)` → `cpu.SetAttribute("WebserverCertificate", cert)`.
  `CertificateUsage`: `Tls=1, OpcUaClient=2, OpcUaClientServer=3, OpcUaServer=4,
  WebServer=5`. **[api]** — implemented as `Fraktal.Tia.Cli webserver-certificate`.

## Tools

- `C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\tia_webapi.py` — stdlib client:
  pinned-fingerprint HTTPS (first contact `--trust-first`), login from
  `FRAKTAL_TIA_WEB_PASSWORD`, `probe`, `browse`, `tree`, `snapshot` (batch-read timing),
  `mailbox` (arguments, then the commit marker alone, wait for the ack, never replay).
- `Spikes\S2_Shape\webapi_1214c.plan` — the Openness plan that enables it on the bench.
