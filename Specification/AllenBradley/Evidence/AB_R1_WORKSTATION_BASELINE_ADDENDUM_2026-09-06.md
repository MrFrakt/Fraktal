# Fraktal/AB R1 — workstation baseline addendum (engineering PC, 2026-09-06)

**Gate:** R1 platform baseline — dated addendum for a **new** workstation

**Result:** **BLOCKED — this workstation does not supply the Logix Designer SDK
licence, and it cannot reach the v33 bench controller with any installed
engineering tool**

**Date:** 2026-09-06

**Repository revision at start:**
`6989e09f7be17c218283bc47139baa8a98c85d75`

**Scope:** read-only workstation discovery and one fixed-vector read-only
EtherNet/IP identity probe against the user-authorized isolated controller. No
download, controller-mode change, tag write, fault clear, clock set, firmware
operation, network configuration, safety operation or SD-card operation
occurred. No activation identifier, credential, licence key or controller key
is recorded here.

## 1. Why this record exists

R1 records PASS for the *previous* workstation
([`AB_R1_PLATFORM_BASELINE_EVIDENCE.md`](AB_R1_PLATFORM_BASELINE_EVIDENCE.md)).
Evidence produced on a different machine is not citable until that machine has
its own dated baseline. This addendum is that record.

The session premise was that this PC removes the Logix Designer SDK licence
blocker recorded on 2026-08-26 in
[`AB_S12_V38_PREFLIGHT_BLOCKER_2026-08-26.md`](AB_S12_V38_PREFLIGHT_BLOCKER_2026-08-26.md).
**Measured read-only, that premise does not hold.** The blocker is not removed,
and two further blockers that the previous workstation did not have are added.

## 2. Operating system and runtimes

| Item | Observed value | Source |
|---|---|---|
| Operating system | Windows 11 Pro, version `10.0.22631`, build `22631`, 64-bit | `Win32_OperatingSystem` |
| Machine name | intentionally omitted from the repository | — |
| Python | CPython `3.14.7` at `C:\Python314\python.exe` | `python --version` |
| Git | `2.55.0.windows.5` | `git --version` |
| .NET SDK | **none installed** — `dotnet --version` reports `No .NET SDKs were found` | `dotnet --version`, `dotnet --list-sdks` |

## 3. Studio 5000 Logix Designer

| Item | Observed value | SHA-256 of `LogixDesigner.exe` |
|---|---|---|
| Studio 5000 Logix Designer v37.00.00 (CPR 9 SR 15) | `V37.00.00` | `74C71849A9D594D01B84A3B9079B95E6E2CCE80129F55AF1C189B404384A6D0A` |
| Studio 5000 Logix Designer v38.00.00 (CPR 9 SR 16) | `V38.00.00` | `FA02C3DA1ED3777B779A28CA7BF84AFB3BD7EFBFB0795AE170F7374815EEB217` |
| Studio 5000 Launcher | `3.8.17.0` | — |
| Legacy RSLogix 5000 | `ENU\v13`–`v20` present | — |

**Installed Logix Designer major revisions are exactly `37` and `38`.**
There is **no Studio 5000 v33** on this workstation. The previous workstation
carried `21, 23, 24, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37`.

## 4. Logix Designer SDK

| Item | Observed value | SHA-256 |
|---|---|---|
| Registered product | `Logix Designer SDK` `2.01.00` | — |
| SDK server binary | `LdSdkServer.exe`, FileVersion `2.1.974.0`, ProductVersion `2.01.974.x` | `B0FFEDF6E749783EBF564040C6F5B7767D5DAFD1D11D58101FC18EE48273CBC1` |
| Windows service | `LdSdkService`, `Running` / `Automatic` | — |
| C# client package present | `RockwellAutomation.LogixDesigner.CSClient.2.1.974.nupkg` | — |

The repository probe
[`Fraktal.Ab.OfflineProbe.csproj`](../../../FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/Fraktal.Ab.OfflineProbe.csproj)
pins `RockwellAutomation.LogixDesigner.CSClient` **`2.2.1109`** (SDK 2.02), which
is the version the previous workstation carried and which commit `6989e09`
updated the probe to. That package is **not present** on this machine, and the
installed SDK server is the older `2.01.974`.

