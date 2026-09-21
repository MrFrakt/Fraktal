# Fraktal/AB — HMI gateway handover prompt

Copy the fenced text below into a new coding-agent chat opened at the cloned
repository root **on a PC that has the Flutter/Dart SDK**. Written 2026-09-21.

It does not supersede
[`AB_LICENSED_WORKSTATION_HANDOVER_PROMPT.md`](AB_LICENSED_WORKSTATION_HANDOVER_PROMPT.md);
that prompt still governs anything needing Studio 5000, the Logix Designer SDK
or the bench controller. This one covers the single remaining piece of the
gateway vertical — putting the generic Fraktal HMI in front of an Allen-Bradley
controller — which is blocked on this workstation only because no Dart SDK is
installed here.

## Why this is a separate host

| Needed | Where it is |
|---|---|
| Flutter/Dart SDK, to build and run the HMI | **the new PC** — absent on the bench workstation |
| Studio 5000 v33, Logix Designer SDK, licences | the bench workstation (`DESKTOP-07VCTIN`) |
| The bench controller `1769-L24ER-QB1B/A` on `192.168.100.0/24` | the bench |

The AB tooling is Python and speaks EtherNet/IP directly, so the gateway can run
either on the new PC (if it can reach `192.168.100.89`) or on the bench
workstation with the HMI pointed at it over the network. **Decide that first —
it determines the WebSocket host the HMI connects to.**

## Prerequisites on the new PC

* Flutter/Dart SDK matching `FraktalCore/HMI/pubspec.yaml` (`sdk: >=3.0.0 <4.0.0`).
* Python 3.10+, and a venv **outside the repository** carrying `pylogix==1.1.5`.
  The bench uses `C:\work\venv_s16`; recreate rather than copy.
* Network reachability to the controller, **or** to whichever host runs the
  gateway.
* No Rockwell licence is needed for anything in this prompt. Nothing here opens
  Studio.

---

