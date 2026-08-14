# Fraktal/AB S1 — EtherNet/IP/CIP data-path evidence

**Spike:** S1 EtherNet/IP/CIP data and time path

**Result:** **PASS — the named v33 target moved the required symbolic data
shapes, enforced External Access, survived bounded fragmentation/concurrency/
reconnect tests, and supplied wall-clock time with explicit synchronization
quality through the selected initial EtherNet/IP adapter**

**Date:** 2026-08-13

## 1. Baseline and safety boundary

The target is the R1 controller `1769-L24ER-QB1B/A`, firmware `33.014`, serial
`7036B510`, at `192.168.100.89:44818`. The probe host uses
`Ethernet1=192.168.100.99/24` with a direct connected route. The controller was
in `REMOTE RUN`.

The initial acquisition sections in this record were read-only. Later, with the
user's explicit authorization and all I/O disconnected, Studio downloaded the
verified memory-only `FraktalPhase0` v33 fixture through the serial-matched USB
path and the fixed execution tool wrote only its `FRK_Write*` memory tags. The
tool restored and verified all inputs at the end. A separate serial- and
fixture-guarded tool explicitly set only `WallClockTime` from the host UTC clock.
No fault, firmware, network-configuration, or physical-I/O operation occurred.
Values were suppressed; committed probes report status, type/shape, timing, and
Boolean comparison results.

## 2. Identity and TCP/IP object

`fraktal_ab_eip_probe.py` sent ten ListIdentity requests and read TCP/IP
Interface Object `0xF5` and Time Sync Object `0x43`, instance 1, with
`Get_Attribute_Single` only.

| Item | Result |
|---|---|
| Identity correlation | PASS: serial `7036B510`, model `1769-L24ER-QB1B/A LOGIX5324ER`, revision `33.014` |
| Address | `192.168.100.89`, mask `255.255.255.0`, no gateway/DNS |
| Startup configuration | raw field `0` (stored configuration); full control word `16` |
| Identity latency | 5.252 ms min / 15.973 ms median / 26.020 ms max, 10 samples |

FactoryTalk Linx 6.50 was also configured with a workstation-only
point-to-point driver alias `Fraktal_AB` and an explicit one-device list. Its
supported command-line browse of `Fraktal_AB\192.168.100.89` succeeded. The
Linx node independently matched controller name `FIS_Aptiv_Rev1`, catalogue
`1769-L24ER-QB1B`, serial `7036B510`, and revision `33.14`. Studio 5000 v33
subsequently selected this node, connected through the exact path
`Fraktal_AB\192.168.100.89`, and matched the same identity in its
**Connected To Upload** dialog. Studio and SDK read-only uploads over this
Ethernet route timed out, so the Ethernet online-project workflow remains open
S4/S15 evidence rather than an S1 identity/routing failure. Studio later
completed the read-only upload through USB at `Backplane\16` with zero errors
and warnings.

A final three-sample direct identity read after the Linx configuration still
matched serial `7036B510` at `192.168.100.89`; latency was 6.695 ms minimum,
6.951 ms median, and 12.392 ms maximum. TCP/IP configuration remained
`192.168.100.89/24` with no gateway. The pre-test application reported
`PTPEnable=1`, `IsSynchronized=0`; after the disposable fixture download the
fixture's controller configuration reported both PTP disabled and
`IsSynchronized=0`. The two project configurations are recorded separately and
are not treated as a clock-quality transition.

After the late Studio upload timeout, a new three-sample identity probe again
matched firmware `33.014` and serial `7036B510`; TCP/44818, TCP/IP
configuration, and the supported Linx command-line browse also passed. No
controller-changing operation was issued.

After the successful USB upload and offline save, a final three-sample
EtherNet/IP identity probe again matched firmware `33.014`, serial `7036B510`,
and `192.168.100.89/24`; the supported Linx browse also succeeded. This
distinguishes the Ethernet upload timeout from a general controller or project
upload failure. It did not by itself close S1's write, time, or limit cases; the
controlled write case was subsequently closed by §5 below.

