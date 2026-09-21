# Fraktal/AB — the generic HMI in front of a live controller

**Spike:** the HMI gateway — the last piece of the gateway vertical.

**Result:** **The unmodified generic Fraktal HMI renders a live Allen-Bradley
controller through a read-only gateway, over the same production code path the
desktop app uses.** The operator sees the press as a Unit with its three control
modules, its mode, states, step and counts; the surfaces the binding does not
publish appear as nothing, save two the mapper synthesizes into defaults, which
are recorded below for a decision. Writes are refused fail-closed before the
controller. This closes the forward pointer left in
[`AB_MANIFEST_CONTROLLER_READ_2026-09-08.md`](AB_MANIFEST_CONTROLLER_READ_2026-09-08.md):
"the gateway that will consume this … is not written; this record only proves
the surface it will read is real."

**Date:** 2026-09-21

**Repository revision:** `4203407`, plus this change (the gateway, its tests, a
projection refactor that extracts the shared live-read, and a live HMI test).

**Scope:** read-only. **No write of any kind was issued** — no tag write, mode
change, fault clear, clock set, firmware, controller-network or SD operation.
The gateway is configured with no write root and refuses `write`/`writeBatch`
before the controller sees them (AB §11.2.1); the projection and the reader it
shares have no write path in them.

## 1. Where the gateway runs

One host both reaches the controller (`192.168.100.89:44818` open) and runs the
HMI (Flutter present), so the gateway runs there, on the loopback, and the HMI
connects to it over the loopback. That settles the handover's first question:
the WebSocket host is `127.0.0.1`. A remote browser would reach it only through
a same-host TLS reverse proxy that owns authentication — the gateway binds
loopback only and refuses to bind anything else, like the reference server.

## 2. The gateway, and why it is Python

`FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_gateway.py`. It wraps
`fraktal_ab_projection` in the `fraktal.opcua.gateway.v1` WebSocket protocol the
HMI already speaks, so no AB-specific screen or repository is needed.

Serving the protocol from Python, not from the existing Dart gateway, was the
choice because the Dart gateway in `FraktalCore/HMI/gateway` is ADS/TwinCAT-
specific (every probe is `probe_ads_*`), while the AB tooling is already Python
that speaks EtherNet/IP through pylogix. A Python transport reuses the proven
projection read directly; bending the Dart gateway to CIP would have duplicated
the read path in a second language. The transport is thin: the projection
already returns `values`, `dataValues`, `truncated` and `nodeCount` in exactly
the snapshot shape, so the gateway adds only the path-index bookkeeping and the
health/origin/revision discipline it mirrors from the reference server.

Resolved dependencies, in a venv **outside** the repository (`C:\work\venv_abhmi`),
pinned in `tools/requirements-gateway.txt`:

```
python      3.11.13
pylogix     1.1.5     (the phase-0 gate's pin; EtherNet/IP to the controller)
websockets  17.1      (asyncio WebSocket server for the HMI protocol)
```

The read is shared, not duplicated: `main()` in `fraktal_ab_projection.py` and
the gateway both call the extracted `read_document()`, so the live-read sequence
has one source. The controller identity is checked when the connection opens
(serial pinned to `7036B510`), and `project()` re-validates the manifest content
hash on **every** poll — a foreign or moved manifest fails the whole projection
closed rather than rendering part of a plant. One pylogix connection is reused
and reconnected transparently once on a stale socket, so an idle period does not
surface a spurious error to the HMI.

## 3. The controller, checked before it was trusted

```
product name  1769-L24ER-QB1B/A LOGIX5324ER
revision      33.014
serial        7036B510          serial_matches: true
address       192.168.100.89:44818
manifest      ContentHash 42334AD69FD1A3AB   ConfigRevision 4338506   Truncated 0
```

## 4. What the HMI renders