## 5. Activation state — the SDK licence question

The mission's recorded proof of an issued `LDSDK.EXE` feature is a harmless
offline ACD open/export through `Fraktal.Ab.OfflineProbe`. **That proof could
not be attempted on this workstation**, because no .NET SDK is installed, so
the probe cannot be built (§2). Independently of that, read-only inspection of
the local FactoryTalk Activation state shows no entitlement that would issue it:

- FactoryTalk Activation `5.02.00.0052` is installed; `FactoryTalk Activation
  Service` and `FTActivationBoost` are `Running`.
- The FlexNet vendor daemon reads only local licence files. **No activation
  server is configured** (no `ftaservers.txt`) and the referenced dongle
  directory is **empty**.
- The licence files present carry `fta.system` plus a single legacy
  disk-serial-locked set dated **2009**, whose features are all pre-Logix-5000
  era products (RSView/RSLogix 500/`rs5000.exe`/`RSLINX.EXE` and similar). The
  host-lock identifier and all key material are deliberately not recorded here.
- **No `LDSDK.EXE` feature exists in any local licence file.** Neither does any
  Studio 5000 v37/v38 feature, nor any FactoryTalk Logix Echo feature.
- The activation daemon log for the current session contains only
  `UNSUPPORTED ... No such feature exists. (-5,346)` entries.

**Conclusion: the Logix Designer SDK licence blocker recorded on 2026-08-26 is
not removed by this workstation.** Whether Studio v37/v38 themselves would open
in a licensed state was not exercised — no Studio process was started, and this
record does not claim one.

## 6. FactoryTalk Linx and Logix Echo

| Item | Observed value |
|---|---|
| FactoryTalk Linx | `6.60.00` (CPR 9 SR 16); `RSLinxNG` services `Running` |
| RSLinx Classic | `4.50.00` (CPR 9 SR 15) |
| FactoryTalk Logix Echo | `4.00.3672` **installed**, with Echo SDK .NET and Echo SDK Python `4.00.3672` and Echo Dashboard `4.00.1811` |
| Echo controller catalogue | ControlLogix 5580 `33/34/35/36/37/38.11.00`; ControlLogix 5590 `38.11.00`; CompactLogix 5380 `36/37/38.11.00`; Compact GuardLogix 5380 `36/37/38.11.00`; GuardLogix 5580 `35/36/37/38.11.00` |
| Echo services | `FactoryTalk Logix Echo Message Broker` `Running`; **`FactoryTalk Logix Echo Service` `Stopped`** despite `Automatic` start |
| RSLogix Emulate 5000 | installed (`EmuLogix 5868 Slot0`–`Slot16`, all `Stopped`) — **not** Echo, and not a permitted substitute |

Echo is the first Echo installation seen on any Fraktal/AB workstation; the tool
catalog §10 still records it as *Not installed*, which this addendum supersedes
for this machine only.

**Echo's usability is UNDETERMINED, not disproved.** Its service is stopped, and
starting it failed with `Cannot open ... service on computer '.'` — an
elevation/permission refusal in this session, not a licence verdict. No Echo
activation feature was found in the local FlexNet set (§5), so the likely cause
is entitlement, but that is inference and is **not** recorded as a measurement.

## 7. Network and controller identity

Host IPv4 addresses: `Ethernet1` carries `192.168.0.100`–`192.168.0.103/24`;
`Ethernet0` carries `192.168.101.129/24`; a `FactoryTalk Optix VPN` adapter
carries `169.254.107.17/16`. **No adapter holds a `192.168.100.0/24` address**,
unlike the previous workstation's `192.168.100.99/24`.

