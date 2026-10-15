# Fraktal/TIA — S1W Web API leg and the ASCII rebuild, bench 1214C (2026-10-08)

**What this records.** The licence-free self-description transport chosen by the
project owner on 2026-10-08 (Part IV §1 transport decision): the S7 Web API,
enabled headlessly on the bench station project, downloaded, and measured from a
host client; and three download-and-restart runs of the ASCII-converted S2 fixture.
Raw material is in [`TIA_S1W_WEBAPI_2026-10-08/`](TIA_S1W_WEBAPI_2026-10-08/)
(numbered in the order things happened, failures included).

| Item | Value |
|---|---|
| Target | CPU 1214C DC/DC/DC `6ES7 214-1AG40-0XB0`, FW V4.7.3, 192.168.0.10 — identified by `s7_probe.py ident` (SZL 0x0011) immediately before **each** of the three downloads |
| Authorization | owner: bench free to use (2026-10-08); this session's download and the lowered protection level confirmed by the owner's "go on" after both were named |
| Toolchain | TIA Portal V20, Openness V20; `Fraktal.Tia.Cli` builds `d8oluUCD…` (probes), `rlDzE2Gb…` (plan), `h2hnPuq1…` (downloads) — Base64 SHA-256, each whitelisted before use |
| Station project | `%LOCALAPPDATA%\Fraktal\TiaStations\FrkSpikeS2\FrkSpikeS2.ap20` (not in the repository; holds the PG/PC and web certificates) |
| Deployed program | `FraktalCore/PLC/Siemens/Spikes/S2_Shape`, 26 sources, **ASCII** (T-ASCII); `sha256sum *.udt *.db *.scl \| sha256sum` = `ffa03293d1846b58…`; repository at `7ba25cc` + uncommitted Siemens tree |
| Client | `FraktalCore/PLC/Siemens/tools/tia_webapi.py` (stdlib), Python on the engineering workstation, same subnet |

> The 2026-10-08 first-bench record ([`TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md`](TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md))
> describes the image built **before** the ASCII conversion; its source-identity
> statement applies to those pre-conversion sources. This record is the first for
> the ASCII sources. Neither record is edited to match the other.

## 1. Build and round-trip (offline)

`build_1214c.plan`: 26 sources generated, software compile **0 errors / 0
warnings**, hardware up to date (`01_…`). The exported sources (41 files) are a
UTF-8 BOM followed by pure ASCII — the mojibake of the first record is gone.

## 2. Enabling the web server headlessly — what Openness V20 can and cannot do on a 1214C V4.7

| Step | Result | Log |
|---|---|---|
| `WebserverActivate = true` | works | `02` |
| `WebserverHttpsOnly`, interface `UseWebServerForInterface` | `EngineeringNotSupportedException` — not on this family | `02` |
| HTTPS certificate | `LocalCertificateManager` → `GetCertificateTemplate(WebServer)` → `Certificates.Create` → `WebserverCertificate`: works (`PLC-1/Webserver-2`, valid to 2037) | `02` |
| Classic web users (`WebserverUserManagement`) | **not offered** — the 1214C V4.7 keeps web users in UMAC | `02` (plan stopped before `save`; nothing written) |
| UMAC: rights the device offers | 21 device function rights, among them `WebReadTags`, `WebWriteTags` | `03` |
| Access control `EnabledWithAccessControlViaAccessLevel` | compile error until access without login is full access or a full-access password is set → anonymous user activated with system role `PLCAdministrator` (bench) → compile **warning** "Anonymous … Full access … only for testing" | `03`, `07` |
| Certificate type (internal `WebserverCertificateType`: 0 none, 1 hardware-generated, 2 downloaded with the software — found by reflection over `Siemens.Simatic.Hwcn.IntItf.dll`) | **neither getter nor setter supported** by Openness (`get_…`/`set_… is not supported`); the compile error "No certificate type is assigned to the Web server security" remains | `04`–`07` |
| Manual step | owner set the type once in the TIA editor ("loaded via the software"), saved | — |
| Station compile after it | hardware **0/0**, software **0/0**; users: `fraktal` → role `FraktalGateway` = exactly `WebReadTags|WebWriteTags`; `Anonymous` → `PLC administrator` | `09` |

A CAx (AML) export carries addresses and channels only — no security, UMAC or web
settings (`05`).

## 3. Downloads

