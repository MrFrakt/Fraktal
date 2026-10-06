# Fraktal/AB — a browser commanded the controller, and the machine moved

**Result:** **the generic Web HMI changed the press mode from a browser, over an
authenticated origin, and the controller state confirms it.** `AUTO` to `MANUAL`
was issued by a click in Chrome, travelled origin to proxy to gateway to CIP,
and `ModeActivePublished` read back `1` — `E_Mode.MANUAL` — off the live unit
context. This is the first Fraktal/AB command from a browser rather than from a
harness.

**Date:** 2026-09-24

**Repository revision:** `ca8efeb`. The loaded build is unchanged from
`AB_WRITE_SURFACE_CLOSED_2026-09-23.md` — `ContentHash 71448732E842290F` /
`ConfigRevision 7423111` — and **no download was performed**. The manifest read
back off the controller agrees with source on all eight tables.

**Target:** `1769-L24ER-QB1B/A LOGIX5324ER`, serial `7036B510`, `192.168.100.89`,
firmware `33.014`. Serial checked immediately before use by every tool that
connected, including the read-only manifest reader.

**Scope:** the mode change was issued **by the operator in the browser**, not by
the agent. The agent's own controller traffic in this session was read-only:
snapshot reads through the gateway and one `fraktal_ab_manifest_read.py` run,
which has no write path in it. No download, keyswitch change, fault clear, clock
set, firmware, controller-network, safety or SD-card operation.

## 1. Why a proxy exists at all

The gateway requires a bearer token before a write path exists. **A browser
cannot set an `Authorization` header on a WebSocket** — the API has no facility
for it — and the Web HMI has no token field, deliberately. So the two cannot be
introduced to each other directly.

A reverse proxy reconciles them without either side bending:

```
Chrome  --https/wss-->  Caddy  --ws + Bearer-->  gateway  --CIP-->  controller
        basic_auth             header_up                  loopback
```

Caddy authenticates the operator with `basic_auth` — that is the Core §14
authenticated principal, and it is what makes the write non-anonymous — then
presents upstream the bearer the browser could not send. **Nothing in the
gateway, the protocol or the PLC changed to allow this.** The HMI needed no
endpoint typed in either: a release Web build derives `wss://<page-origin>/fraktal`
from `Uri.base`, so serving the HMI and the gateway on one origin is the whole
configuration.

Bench components: Caddy `v2.11.4` (SHA-512 verified against the published
checksum), Chrome `153.0.0.0`, gateway bound to `127.0.0.1:8099` with
`--write-token` and `--allow-origin https://press.localhost`. Credentials are
bench-local and are not recorded here.

## 2. The handshake, proved rather than assumed

Whether Chrome would attach its cached `basic_auth` credentials to a **WebSocket**
handshake was the one genuinely unknown step — browsers are not obliged to, and
the HMI reports any failure as the same opaque "could not open the gateway".
Access logging was enabled specifically so this could be read instead of guessed.

Chrome's handshake, from the Caddy access log:

```
GET /fraktal   host press.localhost   Upgrade: websocket
Authorization  REDACTED           <- Chrome sent the cached credentials
user_id        operator           <- basic_auth resolved a principal
status         101                <- upgraded, not refused
```

and the same connection arriving at the gateway:

```
stage=connected peer=('127.0.0.1', ...) authenticated=True
stage=identity-verified serial=7036B510 target=192.168.100.89
```

`authenticated=True` is the proof that `header_up` replaced the browser's Basic
credential with the Bearer — the gateway never sees, and never needs, the
operator password.

**This is observed Chrome behaviour, not a guarantee.** Another browser may
decline to attach cached credentials to a WebSocket upgrade, in which case this
posture needs a cookie or token exchange rather than `basic_auth`. Only Chrome
`153` was exercised.

## 3. The command, proved by machine state

Per `AB_WRITE_SURFACE_CLOSED_2026-09-23.md`, an acknowledgement is not proof. The
mailbox wrote its ten members and then `Kind`, in the required order, and
acknowledged:

```
FRK_Press_HmiRequest.Sequence   165
FRK_Press_HmiResponse.AckSequence  165
FRK_Press_HmiResponse.Accepted     True
FRK_Press_HmiResponse.Diagnostic   (empty)
```

The state that settles it is read from the live unit context, not from the ack:

| published node | value | meaning |
|---|---|---|
| `Press/ModeActivePublished` | `1` | `E_Mode.MANUAL` — the mode changed |
| `Press/Status/State` | `0` | READY |
| `Press/Status/FaultActive` | `False` | no fault raised by the change |
| `Press/GoodCount` / `NokCount` | `3` / `3` | earlier cycles, undisturbed |

`ModeActivePublished` is `unit["Mode"]` — a member of the context read off the
controller each poll — so it is machine state, not an echo of the request.

`Press/Status/Diagnostic/ReasonCode` reads `6102` (`DEVICE_FAULT`) from an
earlier run. It is the latched `ReportedReason` and not a live condition:
`FaultActive` is `False` and `State` is READY beside it.

## 4. The mode list, and where it comes from

The HMI offers `AUTO`, `MANUAL`, `HOME` — `SupportedModesPublished[1..3]`,
ordinals 0/1/2. `CHANGEOVER` is absent because the AB press application declares
no `CHANGEOVER` chain; that is correct, not a regression.

Worth stating plainly, because it is easy to misread as controller state:
**`SupportedModesPublished` and `ModePolicy` are projected by the gateway from
the committed declaration**, not read from the controller. Only
`ModeActivePublished` is live. That is the intended shape — the declaration is
the source for what the station *can* do, the controller for what it *is* doing
— but a future reader checking the mode list against tags will not find it there.

## 5. What this does not prove

- **This is a bench proxy, not the shipped installer.** The packaged Windows path
  (`build_gateway.dart`, `WEB_HMI_GATEWAY_DEPLOYMENT.md`) deploys Caddy with
  generated per-instance routing. This run configured Caddy by hand outside the
  repository to prove the protocol path; the installer path is unexercised for AB.
- **Loopback only.** `tls internal` issued a local CA trusted for the installing
  Windows user. No remote browser device was tested, and local trust never
  propagates — a remote device must trust the exported root or site PKI.
- **One browser, one session.** No reconnect, link-loss or concurrent-client
  behaviour was exercised over the proxy.
- **Read-only remains the shipped AB posture.** The write path was armed
  deliberately for this run. AB §11.2.1 requires the read-only/write-enabled
  answer to be asked per project and recorded in the binding record; arming a
  gateway is a configuration change needing no download, and it arms Core §14 in
  full.