## 3. Namespace acquisition

The live Logix namespace completed successfully through pylogix `1.1.5`:

- 491 returned symbol records;
- 160 program-scoped records; and
- 21,187.958 ms elapsed for the full request.

The offline SDK export contained 461 authored `<Tag>` records. The counts are
not asserted equal: the live result also includes program namespace/system
representations. S7 must define which generated manifest surface is
authoritative; a raw controller symbol upload is not the Fraktal manifest.

An exploratory pycomm3 `1.2.16` full tag initialization timed out and is not
used as positive evidence. This client difference is a gateway-selection and
timeout/reconnect test input, not a controller failure.

## 4. Symbolic read matrix

`fraktal_ab_symbolic_read_probe.py` used a 500-byte connected-message size and
required serial `7036B510`. Values remained redacted.

| Case | Scope/type | Result | Elapsed |
|---|---|---:|---:|
| scalar | controller `DINT` | PASS | 11.125 ms |
| scalar | program `REAL` | PASS | 11.570 ms |
| string | program standard `STRING` | PASS, length 4 | 11.146 ms |
| UDT member | program `INT` | PASS | 11.746 ms |
| UDT member | controller `DINT` | PASS | 11.024 ms |
| array | controller `DINT[25]` | PASS, 25 values | 11.042 ms |
| large UDT | controller raw UDT, 1,232 bytes | PASS | 29.014 ms |

The 1,232-byte value exceeds the forced 500-byte connection size. pylogix uses
CIP Read Tag Fragmented service `0x52` for this path, so this is positive
fragmentation/reassembly evidence. It does not yet establish the final gateway
connection size or worst-case polling budget.

## 5. Controlled write and External Access matrix

The fixture generated by `fraktal_ab_phase0_fixture.py` contains controller- and
program-scoped DINTs, REAL, DINT[25], DINT[1024], standard STRING, UDT, Read
Only, None, scan/heartbeat, test-complete, and cyclic-result memory tags. Its
periodic task disables output updates; the embedded I/O module is inhibited;
the L5X contains no physical-I/O operand.
Studio v33 imported it with zero warnings/errors, verified it with zero
errors/warnings, downloaded it over USB, and returned the controller to Remote
Run with `Controller OK`.

`fraktal_ab_phase0_execute.py` required serial `7036B510`, an explicit arm flag,
and the full fixture fingerprint before the first write. The physical result was:

| Case | Result |
|---|---|
| controller/program DINT and controller REAL | acknowledged write/readback and PLC result PASS |
| DINT[25] | whole-array write/read plus PLC boundary-copy result PASS |
| DINT[1024] | fragmented 4 KiB whole-array write/read, PLC boundary samples, and checksum PASS |
| standard STRING | write/read and PLC length/checksum use PASS |
| UDT | scalar members and four-element member array PASS |
| PLC cyclic result | copied scalars/samples and checksum PASS |
| Read Only | write rejected with `Privilege violation`; readable derived value correct |
| None | absent from CIP tag browse; read/write rejected with `Path segment error` |
| liveness | scan count and heartbeat advanced |
| cleanup | all writable inputs and the derived result checksum verified zero/empty |

The fixed tool returned `execution_passed=true` with pylogix `1.1.5`. Detailed
artifact hashes, Studio dialog identity, rollback state, negative cases, and the
exact command are recorded in
[`AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md`](AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md).

## 6. Transport budget and recovery

`fraktal_ab_transport_budget_probe.py` is fixed to three read-only fixture tags,
requires serial `7036B510`, caps every workload, and closes every client. Its
physical run produced:

| Case | Result |
|---|---|
| 4 KiB fragmented read | PASS at requested connection sizes 128, 256, 500, 1000, 2000, and 4000 bytes; elapsed 899.692, 462.634, 265.608, 200.895, 176.773, and 132.423 ms respectively |
| reconnect | 25/25 connect/read/close cycles; 89.838 ms min, 111.867 ms median, 151.260 ms max |
| timeout recovery | forced 0.1 ms session timeout failed as intended; a new normal client recovered in 103.246 ms |
| concurrent readers | independent levels 1, 2, 4, 8, 12, and 16 all passed; 16-reader maximum elapsed 262.793 ms |

