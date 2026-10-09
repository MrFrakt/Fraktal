# Fraktal/TIA — Siemens TIA Portal binding (working tree)

**Status: Phase 0.** The binding is
[`Specification/Fraktal_TIA_Part_IV.md`](../../../Specification/Fraktal_TIA_Part_IV.md);
the plan is [`Specification/Siemens/SIEMENS_PORT_PLAN.md`](../../../Specification/Siemens/SIEMENS_PORT_PLAN.md).
There is **no runtime library yet** — only the engineering driver, a read-only
bench probe and disposable spike fixtures. Do not describe anything here as a
conforming implementation.

What *is* proven (2026-10-08, [evidence](../../../Specification/Siemens/Evidence/TIA_S2_S15_FIRST_BENCH_RUN_2026-10-08.md)):
the S2 fixture builds headless through Openness, compiles 0 errors / 0 warnings
(software and hardware), downloads to the physical CPU 1214C, and its 17 self-test
assertions pass on three consecutive download-and-restart runs.

And since 2026-10-08 evening ([evidence](../../../Specification/Siemens/Evidence/TIA_S1W_WEBAPI_2026-10-08.md)):
the ASCII sources pass 17/17 on three more runs, and the CPU's licence-free **Web
API** is on — HTTPS with a pinned project certificate, one UMAC user `fraktal` with
read/write-process-data rights only. `tia_webapi.py` browses the spike Unit (126
leaves, private state absent), reads it, is refused every write except the mailbox,
and commits mailbox requests acknowledged in ≈ 140 ms. Throughput on the 1214C is
≈ 57 ms per request + 15 ms per leaf.

The gateway reaches it with `--plc-endpoint s7web://192.168.0.10 --plc-certificate
<pem>` (`WebApiSessionClient`, OPCUA_TRANSPORT "Siemens S7 Web API transport"), and
the **unchanged Web HMI** served by that gateway discovered, rendered and commanded
(Start/Stop) the spike Unit on 2026-10-08 (S7 PASS, spike scope; evidence §10).

Decisions that shape this tree: TIA Portal V20 only; sequences in **S7-GRAPH
(SFC) + SCL (ST)**, permissives in SCL, **no Ladder**; the press bench is ported
**without power control**; self-description through the CPU's licence-free **Web
API** (JSON-RPC over HTTPS) into the Fraktal gateway, the embedded OPC UA server only
as an optional licensed projection (Part IV §1). S7-1500 is the reference family;
the S7-1200 is a constrained family.

```
tools/
  TiaCli/                Fraktal.Tia.Cli — TIA Portal Openness V20 driver (C#, net48)
  s7_probe.py            read-only: identify a CPU (SZL), dump an SZL, harvest test results
  tia_webapi.py          Web API probe (S1W): pinned HTTPS, login, browse, snapshot, mailbox
  tia_lint.py            source gate (Part IV §5.3 T-rules) + test_tia_lint.py; pre-commit
  fraktal_tia_graph.py   S7-GRAPH writer (from a chain declaration + TIA's exported template),
                         reader (canonical dump) and SCL rendition parity + its tests
  Invoke-PlcSimInstance.ps1  S7-PLCSIM Advanced instance: host/status/run/stop, read-only tag read
  Enable-TiaOpenness.ps1 admin setup: Openness group, and whitelisting of a driver build
Spikes/
  S2_Shape/              module FB frame, FRK_Begin/FRK_End/FRK_Hold, CM ×2, Unit, mailbox,
                         SCL AUTO chain with parameter instances, self-test harness,
                         TCP result server; station/build/download/webapi plans for the bench
  S11_Graph/             the AUTO chain as GENERATED S7-GRAPH on a simulated S7-1500 (PLCSIM
                         Advanced): reference export, chain declaration, owner/rig, plans
```

## Bench

| Item | Value | Source |
|---|---|---|
| CPU | 1214C DC/DC/DC `6ES7 214-1AG40-0XB0`, FW **V4.7.3** | `s7_probe.py ident` (SZL 0x0011) |
| Address | 192.168.0.10; TIA PG/PC interface `Intel(R) 82574L Gigabit Network Connection` #2 (adapter `Ethernet1`, 192.168.0.123/24) | `interfaces --scan` |
| Station project | `%LOCALAPPDATA%\Fraktal\TiaStations\FrkSpikeS2\FrkSpikeS2.ap20` — holds the certificate the CPU trusts | see below |
| Running image | S2 test image (ASCII sources); serves its result table on TCP 2000 and the Web API on HTTPS 443 | |
| Security (bench only) | access control via access level, anonymous = full access (no password), lowered protection accepted on download; web user `fraktal` (password DPAPI-protected in `TiaStations\FrkSpikeS2.webapi.secret`) | Part IV §14 |
| Use | nothing connected; may be downloaded/stopped/reset for Fraktal work (owner, 2026-10-08) | |

The bench is S7-1200: **no S7-GRAPH, no `REF_TO`, no named value types, 150 KB
work memory.** GRAPH renditions are proved on S7-PLCSIM V20 (S7-1500) until an
S7-1500 exists.

## Engineering workstation prerequisites

1. TIA Portal V20 (STEP 7 Professional) with Openness V20 — installed.
2. **Account in the `Siemens TIA Openness` group**, then a new logon.
3. **Every driver build whitelisted** in the Openness firewall — it gates headless
   instances too, by the exe's hash; a rebuild fails with
   `EngineeringSecurityException: The operation has timed out` until approved.
   Both: `tools/Enable-TiaOpenness.ps1 -WhitelistExe <built exe>` in an elevated shell.