Proved through the **production code path**, not a mock:
`ConnectionSettings(ws://127.0.0.1:8080/fraktal)` →
`createExternalRepository` → `IoGatewayOpcUaClient` → `OpcUaRepository` →
`forest()` — the exact chain the desktop app runs. The test is
`FraktalCore/HMI/test/live_ab_gateway_test.dart` (tagged `live`, so it is skipped
in the offline suite and run explicitly against a running gateway).

The module tree the operator sees:

```
- Press            type=unit           state=ready  mode=auto  good=0 nok=0 step=-
  - Press.Door       type=controlModule  state=ready  fault=false
  - Press.PartSlide  type=controlModule  state=ready  fault=false
  - Press.PressRam   type=controlModule  state=ready  fault=false
```

Four modules, correct identities and parentage: the press is the root Unit, the
three control modules are its children, built from the dotted identity by the
unchanged transport-neutral mapper. The Unit publishes its mode, its
good/scrap counts and its current step; each control module publishes its
execution state and fault. The `contentHash` on the snapshot equals the
declaration, `truncated` is false, and the discovery revision is stable at 1
across snapshot, discovery and targeted reads.

## 5. What it does not show — and two surfaces that render as data

Most of what the projection lists in `absent` renders as genuine nothing, which
is the honest result:

```
commands=0  availableModels=[]  activeEvents=0  ringEvents=0  hostEvents=0
oee=null  nameplate=null  cycle=null  controlPower=null
Press.Door/PartSlide/PressRam: ioTag="" ioAddress="" commands=0
```

**Two surfaces the mapper coerces into defaults rather than leaving blank — the
"silence renders as data" caveat, now measured:**

1. **Supported modes.** The projection publishes `ModeActivePublished` (the
   active mode) but not the §3.7 `_M_Supports` set. The mapper falls back to
   offering only the active mode, so the mode picker shows `[auto]` — the current
   mode alone, not the controller's real AUTO/MANUAL/HOME set.
2. **Access.** The mapper always builds an `AccessSession`, so a binding that
   publishes no `Access/*` still renders a default **logged-out** session
   (`level=none`, empty user), not a blank panel.

Neither is a bug to paper over, and neither is changed here: whether the
projection should publish `_M_Supports` and an access surface, or the panels
should treat their absence as absence, is a scope decision for the user, so it
is recorded, not silently patched. Because writes are refused, the mode picker
cannot switch anything regardless.

## 6. The negative tests

A probe that cannot fail is not evidence. Each check is paired with the fault it
must catch, live against the controller and offline in unit tests.

* **A remote Origin is refused at the handshake.** A client presenting
  `Origin: http://192.168.100.50:8080` is refused with **HTTP 403**; a loopback
  Origin is upgraded. (`test_fraktal_ab_gateway.py` pairs the loopback accept
  with remote/`null`/bad-scheme/path rejects.)
* **Writes are refused fail-closed.** `write` and `writeBatch` return
  `{ok:false}` with `read-only Allen-Bradley gateway (AB §11.2.1): configured
  with no write root; operator commands are refused before the controller sees
  them`. The HMI receives the refusal as a remote error and degrades; it does
  not appear to command the machine. The paired positive: the same gateway
  serves every read method.
* **A stale discovery revision is refused.** `readValues` with a revision the
  gateway does not hold returns `Discovery revision is stale; discover paths
  again.`, so the client re-discovers rather than reading against a shifted path
  list. Empty and out-of-range index lists are refused likewise.
* **The serial guard refuses.** The reader verifies the controller serial before
  it trusts a manifest; aimed at the wrong serial it refuses and reads no
  manifest. `test_fraktal_ab_projection.py` proves the projection refuses an
  invalid, truncated, foreign or hash-disagreeing manifest, reporting which
  check failed.

R6 passes here **for the read-only claim only.** Enabling writes is not a change
to make on judgement — it rearms Core §14 in full (authenticated principals,
least-privilege roles, no anonymous write) and is a question for the user,
recorded in the binding record.

## 7. The mode value is not yet safe to read into