| # | Choices | Result | Log |
|---|---|---|---|
| d1 | `um=reset`, protection **empty** | TIA asked "You are changing the CPU protection to a lower level"; the driver left `NoChange`; download **refused before anything was written** — the safe failure works | `10` |
| d2 | `um=reset`, `--accept-lower-protection` | **Success 0/0**: hardware (certificate configuration, user management) + all blocks; CPU restarted; online afterwards with **no** login prompt (anonymous access levels) | `11` |
| d3, d4 | `um=keep`, protection empty | **Success 0/0**; no protection question; user-management question reads "already exist" and keeps them | `20`, `22` |

## 4. S2 fixture on the ASCII image

| Run | Result |
|---|---|
| after d2 | **17/17 PASS** (`12_…`) |
| after d3 | **17/17 PASS** (`21_…`) |
| after d4 | **17/17 PASS** (`23_…`) |

Rows as in the first record (T1, T4, T2 + SourcePath, T3 HELD and resume, identity,
registry, mailbox SET_MODE/START/STOP/OPERATOR_RESET, chain trace, T6 rollup).

## 5. S1W — the Web API, measured

**Endpoint.** After d2: TCP **443 open, 80 closed** (HTTPS only, although Openness
offers no switch for it), 4840 closed (no OPC UA), 102 and the test port 2000 open.
TLS 1.2 `ECDHE-ECDSA-CHACHA20-POLY1305`. Served certificate: CN `PLC-1/Webserver-2`,
self-signed, SAN IP/DNS `192.168.0.10`, valid 2026-10-08 → 2037-10-07 — the project
certificate. (The template logged RSA/SHA-256 while the negotiated suite is ECDSA;
recorded as observed, not explained.) Pinned SHA-256 `5b7cbc6c…29581` on first
contact (`--trust-first`, `13`); **unchanged after d3 and d4**.

**Method set** (`Api.Browse`, `13`): `Api.Browse, ChangePassword, GetAuthenticationMode,
GetCertificateUrl, GetPasswordPolicy, GetPermissions, Login, Logout, Ping, Version,
PlcProgram.Browse, PlcProgram.Read, PlcProgram.Write, Syslog.Browse` — 14, `Api.Version`
**1.473**. `Api.GetQuantityStructures` is **not offered** (`-32601`), so session and
request budgets are not discoverable on this family.

**Authentication and rights** (`15`): `Api.GetPermissions` for `fraktal` =
`read_value, write_value` only. No token → `PlcProgram.Read` **refused, 2 Permission
denied**. A second `Api.Login` on a session that holds a token → **101 Already
Authenticated** (a client logs in once).

**Discovery** (`14`): `PlcProgram.Browse` walk of `"SpikeUnit"` — **126 leaves, 19
browse calls, 2.56 s**, both CM children included. **Private state is absent**: 0 leaves
from `Core`, `Seq`, `Auto`, the run/abort latches, `MbLastSeq`, `ModeActive`,
`ParentIndex` or the in/out HAL; reading `"SpikeUnit".Core.Exec` → **200 Address does not
exist**. Identity reads verbatim: `Status."Name"` = `SpikeUnit`, `CylB.Status."Name"` =
`SpikeUnit.CylB`.

**Types** (`14`, `15`): leaves are `bool, dint, dword, int, string, udint, uint, usint`.
A structure — including `DTL` — **cannot be read whole** (`204 Unsupported address`);
`DTL` browses as 8 members (`YEAR … NANOSECOND`) and reads member by member. The
CPU clock is **not set** (`Since.YEAR` = 2012; no NTP configured) — S12/§8.11 input.

**Write surface** (`15`): every module input, output and status leaf refused —
`CylA.Execute`, `CylA.Command`, `Status.State`, `HmiResponse.Accepted` → **205 Address
is read-only**; a hidden member → 200. A `HmiRequest` argument leaf → accepted and read
back. The member attributes the generator sets are the whole write gate, as designed
(Part IV §3.3, §3.10.1).

**Read cost** (`16`, `17`):

| Read | Median |
|---|---|
| `Api.Ping` (no PLC data) | 57 ms |
| 1 leaf (DInt, or String[80]) | 70 ms |
| 5 leaves, one batch | 127 ms |
| 10 leaves, one batch (simple or raw) | 205 ms |
| all 126 leaves, batches of 10 / 50 / 126 | 2.74 s / 2.21 s / **2.13 s** |

≈ **57 ms per request + ≈ 15 ms per leaf**, almost independent of batching beyond a
few leaves: the cost is per variable inside the CPU. A whole-tree poll at display
rate is therefore **not** possible on a 1214C; a fast tier of a few dozen leaves at
1–2 Hz with everything else on demand is — exactly the tiering the HMI already uses
(Part IV §3.10.3).

**Mailbox** (`18`, `19`): arguments written in one batch, `Sequence` alone in a
second request, then `AckSequence` polled:

| Request | Ack | Verdict |
|---|---|---|
| SET_MODE MANUAL | 146 ms | accepted; `Mode` → 1 |
| START while MANUAL | 140 ms | refused `std.release.notAuto` |
| kind 99 | 140 ms | refused `std.mailbox.unsupportedKind` |
| SET_MODE AUTO | 143 ms | accepted; `Mode` → 0 |

Sequences continued the harness's own (1006 … 1011); nothing was replayed.

## 6. Verdicts

- **S1W (Web API data path): PASS (functional, bench)** — browse, symbolic leaf
  reads, attribute-gated writes, authentication and pinning all behave as Part IV
  §11.1a requires; **narrowed on S7-1200 for throughput** (~15 ms/leaf, no structure
  reads, no quantity-structure query).
- **S9 mailbox leg over the Web API: PASS** (separate-request commit, acknowledgement
  by sequence, refusals with keys, no replay). Snapshot coherence, token expiry and
  reconnect are **not yet measured**.
- **S8 (web part): PASS for users/rights/HTTPS/pinning on the bench posture** —
  anonymous full access and the lowered protection level are **bench-only** and
  declared (Part IV §14).
- **S5/S2 on the ASCII image: PASS ×3.**
- **Openness gap (fails closed):** the S7-1200 web certificate type is one manual
  editor step per station project.

## 7. Still owed

Scan-time cost of Web API polling (S3); token expiry and re-login, CPU restart and
link-loss recovery, two concurrent clients (S9); the gateway's `WebApiSessionClient`
and the unchanged Web HMI rendering the spike Unit (S7); NTP/clock (S12);
`Syslog.Browse` as a diagnostics source; a deployed-posture run (full-access password,
no anonymous rights).

## 8. Later the same session — connections, concurrency and scan cost

Appended after §1–§7 were written; nothing above was changed. Logs `24`–`28`.

- **Name syntax** (`24`): quoting every segment works (`"SpikeUnit"."Status"."State"`),
  as does the unquoted form; arrays address as `"FRK_Registry".Rows[0].<member>`. The
  root browse lists every DB (six here); a non-root FB instance DB whose members are
  not accessible (`SpkMain`) browses as an empty list.
- **Idle connections are closed by the CPU** (`26`): a keep-alive HTTPS connection
  idle for 1 s survives, one idle for ≥ 2 s is reset (`ConnectionResetError 10054`).
  The **login token outlives the connection** — the same token works on a new
  TCP+TLS connection. With reconnect-and-resend on reset (pin re-verified on every
  connection) all idle gaps 1–12 s succeed (`27`). Resending is safe for reads, and
  for a mailbox write because the PLC acts only on a *changed* `Sequence`.
- **Concurrent sessions work** (`27`): two sessions alternating 40/40 reads.
- **The web server serves one request at a time across sessions** (`28`): while a
  second session read the whole Unit (126 leaves, 2.41 s per batch, 7 batches), the
  sampling session completed only 10 small reads in 20 s — each waited behind a large
  batch. Consequence for a gateway: one session per CPU, and **small batches** so a
  mailbox acknowledgement never queues behind a large snapshot.
- **Scan time** (`28`, from the PLC's own `FRK_Clock`): idle 447 scans/s (mean cycle
  2.24 ms, single-cycle median 2.30 ms, p95 2.57 ms); under continuous full-tree
  polling 406 scans/s (mean 2.47 ms, +0.23 ms ≈ +10 %), single-cycle samples unchanged
  (median 2.29 ms, max 2.40 ms) — the web server works between cycles. `MaxCycleMs`
  since start 8.9 ms (start-up). S3's polling-cost item: **measured on this image**.
- The first scan-load attempt (`25`) crashed its sampler on the idle reset and left
  its load thread polling; the process was stopped by PID and the script hardened
  (daemon thread, `finally`). Recorded as it happened.

## 9. Later the same session — the gateway's `WebApiSessionClient`, end to end

Appended; nothing above was changed. Logs `29`–`34`; fixture
`FraktalCore/HMI/test/fixtures/tia_webapi_spike_snapshot.json`. Toolchain: Flutter
3.47.6 / Dart 3.13.5 at `C:\Users\Siemens\Documents\FlutterSdk\flutter` (AGENTS.md
names 3.47.5 at another path; `pub get --enforce-lockfile` resolved unchanged and no
lockfile was rewritten).