S1 therefore freezes a conservative initial adapter ceiling of **500 bytes per
connected request**, **four concurrent PLC reader sessions**, and application-
level fragmentation for larger arrays/UDTs. The higher successful values are
headroom evidence, not a production sizing promise. S3 must still measure the
real manifest/forest workload and may lower those operational budgets.

## 7. Wall clock and synchronization quality

The first fixture wall-clock read succeeded but returned 1998, about
902,980,517 seconds behind the probe host. The guarded
`fraktal_ab_time_probe.py --set-to-host` operation then set only
`WallClockTime` from host UTC. Seven post-set samples succeeded; controller
minus host-midpoint offset ranged from -19.855 ms to -12.629 ms. Identity,
firmware, IP configuration, and Remote Run state were unchanged.

Time Sync Object `0x43`, instance 1 reported `PTPEnable=0` and
`IsSynchronized=0` for the downloaded fixture before and after the set.
Accordingly, the controller timestamp is usable as the event's source time but
shall be published with `TimeSynchronized=FALSE`; the gateway separately records
its reception time and shall not claim correlated ordering with other
controllers. A deployment that requires correlated multi-controller ordering
must commission CIP Sync/PTP and prove `IsSynchronized=1`. An unsynchronized
clock is represented honestly, not promoted to synchronized quality and not a
base-binding failure.

## 8. Initial gateway-adapter decision

The initial PLC-facing EtherNet/IP adapter is **pylogix 1.1.5**, pinned by the
wheel SHA-256
`6bf2ab0b4ebff4e5085717cb131efa48feb547d868c6176a47c3f50f7adab56e`.
The exact package path completed the namespace, scalar, program-scope, UDT,
STRING, fragmented read/write, access-control, time, timeout, reconnect, and
concurrency matrix on this controller. It has no package dependencies and its
documented surface includes tag discovery/read/write and PLC-time operations.

This selection is a **private adapter boundary**, not a public generic CIP API.
The future transport-neutral Dart gateway remains responsible for repository
negotiation, allow-lists, roles, freshness, command acknowledgement, and browser
security; its supervised Python worker may expose only the versioned operations
R3/S7/S9 freeze. In particular, arbitrary `Message()` service forwarding is not
part of the boundary. `libplctag` remains a possible future versioned adapter,
but its Dart FFI/type-decoding path has not been exercised on this exact target
and is not S1 evidence.

No production gateway/runtime code is authorized by this decision while R2–R6
remain open. It settled the S1 transport mechanism; S2's disposable AOI
parameter/access fixture subsequently passed, so the next execution-form
blocker is S11.

## 9. Exit decision

S1 is **PASS** on the R1 baseline. The standard contract is movable within the
measured conservative budget, and diagnostic time carries explicit source-clock
quality. S2 is now separately PASS. R2 remains **OPEN** for S4, S11, and S12;
S3/S7/S9 will refine
production polling, manifest, coherence, and repository semantics.

## 10. Primary references

- Rockwell Automation, [Access the WallClockTime object](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/37-01/contents-ditamap/instruction-set/input-output-instructions/access-the-wallclocktime-object.html)
- Rockwell Automation, [Access the TimeSynchronize object](https://www.rockwellautomation.com/en-gb/docs/studio-5000-logix-designer/38-00/contents-ditamap/instruction-set/input-output-instructions/access-the-timesynchronize-object.html)
- ODVA, [CIP Sync](https://www.odva.org/technology-standards/distinct-cip-services/cip-sync/)
- pylogix, [project and supported Logix scope](https://github.com/dmroeder/pylogix)
- pylogix, [connection-size, timeout, and API documentation](https://github.com/dmroeder/pylogix/blob/master/docs/Documentation.md)
- PyPI, [pylogix 1.1.5 release and wheel hash](https://pypi.org/project/pylogix/)