The bench controller nevertheless answers at `192.168.100.89` (ICMP 4 ms/2 ms).
The fixed-vector read-only probe
[`fraktal_ab_eip_probe.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_eip_probe.py)
was run with its serial guard:

```
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_eip_probe.py 192.168.100.89 --expect-serial 7036B510
```

| Field | Value |
|---|---|
| `product_name` | `1769-L24ER-QB1B/A LOGIX5324ER` |
| `revision` | `33.014` |
| `serial_number` | `7036B510` |
| `serial_matches` | `true` |
| `state` / `device_status` | `3` / `48` |
| `socket_address` / `port` | `192.168.100.89` / `44818` |
| `interface_configuration.address` | `192.168.100.89`, mask `255.255.255.0`, gateway `0.0.0.0` |
| `time_sync.ptp_enabled` / `is_synchronized` | `false` / `false` |
| identity latency (5 samples) | min `16.833` ms, median `19.607` ms, max `69.413` ms |

The target identity is **exactly** the documented bench controller, and it is
reachable over Ethernet from this workstation. That answers, positively, one
open S15 scope question: EtherNet/IP reachability from the engineering host is
not the obstacle here.

## 8. What this workstation blocks

1. **Every v33 online leg, including any download.** The bench controller is
   firmware `33.014`. Logix Designer goes online with a controller only through
   its matching major revision, and this machine has only v37 and v38. Neither
   USB nor Ethernet changes that — it is a missing-tool fact, not a route fact.
   Ethernet reachability (§7) does not substitute for the absent v33 editor.
2. **The S15/R4 SDK automation backbone.** With no .NET SDK, the offline probe
   cannot be built, so `fraktal_ab_phase0_gate.py` stage 1 cannot run here at
   all — a different and earlier failure than 2026-08-26's `No valid license`.
3. **The v38 S12 acceptance rerun**, additionally and independently of §5 — see §9.
4. **R5 through Echo**, pending the elevation and entitlement questions in §6.

## 9. Missing prerequisite record

The acceptance rerun this session was asked to execute is defined by section 7
of `AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md`. **That file does not exist in
this repository.** It is absent from the working tree, absent from all of
`git log --all` across every path, and referenced by no tracked file. The only
v38 record present is the 2026-08-26 preflight blocker. Part III §12 contains no
v38 row, and the AB tool suite reports **156** tests where the session premise
expected 162+.

Per the standing rule that evidence records are append-only and history is never
regenerated, the rerun was **not** attempted and no substitute acceptance
criteria were invented.

## 10. Repository gates run on this workstation

All STEP 0 gates were run from the repository root at `6989e09` and are green:

| Gate | Result |
|---|---|
| `python -m unittest discover -s FraktalCore/PLC/Allen-Bradley/tools -t FraktalCore/PLC/Allen-Bradley/tools` | `Ran 156 tests` — `OK` |
| `python tools/check_ab_contracts.py` | `Fraktal/AB frozen-contract gate: clean.` |
| `python FraktalCore/PLC/TwinCAT/tools/plc_lint.py` | `360 file(s) clean (profile: modern)` |
| `python FraktalCore/PLC/TwinCAT/tools/plc_lint.py --profile 4024` | `360 file(s) clean (profile: 4024)` |
| `python tools/check_consistency.py inventory localization parity` | `0 error(s), 0 warning(s)` |
| `python -m unittest tools.test_check_consistency` | `Ran 15 tests` — `OK` |
| `git -c core.whitespace=cr-at-eol diff --check` | clean |

The repository itself is therefore healthy on this machine; what is missing is
Rockwell tooling and entitlement, not repository state.

## 11. What would unblock which leg

| Leg | Exact missing fact |
|---|---|
| Any v33 online work or download | **Studio 5000 Logix Designer v33** installed and licensed on this workstation |
| SDK build/automation (S15, R4) | a **.NET SDK** able to target the installed client's 32-bit architecture, **and** an issued `LDSDK.EXE` activation |
| SDK client/version coherence | either client `2.1.974` pinned for this machine, or SDK **2.02** installed to match the repository's `2.2.1109` pin |
| v38 S12 acceptance rerun | the **`AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md`** record supplying section 7's six steps |
| R5 through Echo | an elevated session to start `FactoryTalk Logix Echo Service`, **and** an Echo entitlement |

No leg is unblocked by a workaround available to this session, and none was
substituted.

## 12. Controller-changing operations this session

**None.** The only controller interaction was the fixed-vector read-only
EtherNet/IP identity/TCP-IP-interface/time-sync probe recorded in §7.
