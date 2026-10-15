# Physical S7-1200 press I/O bridge

The existing CPU **1214C DC/DC/DC, 6ES7 214-1AG40-0XB0, FW 4.7.3** supplies
onboard I/O; the S7-1500 in PLCSIM Advanced runs the Fraktal press logic. This
small physical application contains a tag table, one hardware driver, one
shared communication endpoint and a retained boot counter. `Main` makes one
root call. It does not duplicate the Unit, sequences or device lifecycle.

```mermaid
flowchart LR
    A[Fraktal press in PLCSIM Advanced] <-->|Two cyclic TCP streams| B[1214C I/O bridge]
    B <-->|14 DI / 10 DQ| C[Press bench]
```

This uses ordinary Open User Communication (`TSEND_C`/`TRCV_C`), without
PUT/GET or a PC relay. PLCSIM Advanced supports TCP/IP communication to real
CPUs but does not simulate PROFINET IO or I-device functionality. See Siemens'
[communication paths](https://docs.tia.siemens.cloud/r/simatic_s7_1500_et_200mp_manual_collection_enus_21/comprehensive-information/cpu-function-manuals/s7-plcsim-advanced/communication-paths/communication)
and [restrictions](https://docs.tia.siemens.cloud/r/simatic_s7_1500_et_200mp_manual_collection_enus_21/comprehensive-information/cpu-function-manuals/s7-plcsim-advanced/product-overview/differences-between-a-simulated-and-a-real-cpu/restrictions-for-all-supported-cpus).

## Project and mapping

[`00_System/io.json`](00_System/io.json) owns the proposed **rewiring to the
1214C terminals**, not the old EtherCAT addresses. It preserves the electrical
tags and feeder polarity from the
[approved press list](../../../../../Specification/Reports/CX2030_PRESS_IO_MAPPING.md).
The eight ordinary outputs are the three cylinder valve pairs and two start
lamps. Q1.0/Q1.1 are the unverified Control On coils and are always FALSE.

I1.5 is reserved for an **evaluated two-hand relay result**, additional to the
original worksheet. `EVALUATED_TWO_HAND_WIRED` stays FALSE until that wiring is
verified; pressing the two ordinary button inputs never synthesizes this
result. No quality sensor exists in the supplied list, so physical-mode
`PartQuality` is FALSE. The independent hardwired safety circuit retains its
authority; this ordinary I/O bridge does not implement its functions.

`OUTPUT_MAPPING_CONFIRMED` also defaults FALSE. The local output permit requires
it, a fresh round trip, peer enable, Control On feedback, the E-stop status
mirror and operating pressure without the low-pressure signal. Opposite coil
demands withdraw both coils. Ram down additionally requires door closed and
the evaluated two-hand input. The driver writes every output every scan.
On CPU STOP configure/verify substitute output values of zero in TIA hardware
properties. The bridge does not operate the two unverified Control On coils;
establish control power through the commissioned bench circuit.

## Network and protocol

The physical project uses **192.168.0.10/24**. The matching bench simulator
project uses **192.168.0.20/24**, reserved for a separate bench instance. Keep
the saved `Fraktal` instance, its addresses, storage and adapter mappings.
Before deployment, connect the bench instance to the physical Ethernet adapter
through PLCSIM Advanced's distributed TCP/IP mode and ensure the VM/host bridge
passes that network. Do not infer reachability from the local virtual adapter.

The physical receive port is **24001**, simulator receive port **24002**;
each side maintains one active send connection and one passive receive
connection. Interface hardware ID 64 and connection IDs 257/258 are project
configuration: verify them against the target's system constants and other
OUC users. The small standalone bridge allocates only these two connections.

Each 32-byte frame is explicitly encoded in network byte order: `FRIO`,
version/role/reserved bytes, boot epoch, sequence, echoed epoch/sequence,
signal bits, enable/reserved bytes and CRC-16/CCITT-FALSE over bytes 0–29.
Send buffers remain unchanged while a job is busy. Receive uses a fixed full
frame, so TCP segmentation cannot expose a partially updated image.

The default period is **50 ms**, watchdog **500 ms**. CRC/schema/role, reserved
bits, bounds, boot epochs and forward sequence are checked before publication.
A recent echo of an actually offered sequence proves the return path. Replays
do not renew liveness. Loss clears published signals and peer enable; connection
reset flushes a damaged stream. After loss/restart, a controller must observe
its actual demands at zero before enabling outputs again, and the physical
endpoint must receive a fresh disabled/neutral frame. CRC is error detection,
not authentication: use this ordinary protocol only on the isolated bench LAN.

## Regeneration and engineering

Preserve the saved target project/certificate. Copy it to a **new offline
directory** before importing this application. Generated plans replace program
blocks only in the specified copy; they contain no download command.

```powershell
python FraktalCore/PLC/Siemens/tools/fraktal_tia_io_bridge.py --out <new-sources> --project <copied-1214C.ap20> --native <new-export>
python FraktalCore/PLC/Siemens/tools/fraktal_tia_io_bridge.py --client --out <new-client-sources> --project <copied-press-1516.ap20> --native <new-client-export>
```

Run each resulting `import.plan` with the existing owner-whitelisted
`candidate_structure_examples/Fraktal.Tia.Cli.exe`. Require zero compile errors
and warnings and compare native exports before deployment. The client profile
wraps the press's existing input routine, replaces the local plant simulation
with real feedback and retains the three-call press `Main`.

Commission inputs and outputs individually with the pneumatic energy isolated,
check the proposed terminal mapping, confirm zero outputs on cable loss, peer
STOP and physical CPU STOP, then validate the independent safety circuit and
the local permit gates. Enabling either wiring gate is an explicit engineering
change after those checks. Physical download/energization is separate from
preparing these projects.