```text
You are continuing the Fraktal/AB (Allen-Bradley Logix) implementation. The
objective is one thing: get the generic Fraktal HMI rendering a live
Allen-Bradley controller, and record what it does and does not show.

Everything below the HMI is already built, proved on hardware and pushed. Read
`Specification/Fraktal_AB_Part_III.md` and
`FraktalCore/PLC/Allen-Bradley/README.md` before touching this tree.

WHAT ALREADY EXISTS

* One committed Python declaration emits the whole application - contract UDTs,
  module AOIs, mode owner, routines and the full-project L5X. Hand-authored L5X
  and hand-authored ladder are forbidden; regenerate, never edit.
* The press demo publishes a controller-resident manifest (Core 3.10). It has
  been read off the bench controller: 22,112 bytes, ten CIP requests, ~91 ms at
  a 4002-byte connection, every published row equal to the declaration.
  Evidence: `AB_MANIFEST_CONTROLLER_READ_2026-09-08.md`.
* `FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_projection.py` already turns a
  live controller into the flat, transport-neutral snapshot document the HMI's
  own mapper consumes. It has run against the bench and discovered four modules
  with correct identities and parentage.

THE ONE MISSING PIECE

`lib/data/opcua_snapshot_mapper.dart` describes itself as mapping a
"transport-neutral flat OPC UA browse snapshot", and it finds a module wherever
a node publishes `Status/Name` and `Status/ModuleType`, building the tree from
the dotted identity. That is why no AB-specific screens and no AB repository are
needed. What is missing is a gateway that serves the projection over the
WebSocket protocol the HMI already speaks.

The protocol, taken from `lib/data/opcua_gateway_client_io.dart` and
`gateway/lib/src/fraktal_gateway_server.dart` - re-read both, do not trust this
summary alone:

  subprotocol   fraktal.opcua.gateway.v1
  request       {"id": <int>, "method": <string>, "params": {...},
                 "protocol": "fraktal.opcua.gateway.v1"}
  response      {"id": <int>, "ok": true, "result": <any>}
                {"id": <int>, "ok": false, "error": <string>}

  snapshot       params {} -> {values:{path:value}, dataValues:{...},
                               truncated:bool, nodeCount:int, paths?:[...]}
  discoverPaths  params {} -> {revision:int, paths:[string]}
  readValues     {revision, indices:[int]} -> {path: value}
                 (the client chunks indices in blocks of 512)
  setReadTiers   {revision, slow:[int], excluded:[int], refreshSlow:bool}
                 -> true
  write          REFUSE - see the read-only boundary below
  writeBatch     REFUSE

`indices` index into the array returned by `discoverPaths`, and the client
rejects a stale `revision`, so the gateway must hold that list stable and bump
the revision when it changes.

`fraktal_ab_projection.project()` already returns `values`, `dataValues`,
`truncated` and `nodeCount` in exactly the snapshot shape. The gateway is
mostly transport plus the path-index bookkeeping.

No WebSocket library is installed in the bench venv (it carries pylogix and
nothing else, deliberately). Choose and pin one, or serve the protocol from
Dart inside the existing gateway - either is defensible; say which you chose and
why in the evidence record.

THE READ-ONLY BOUNDARY, WHICH IS NOT NEGOTIABLE HERE

R6 passes for the declared read-only claim ONLY. AB 11.2.1: the gateway is
configured with no write root and refuses every operator command before the
controller sees it. So `write` and `writeBatch` must fail closed with a clear
reason, and the HMI must be seen to degrade gracefully rather than appear to
command a machine it cannot command. Enabling writes is not a code change you
may make on your own judgement - it rearms Core 14 in full (authenticated
principals, least-privilege roles, no anonymous write) and is a question for the
user, recorded in the binding record.

WHAT THE BINDING DOES NOT PUBLISH

The projection lists this in its `absent` field, with a reason for each entry,
because the mapper coerces a missing key into a default - a missing
`TileEnable` becomes true - so silence would render as data. Currently absent:
alarm logs, host events, access sessions, control power, OEE, nameplates,
recipes/models, and the I/O diagnostic fields (the press demo declares no
physical I/O, deliberately). Expect the HMI to show a plant with modules, modes,
states, step and counts, and to show nothing for those surfaces. That is the
honest result, not a bug to paper over: if a panel looks broken, decide whether
the projection should publish something real or the panel should handle absence,
and record which.

YOUR TASK

1. Decide where the gateway runs, given network reach to 192.168.100.89.
2. Build the gateway serving the five read methods above from
   `fraktal_ab_projection`, refusing the two write methods.
3. Run the real HMI against it. Record what renders - module tree, modes,
   states, steps, counts - and what does not.
4. Write a dated evidence record in
   `Specification/AllenBradley/Evidence/`, following the form of the existing
   ones. Include the gateway's resolved dependency versions, the controller
   identity and serial, and screenshots or a described walkthrough.
5. Update `Specification/Fraktal_AB_Part_III.md`, the AB README and
   `Specification/AllenBradley/AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md`.
6. Run the full test suite from a clean checkout. The AB gate
   (`fraktal_ab_phase0_gate.py`) needs Studio and will not run here - say so
   rather than recording a pass around it.
7. Commit in imperative style and push.

HOUSE RULES THAT HAVE TEETH HERE

* Past evidence is append-only. Add a dated record; do not rewrite one.
* A probe that cannot fail is not evidence. Every check gets a paired negative
  test. This has repeatedly caught real defects in this programme, including a
  comparison that silently passed when a table read back empty.
* Acceptance is not publication, and silence is not parity. The manifest once
  imported with zero errors and stored none of its 208 strings; it was found by
  reading the project back, not by trusting the import.
* Enum ordinals are the PLC contract. `test_fraktal_ab_core_ordinals.py` reads
  the TwinCAT DUTs directly and asserts the AB binding matches - it exists
  because AB had AUTO and MANUAL swapped against Core `E_Mode`, which would have
  made an operator screen render MANUAL as AUTO. If you add a mapping, pin it
  the same way.
* Never perform a controller-changing operation - download, mode change, tag
  write, fault clear, clock set, firmware, network configuration - without
  current explicit authorization and an exact target check immediately before
  use. Prior authorization is historical and shall not be inferred. Reading is
  fine; this whole task should need no write at all.
* If something cannot be proved here, record the narrowing honestly and say
  what would prove it. Do not mark a gate PASS around a gap.
```

## Bench state at handover

| Item | Value |
|---|---|
| Controller | `1769-L24ER-QB1B/A LOGIX5324ER`, firmware `33.014`, serial `7036B510` |
| Address | `192.168.100.89:44818`; bench host adapter `Ethernet1` `192.168.100.123/24` |
| USB | Rockwell Automation USB CIP Device present; Studio route `Backplane\16` |
| Loaded program | **as written, the press demo built before the mode-ordinal correction.** The corrected build `press_modes.ACD` (`E8FC0B77D1F390F56CD634ACFFAE2CF79558976FB8BA3DF32328BBF23943589C`, SDK import 0/0, Studio v33 Verify 0/0) was ready but not yet downloaded |
| Rollback ACD | recorded in the tool catalog, outside the repository, not executed |

**Check which build is actually loaded before trusting `Mode`.** The manifest
content is identical across the two builds, so a gateway sees the same station
either way and the ContentHash cannot tell them apart. Only the meaning of
`Mode` differs: the corrected build follows Core `E_Mode` (`AUTO := 0,
MANUAL := 1, HOME := 2`), the earlier one had AUTO and MANUAL swapped. If a
later evidence record in `Specification/AllenBradley/Evidence/` records the
download of `press_modes.ACD`, the corrected build is on; if none does, assume
it is not and confirm with the bench operator before reading anything into a
mode value.
