# Physical 1214C press I/O companion — 2026-10-15

The owner confirmed CPU 1214C DC/DC/DC `6ES7 214-1AG40-0XB0`, FW 4.7.3,
192.168.0.10, using onboard terminals. The
[guide and mapping](../../../FraktalCore/PLC/Siemens/Examples/PressIoBridge/README.md)
describe the proposed rewiring and matching simulated S7-1500 driver. This is
an I/O companion, not the constrained S7-1200 Fraktal profile.

## Implemented

The small physical application has one calling Main, one hardware driver, the
shared TCP endpoint, a retained boot counter and a raw tag table: 14 DI, eight
ordinary DQ, two inhibited Control On DQ. Native groups follow
`Framework/IoBridge` and `Examples/PressIoBridge/00_System`. The simulator
profile wraps the existing press input routine and retains its three-call Main.
All 21 logical I/O members are private in native XML, closing an external raw
command path.

Frames carry explicit network-order version/role, epoch/sequence, bounded
recent echo, signals, enable and CCITT CRC. Period 50 ms, watchdog 500 ms.
Expired/refused frames withdraw the image; connection resets flush damaged
streams. Restart requires actual zero demands and a fresh disabled/neutral
image before enabling. Instruction versions are pinned to native exports:
TSEND_C/TRCV_C 3.2, TCON_IP_v4 1.0.

`OUTPUT_MAPPING_CONFIRMED` and `EVALUATED_TWO_HAND_WIRED` remain FALSE;
Q1.0/Q1.1 remain FALSE. I1.5 is an additional evaluated relay result, never
derived from ordinary buttons. No quality sensor exists in the supplied list,
so physical PartQuality is FALSE. Independent bench safety retains authority.

The physical copy keeps 192.168.0.10/24; the simulator bench copy uses
192.168.0.20/24, ports 24001/24002. Physical adapter mapping is commissioning
work. No physical CPU download or existing Fraktal address/mapping change occurred.

## Gates

| Check | Result |
|---|---|
| Physical05 software/hardware compile | Both 0 errors / 0 warnings |
| Physical native comparison | 9 code/type blocks, 4 interfaces; Epoch is Retain |
| Simulator client04 full import + client05 privacy delta | Every final program compile 0 errors / 0 warnings |
| Simulator client05 comparison | 503 code/type blocks, 129 interfaces; 21 private I/O members |
| Sequence read-back | GRAPH AUTO 19 / HOME 4; LAD 198 networks / 192 calls |
| Frozen Core candidate | All 31 UDTs and 22 enum domains unchanged |
| Native protocol | 18 checks, 0 failures: watchdog, CRC, replay, schema/role, cached demands, epoch/sequence wrap, neutral rearm |
| Bridge tools | 11 tests pass, including forged manifest, address bounds and I/O privacy |
| Siemens tools | 220 tests pass after the final privacy test |
| Consistency/candidate tests | 44 pass; consistency and Siemens lint 0 findings |

The protocol ran on a disposable CPU1516, FrkIoBridgeTest at 169.254.212.51,
secondary 172.31.254.51, all physical mappings zero. Its helper powered off and
unregistered only that instance. Fraktal remained CPU1516/RUN/TCPIP at
169.254.212.49 and 192.168.1.1, mappings zero.

Early attempts are retained: RETAIN syntax corrected to VAR RETAIN; dependent
client and I/O DB imported together; standalone OB1 made optimized. The first
harness falsely compared observation timestamps as controller state; the
corrected read-only observation passed without replaying the download. The
test copy's initial full hardware build recorded two existing bench security
warnings (no protection level/display password). Final incremental source
builds pass; R6 and fresh production security qualification remain open.

## Native bundles

The local private engineering bundles include native projects, guide, mapping
and sources; they are excluded from Git/evidence because they preserve target
project certificates. Original project filenames are preserved.

| Bundle under `%LOCALAPPDATA%\Fraktal\Artifacts` | Bytes | SHA-256 |
|---|---:|---|
| PressIoBridge_1214C_20261015.zip | 9392689 | f815d8c1fd8272ab17f4054eaa1c8cfdf118c2f473260abd4951c7bf0515568e |
| PressIoBridge_Press1500_20261015.zip | 124098555 | 3c565bd8905b8f0148e91d978aa5cc7c793a7d794a75d541b70b77180b036b44 |

Projects: `TiaStations/Press_IoBridge_1214C_20261015/FrkSpikeS2.ap20` and
`TiaStations/Press_IoBridge_Press1500_20261015/FrkS12/FrkS12.ap20`.
The approved Openness executable was reused without rebuilding.

Physical wiring, real TCP exchange, latency, cable/peer STOP recovery, CPU STOP
substitution and press acceptance remain commissioning gates. Simulated 1500
protocol tests do not substitute for them. Wiring gates stay disabled until
the commissioning engineer verifies their conditions.

P1 gains its namespace prerequisite: station/model config refuse line.* keys,
with both cases tested. Owner/local mirror, persistence and the HMI Line facet
remain next. The bridge does not close P8's generic I/O topology/PN-health work.

[Raw evidence manifest](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_PRESS_IO_BRIDGE_2026-10-15/SHA256SUMS).