4. .NET SDK (any recent) to build the driver (net48 via the reference-assemblies
   package; no Developer Pack).
5. Python 3 for `s7_probe.py` and `tia_webapi.py` (standard library only).

## Build the driver

```powershell
dotnet build FraktalCore/PLC/Siemens/tools/TiaCli/TiaCli.csproj -c Release
# -> FraktalCore/PLC/Siemens/tools/TiaCli/bin/Release/net48/Fraktal.Tia.Cli.exe (gitignored)
# then whitelist that exact build (prerequisite 3)
```

## Run the S2 spike

```powershell
$st = "$env:LOCALAPPDATA\Fraktal\TiaStations"; $src = "<repo>\FraktalCore\PLC\Siemens\Spikes\S2_Shape"
$pc = 'pc=Intel(R) 82574L Gigabit Network Connection'
# 0. ONCE per target: station project (hardware, bench security posture, certificate)
Fraktal.Tia.Cli plan $src\station_1214c.plan --set work=$st
# 1. every build: delete program, import sources, compile 0/0, export (no controller access)
Fraktal.Tia.Cli plan $src\build_1214c.plan --set work=$st --set src=$src
# 2. CONTROLLER-CHANGING: download to 192.168.0.10 (needs current authorization)
Fraktal.Tia.Cli plan $src\download_1214c.plan --set work=$st --set $pc --set pcnum=2 --set um=keep --set protection=
#    (um and protection have no default: an unset one stops the plan before TIA starts)
# 3. ~40 s later: harvest the self-test rows from the test image's result server
python FraktalCore/PLC/Siemens/tools/s7_probe.py harvest --tcp 2000 --junit s2.xml
```

## Web API (S1W, licence-free self-description)

```powershell
# ONCE: web server on (HTTPS only), its certificate, the gateway's web user.
# The password is read from the environment only - never a plan, an argument or a log.
$env:FRAKTAL_TIA_WEB_PASSWORD = '<from the site secret store>'
Fraktal.Tia.Cli plan $src\webapi_1214c.plan --set work=$st
# then download_1214c.plan (CONTROLLER-CHANGING) carries it to the CPU
python FraktalCore/PLC/Siemens/tools/tia_webapi.py --trust-first probe   # pins the certificate once
python FraktalCore/PLC/Siemens/tools/tia_webapi.py tree --root SpikeUnit
python FraktalCore/PLC/Siemens/tools/tia_webapi.py snapshot --root SpikeUnit --repeat 10
python FraktalCore/PLC/Siemens/tools/tia_webapi.py mailbox --root SpikeUnit --kind 3 --int 1
```

**One manual step on S7-1200 V4.7:** Openness V20 cannot set the web server's
*certificate type* (neither getter nor setter). Set it once in the TIA editor —
PLC_1 > Properties > Web server > Security, "certificate loaded via the software" —
and save; the station project keeps it. Until then the hardware compile fails and
download refuses. The first download into the new posture needs `--set um=reset`
and `--set protection=--accept-lower-protection`; later ones `um=keep` and an empty
`protection=`.

The pin lives in `%LOCALAPPDATA%\Fraktal\TiaStations\<host>.webapi.pin`; a changed
certificate fails closed until someone deliberately re-pins it. `mailbox` writes the
arguments, then `Sequence` alone, and waits for `AckSequence`; it never replays.

Every driver run prints one JSON object per line — keep the log with the
evidence record. `download` refuses unless `--confirm-target` equals the CPU
address configured in the project, and answers security-relevant questions only
when an explicit flag says so.

**If the bench refuses to connect** ("Connect to module failed" / "Changing to
online mode failed"): the CPU holds a certificate from a project you are not using.
Use the station project. Recovering a CPU that holds a foreign certificate is a
deliberate, logged trust decision: add `--trust-plc PLC_1` to one `download`.

## Rules that already apply

- Sources are **ASCII** text (`.udt`, `.scl`, `.db`, GRAPH SimaticML) imported
  through Openness in **file-name order** — the numbered prefix is the dependency
  order. One `TYPE` per `.udt`, nothing before the keyword. TIA reads BOM-less files
  as ANSI. (The S2 sources are ASCII since 2026-10-08; the image running on the
  bench was built before that conversion, until the next build replaces it.)
- The TIA **program** is a build output; the TIA **project** is per-station
  engineering state (certificate) kept under `%LOCALAPPDATA%\Fraktal\TiaStations`.
  Never commit `*.ap20`.
- Contract members sit **directly on the module instance** (the HMI finds a module
  by its `Status` child). `Status` and the root `HmiRequest` are published statics;
  outputs are written, never read, by their own block. Private state carries
  `ExternalAccessible/ExternalVisible/ExternalWritable := 'False'`; only `HmiRequest`
  is `ExternalWritable`.
- Every module FB calls `FRK_Begin` first and `FRK_End` last, inside ONE generated
  quiescent guard (Part IV §3.14): an initialised, READY module with Execute/Abort low
  and nothing pending skips the lifecycle (≈ 0.20 → 0.053 ms per idle CM on the
  1214C, measured); identity setup and derived `OutImm` run outside the guard, every
  scan. Every child is called exactly once per scan by its owner.
- Identity comes from `#w := GetInstancePath(SIZE := 0);` at setup, never from a
  typed string. A member named `Name` is declared quoted (`"Name"`).
- An open interlock during a command is **HELD** (busy, outputs off, reason at LOW,
  self-resume), as in the TC3 reference — never a fault.
