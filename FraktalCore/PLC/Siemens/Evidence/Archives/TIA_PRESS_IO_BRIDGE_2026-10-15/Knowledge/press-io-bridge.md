# Physical 1214C I/O companion (2026-10-15)

**Measured.** Owner confirmed existing CPU 1214C DC/DC/DC
6ES7 214-1AG40-0XB0 FW4.7.3 at 192.168.0.10, onboard I/O.
`FraktalCore/PLC/Siemens/Examples/PressIoBridge` owns io.json (proposed terminal
rewiring) and guide. Shared endpoint: Framework/IoBridge/bridge.scl.in;
generator/verification: tools/fraktal_tia_io_bridge.py. This is a small I/O
companion, not the S7-1200 Fraktal binding.

Physical project Main calls one hardware driver. 14 DI, eight ordinary DQ,
Q1.0/Q1.1 always off for unverified Control On coils. OUTPUT_MAPPING_CONFIRMED
and EVALUATED_TWO_HAND_WIRED FALSE. I1.5 requires an evaluated two-hand relay
result, never ordinary-button logic. PartQuality FALSE: no supplied sensor.
Independent safety remains external. Local permit also requires Control On,
E-stop mirror, operating pressure, round trip and peer enable; ram down adds
door closed/evaluated two-hand. Opposite demands withdraw both coils.

TCP TSEND_C/TRCV_C 3.2, TCON_IP_v4 1.0 pinned; two connections, 32-byte
network-order frame, CCITT CRC, epoch/forward sequence, bounded recent echo,
50 ms period/500 ms watchdog. Actual zero demands and a neutral disabled
frame are required after loss. Physical IP .10, separate simulator bench .20
on 192.168.0/24, ports 24001/24002. Do not change original Fraktal mappings.

Physical05 software/hardware compile 0/0; native 9 code/type blocks/4 interfaces
match and boot Epoch Retain. Client05 press 503/129 match, 21 logical I/O fields
private, Main three calls; GRAPH19/4, LAD198 networks/192 calls. Native protocol
18/18 on disposable FrkIoBridgeTest (.51 link-local, secondary172.31.254.51,
maps0); it was powered off/unregistered. Original Fraktal remains RUN, TCPIP,
169.254.212.49/192.168.1.1, maps0. Real CPU never downloaded. Physical network,
latency, STOP/cable withdrawal and bench commissioning remain open.

Artifacts (private project certificates, excluded from Git) under
AppData/Local/Fraktal/Artifacts: PressIoBridge_1214C_20261015.zip and
PressIoBridge_Press1500_20261015.zip. Native project copies under TiaStations/
Press_IoBridge_1214C_20261015/FrkSpikeS2.ap20 and
Press_IoBridge_Press1500_20261015/FrkS12/FrkS12.ap20. Original projects preserved.

P1 namespace prerequisite now rejects line.* in station/model config. Full
line owner/local mirror remains next. Evidence: Specification/Siemens/Evidence/
TIA_PRESS_IO_BRIDGE_2026-10-15.md. Do not claim hardware I/O, R3/R6 or full
profile conformance from these protocol/compile gates.