- **Client** `packages/fraktal_opcua_client/lib/src/webapi_session_client.dart`, a
  third session client beside ADS and OPC UA, emitting `fraktal.opcua.snapshot.v1`;
  gateway transport `s7web://<host>` with `--plc-certificate` (pin) and
  `FRAKTAL_TIA_WEB_USER/PASSWORD`. Unit tests: 11 against a fake CPU reproducing the
  measured error codes (`test/webapi_session_client_test.dart`). `flutter analyze`
  clean; full HMI suite **563 passed, 7 skipped**.
- **First live run (`29`): correct but ~2.8 s per request** — 21 s per snapshot.
  Diagnosis (`30`): the CPU's **TLS handshake costs ≈ 2.75 s** (TCP connect 3–17 ms;
  Python measures the same 2.75 s per handshake, one 5.3 s), and `dart:io`
  `HttpClient` opened a **new connection for every request** (a new local port each
  time, with any header set), while the CPU keeps a connection open for a second
  request on the same raw TLS socket (59–62 ms). The Python tool had been fast only
  because it reused one connection.
- **Fix:** the transport is a minimal HTTP/1.1 client on ONE persistent pinned
  `SecureSocket`, requests serialized, `Api.Ping` keep-alive before the CPU's idle
  close, one resend on a dropped connection. **Second live run (`31`):** connect +
  login + discovery 4.7 s (126 leaves); snapshot 2.4 s (126 leaves, batches of 20);
  acknowledgement poll (3 leaves) 97 ms; mailbox `writeBatch` → acknowledged and
  accepted in 244 ms; a write to `Status/State` refused.
- **Through the gateway process** (`32`–`34`): `fraktal_gateway --plc-endpoint
  s7web://192.168.0.10 --plc-certificate … --write-root PLC1/SpikeUnit` connected and
  listened; over the `fraktal.opcua.gateway.v1` WebSocket: `discoverPaths` 126,
  `snapshot` 126 values (2.4 s), mailbox SET_MODE → acknowledged and accepted in
  227 / 230 ms; a batch that is not an `HmiRequest` commit refused by the gateway; the
  same `Sequence` again refused (`stage=write-refused reason=sequence`, no replay).
- **Unchanged mapper:** the captured snapshot maps to one Unit `SpikeUnit` with
  control-module children `SpikeUnit.CylA`, `SpikeUnit.CylB`, no discarded aliases
  (`test/tia_webapi_snapshot_mapper_test.dart`).
- **Not yet shown:** the Web HMI in a browser against this gateway (S7's visual
  half); the spike Unit also lacks contract members the HMI renders (e.g. command
  catalog, `ModeActivePublished`), which the generated Fraktal/TIA Unit will carry.

## 10. Later the same session — the unchanged Web HMI against the Siemens CPU (S7)

Appended; nothing above was changed. Screenshots `35`–`41`, gateway log `42`, driver
`cdp.mjs` (Chrome DevTools Protocol, headless Chrome, fresh profile).

- `flutter build web --release` (Flutter 3.47.6), served by the same gateway
  (`s7web://192.168.0.10`, `--web-root build/web`, `--write-root PLC1/SpikeUnit`) on
  127.0.0.1:8099; `/readyz` → `ready`, `plcReady: true`.
- The setup wizard ran unchanged: languages, appearance, access, then **the endpoint
  derived from the page origin** (`ws://127.0.0.1:8099/fraktal`, `36`) and **root-Unit
  selection listing `SpikeUnit`** discovered on the CPU (`37`).
- The operator shell came up (it appears only when the connection is LIVE): the
  navigation tree **SpikeUnit → CylA, CylB** and the station tile (`38`); CylA's
  detail shows identity `SpikeUnit.CylA` and state READY (`39`).
- **Command from the browser:** Start on SpikeUnit → Unit BUSY, CylA moving, the rail
  turns to Stop (`40`); Stop → READY, both cylinders idle (`41`). Cross-checked on the
  CPU through an independent Web API session: `HmiRequest.Sequence` = `AckSequence` =
  1011 (1009 was the last probe commit, so 1010 = START, 1011 = STOP), `Accepted`
  true, `Status.State` 0, `Busy` false; `Kind` reads 0 because the HMI resets it to
  `none` after every acknowledgement (`opcua_repository.dart`), a plain single-leaf
  write that also went through the `s7web` path.
- Sparse by design: the spike Unit publishes no command catalog, `ModeActivePublished`
  or description keys, so the station tile shows mode `-` and the detail shows "No
  module description configured" — the generated Fraktal/TIA Unit carries those.

**Verdict S7 (live tree reconstruction by the unchanged HMI through the gateway's Web
API session client): PASS (bench, spike scope).** Remaining for S9: token expiry
and re-login over a long session, CPU STOP/RUN and cable-pull recovery in the HMI.