The live read returned `ModeActivePublished = 0`, which is AUTO under the
corrected Core `E_Mode` (`AUTO := 0, MANUAL := 1, HOME := 2`). **But the loaded
bench build may pre-date the mode-ordinal correction, in which case AUTO and
MANUAL were swapped.** The manifest content is identical across the two builds,
so the ContentHash cannot tell them apart, and no evidence record in this folder
records a download of `press_modes.ACD`. So this record does **not** conclude the
press is in AUTO; the ordinal is reported verbatim, and the meaning must be
confirmed with the bench operator before it is read into an operator screen.

## 8. Tests

Run from this checkout with the gateway venv and Flutter on the path.

* **AB Python tools:** `python -m unittest discover` over
  `FraktalCore/PLC/Allen-Bradley/tools` — **493 tests, OK**, including the 25 new
  gateway tests and the 30 projection tests (the projection refactor is
  behaviour-preserving). The `usage:` lines in that run are the tools' own
  paired-negative tests asserting their CLIs reject bad arguments.
* **HMI analyze:** `flutter analyze` — no issues.
* **Live HMI path:** `flutter test --run-skipped -t live
  test/live_ab_gateway_test.dart` — passes against a running gateway (§4–§5).
* **HMI offline suite:** `flutter test` is green **except two tests**
  (`cycle_gantt_test.dart §8.11.4(c)` and `opcua_snapshot_mapper_test.dart`
  "hydrates live alarms…"). These fail on a **clean HEAD worktree with none of
  this change's files**, so they are not caused by this work: the local
  toolchain is Flutter **3.44.5**, CI pins **3.44.6**, and both failures track
  that delta (a `Color.colorSpace` framework addition and an alarm-meta count).
  Recorded honestly rather than worked around; the fix is to run the suite on
  the pinned Flutter.
* **Other repository gates (unchanged by this work):** `check_ab_contracts.py`
  clean; `check_consistency.py --strict` 0 errors, 0 warnings; TwinCAT
  `plc_lint.py --profile modern` 360 files clean; the TwinCAT gate-tool suite 75
  OK. `check_ab_spec.py` reports **3 errors** and its unit test
  (`tools.test_check_ab_spec`) has **1 failure**, both in the readiness table
  (R0–R5 all PASS) and the §12 register (S16 present, S15 not OPEN). These also
  reproduce on a clean HEAD worktree — the gate's hardcoded expectations
  (R0–R3 PASS / R4–R6 OPEN, S1–S15) are stale against the synced spec, not
  broken by this change, which adds no readiness row and no spike. Reconciling
  the gate with the advanced spec is a separate task and is left to the user.
* **AB Phase-0 gate:** `fraktal_ab_phase0_gate.py` needs Studio 5000 and the
  Logix Designer SDK, which are on the bench workstation, not here. It was **not
  run**, and is not recorded as a pass.

## 9. How to run the GUI (operator step)

The data path above is the substance and is proved headlessly. The visual
walkthrough is an operator step on a host with the desktop toolchain:

```
# 1) gateway (venv with pylogix + websockets):
python fraktal_ab_gateway.py 192.168.100.89 --expect-serial 7036B510
# 2) HMI:
flutter run -d windows
#    wizard → transport: gateway, endpoint: ws://127.0.0.1:8080/fraktal
#    → select the "Press" unit → the plant screen shows the tree from §4.
```

The gateway also answers `/healthz`, `/livez` and `/readyz` (200 JSON;
`/readyz` is 503 until the first controller read succeeds), so an operator can
confirm it is live and talking to the controller before opening the HMI.

## 10. What this settles and does not

Settled: the generic Fraktal HMI renders a live Allen-Bradley controller
read-only, through a gateway that reuses the proven projection; writes are
refused before the controller; and everything the binding does not publish is
named, not fabricated.

Not settled, and still owed: writes (a Core §14 decision, not taken here); the
event core, release/access enforcement, recipes/models, OEE, nameplates and
physical-I/O diagnostics; the two synthesized-default surfaces in §5; and the
meaning of the live mode value until the loaded build is confirmed.
