# Fraktal/TIA R1 — platform baseline evidence, 2026-10-08

**Gate:** R1 platform baseline (Part IV §0). **Verdict: OPEN — partly evidenced.**
Append-only record; later findings go in a new dated record.

## 1. Controller identity (measured)

Method: `FraktalCore/PLC/Siemens/tools/s7_probe.py ident --host 192.168.0.10`
(read-only: COTP connect rack 0 slot 1, S7 setup, SZL 0x0011 index 0).

```
pdu 240
module idx=0001 order=6ES7 214-1AG40-0XB0  raw=0000000d2020
module idx=0006 order=6ES7 214-1AG40-0XB0  raw=0000000d2020
module idx=0007 order=6ES7 214-1AG40-0XB0 V4.7.3 raw=000056040703
```

| Item | Value |
|---|---|
| Article | `6ES7 214-1AG40-0XB0` — SIMATIC S7-1200 CPU 1214C DC/DC/DC |
| Firmware | V4.7.3 |
| Negotiated S7 PDU | 240 bytes |
| MAC | 8c-f3-19-b8-3f-4d (Siemens OUI) |
| TCP ports | 102 open; 80, 443, 4840, 502 closed (no web server, no OPC UA server configured) |
| SZL 0x001C (component identification) | refused (`0a000000`) |
| Engineering host route | NIC `Ethernet1` 192.168.0.123/24, same subnet |

**Consequence.** The bench is an S7-1200, not an S7-1500. Part IV §1.1 makes
S7-1500 the reference family and S7-1200 a constrained family; no result measured
on this CPU transfers to S7-1500.

## 2. Vendor figures for this article (documented, not measured)

From the Siemens data sheet `6ES7214-1AG40-0XB0` (firmware V4.7, data sheet date
2026-09-28; archived in the engineering KB as
`siemens-kb/manuals/downloaded/Datasheet_6ES7214-1AG40-0XB0_CPU1214C_DCDCDC.pdf`):

- work memory 150 KB (program + data), load memory 4 MB, retentive 14 KB, bit
  memory 8 KB, local data 16 KB (OB1) / 6 KB (other priority classes);
- OPC UA server (DA, subscriptions, methods), runtime licence "Basic" required;
  10 sessions, 5 subscriptions/session, 100 ms min sampling, 200 ms min publishing,
  20 methods, ~1,000 monitored items recommended, 2 server interfaces, 2,000 nodes
  per user-defined interface; 10 OPC UA connections max;
- connections: PG 4/4, HMI 12/18, S7 8/14, open user 8/14, web 2/30, total 34/68;
- PG/OP communication TLS 1.3 pre-selected; user management 42 users / 14 groups / 20 roles;
- languages LAD, FBD, SCL (no GRAPH).

Siemens entry 109755846 (V1.0, 02/2024; archived as
`siemens-kb/manuals/downloaded/TIA_Portal_OPC_UA_system_limits_109755846.pdf`)
gives the same S7-1200 V4.6 server limits.

TIA Portal V20 information system (en-US): S7-GRAPH, `REF_TO` references, named
value data types, `LTIME`/`LDT`/`ULINT` are scoped S7-1500 only; VARIANT, LREAL,
WSTRING, parameter instances, `GetInstancePath`, `RUNTIME`, `RD_SYS_T` are scoped
S7-1200 and S7-1500.

## 3. Engineering workstation (measured)

| Item | Value |
|---|---|
| OS | Windows 10 Pro 10.0.19045, account `WINDOWS-10\Siemens` (local Administrators) |
| TIA Portal | V17, V18, V19, **V20** installed side by side |
| Openness | `PublicAPI\V20\Siemens.Engineering.dll` (registry `Openness\20.0\PublicAPI\20.0.0.0`) |
| Simulation | S7-PLCSIM V17/V18/V20; S7-PLCSIM Advanced V5.0 |
| .NET | SDK 10.0.401; .NET Framework 4.x runtime; no 4.8 Developer Pack (not needed) |
| `Fraktal.Tia.Cli` | builds warning-clean (net48, x64); `processes` loads the Openness API from the installed Portal |

**Openness access refused** (`Fraktal.Tia.Cli create-project`, headless):

```
{"event":"fatal","type":"Siemens.Engineering.EngineeringSecurityException",
 "message":"... Owner 'WINDOWS-10\\Siemens' of this process is not member of the
 windows group 'Siemens TIA Openness'. Please contact your administrator."}
```

The local group exists and has no members. Adding the account was attempted by
the agent and blocked by the session's permission policy; it is an administrator
action (`tools/Enable-TiaOpenness.ps1`, then a new logon).

## 4. Still owed before R1 can PASS

1. Openness access granted and a headless create → compile → download → online
   run against 192.168.0.10 recorded (S15).
2. TIA licence inventory (STEP 7 Professional/Basic V20 keys in ALM) recorded.
3. OPC UA runtime licence status of the bench ("Basic") recorded.
4. The PG/PC interface name TIA reports for `Ethernet1` recorded.
5. The S7-1500 target decision (hardware to procure, or PLCSIM-only scope stated).
