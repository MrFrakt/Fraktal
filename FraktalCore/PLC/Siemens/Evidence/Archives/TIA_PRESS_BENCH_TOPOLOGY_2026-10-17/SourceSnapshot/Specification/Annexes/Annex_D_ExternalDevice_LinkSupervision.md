# Annex D — Worked Example: External Device & Link Supervision

*Companion to **Fraktal Core** (Part I) exercised through the **Fraktal/TC3** binding (Part II); slots under Core §12.*
*Core concepts demonstrated: device connector & link supervision (§3.15), loss reactions, bounded reconnect with no self-resume, link fault in the stall walk (§6.9/§8.2). / TC3 mechanics used: TCP socket/transport FBs, `TON`/`SysTime`, `OPC.UA.DA` pragmas (TC3 §3.10).*
*Reference implementation — illustrative, not compile-tested; validate against the pinned TwinCAT version and your transport library.*

This annex builds the **external device connector** tier (§3.15) and shows the one thing the I/O-bound annexes (A–C) can't: a **networked smart device** whose dominant failure mode is the **link itself going away**. It demonstrates the `I_DeviceConnector` contract — heartbeat, a configured loss reaction, bounded reconnect with **no self-resume** — and shows a dead link rolling up through the **same stall walk** (§6.9) as any sensor fault, with no per-device diagnostic code.

The station from Annexes A–C gains a programmable DC power supply over TCP (a typical end-of-line-test device). The supply is fronted by a Control Module so the Unit commands it like any other CM and never sees the protocol:

```
InfeedUnit (FB_InfeedUnit : FB_Unit)                       ← Annex C
 ├─ Separator1   (FB_SeparatorCM)                           ← Annex A
 ├─ ClampStation (FB_ClampEM → CylA, CylB)                  ← Annex B
 ├─ FixtureUnit  (FB_FixtureUnit : FB_Unit)                 ← Annex C
 └─ Supply1      (FB_SupplyCM, Control Module)              ← here
       └─ _conn  (FB_PsConnector : I_DeviceConnector)       ← TCP session + heartbeat
```

---

## D.1 Reasons (Framework band — already registered, §8.8)

```iecst
// E_Reason — external device / link supervision (Framework 2010–2019)
//   LINK_TIMEOUT          := 2010   // heartbeat lapsed beyond LinkTimeout
//   DEVICE_NOT_READY      := 2011   // session up, device reports not operable
//   DEVICE_PROTOCOL_ERROR := 2012   // malformed / refused exchange

{attribute 'qualified_only'}
TYPE E_LinkReaction : (HOLD := 0, ABORT := 1, MODE_STOP := 2) DINT;
END_TYPE
```

---

## D.2 The connector (`I_DeviceConnector`)

The connector owns the socket and the heartbeat; nothing above it sees the protocol. Heartbeat here is a cyclic identity/measure query whose reply must arrive within `LinkTimeout`; consecutive misses drop `Linked`.

```iecst
// Publication is inherited from the explicitly marked deployed root instance.
FUNCTION_BLOCK FB_PsConnector IMPLEMENTS I_DeviceConnector
VAR
    ParCfg : PsLinkParCfg;          // Endpoint, LinkTimeout, Reaction, BackoffMin/Max
    _name  : STRING(80);
    _sock  : FB_EthSocket;          // transport (vendor/stack detail stays in here)
    _hbReq : FB_PsQueryIdentity;    // the cyclic liveness exchange
    _tHb   : TON;                   // heartbeat-due timer
    _tLoss : TON;                   // loss-confirm timer (PT := LinkTimeout)
    _tBkoff: TON;                   // reconnect backoff
    _linked: BOOL;
    _diag  : ST_Diagnostic;
    _lastSeen : DT;
END_VAR

METHOD Setup : BOOL
VAR_INPUT Name : STRING(80); Endpoint : STRING(255); Recipe : I_RecipeProvider; END_VAR
    THIS^._name := Name;  ParCfg.Endpoint := Endpoint;
    // recipe wiring (LinkTimeout, Reaction, backoff) as Annex A …

METHOD Connect    : BOOL   _sock.Open(ParCfg.Endpoint);   Connect := TRUE;
METHOD Disconnect : BOOL   _sock.Close();   _linked := FALSE;   Disconnect := TRUE;

PROPERTY Linked    : BOOL        Linked    := _linked;
PROPERTY LastSeen  : DT          LastSeen  := _lastSeen;
PROPERTY LinkReason : ST_Diagnostic   LinkReason := _diag;

// ---- cyclic ----
METHOD Cyclic
    IF NOT _sock.Connected THEN
        _M_EnterLost(E_Reason.DEVICE_NOT_READY, 'Session down');
        _M_Reconnect();   RETURN;
    END_IF
    // heartbeat: issue query when due, watch for reply within LinkTimeout
    _tHb(IN := NOT _tHb.Q, PT := ParCfg.HbPeriod);
    IF _tHb.Q THEN  _hbReq.Execute := TRUE;  END_IF
    _hbReq(Socket := _sock);
    IF _hbReq.Done THEN
        _hbReq.Execute := FALSE;  _tHb(IN := FALSE);
        _lastSeen := SysTime();              // synchronized clock (§2.7)
        _tLoss(IN := FALSE);  _linked := TRUE;  _M_ClearDiag();
    ELSIF _hbReq.Error THEN
        _M_EnterLost(E_Reason.DEVICE_PROTOCOL_ERROR, 'Bad/again refused reply');
    END_IF
    // confirm loss only after LinkTimeout of no healthy beat
    _tLoss(IN := NOT _linked, PT := ParCfg.LinkTimeout);
    IF _tLoss.Q THEN _M_EnterLost(E_Reason.LINK_TIMEOUT, 'Heartbeat lapsed'); END_IF
```

`_M_EnterLost` sets `_linked := FALSE` and stamps `_diag` with the reason and the connector's `SourcePath`; `_M_Reconnect` re-opens on a bounded backoff (`_tBkoff`, BackoffMin→BackoffMax) and **never** resumes a dependent command on its own.

---

## D.3 The Control Module that fronts the device

`FB_SupplyCM` exposes ordinary device commands (`OUTPUT_ON`, `SET_VOLTAGE`) through the standard handshake. Its only addition over a plain CM is that **every command first requires `Linked`** — a lost link is adopted as the module's fault:

```iecst
// The type is ONLY its device logic: Execute/Abort arrive through ExecuteCommand/
// AbortCommand, and Busy/Done/Error/Aborted/ErrorID are base-owned (§2.2).
FUNCTION_BLOCK FB_SupplyCM EXTENDS FB_ControlModuleBase
VAR_INPUT
    Command : E_PsCommand;
    ParCfg  : ST_PsParCfg;
    ParCmd  : ST_PsParCmd;        // e.g. Voltage for SET_VOLTAGE — latched on the Execute rising edge
END_VAR
VAR_OUTPUT
    OutCmd : ST_PsOutCmd;
    OutImm : ST_PsOutImm;
END_VAR
VAR
    {attribute 'OPC.UA.DA' := '0'}
    _conn : FB_PsConnector;
END_VAR

METHOD Setup : BOOL
VAR_INPUT Name : STRING(80); Endpoint : STRING(255); Recipe : I_RecipeProvider; END_VAR
    _conn.Setup(Name := CONCAT(Name, '.Link'), Endpoint := Endpoint, Recipe := Recipe);

// ---- cyclic body ----
METHOD PROTECTED OnCyclic
OnCyclic := SUPER^.OnCyclic();
_conn.Cyclic();                                   // heartbeat/session managed here
IF NOT _conn.Linked AND Busy THEN
    _M_AdoptLink();                               // link loss → CM fault (D.4)
END_IF
// … normal command step chain (SET_VOLTAGE → OUTPUT_ON) when Linked, in _M_Dispatch …
```

The loss **reaction** is honoured here: `HOLD` freezes the chain awaiting reconnect; `ABORT` safe-stops the command and reports `Error`; `MODE_STOP` additionally asks the owning Unit to stop after cycle (the Unit handles it in `OnModeExit`, §3.14).

---

## D.4 Link loss rolling up the stall walk

`_M_AdoptLink` copies the connector's first-out link reason up — exactly the rollup of §8.2, so the device names itself:

```iecst
METHOD PRIVATE _M_AdoptLink
    // Adopt the connector's first-out link reason VERBATIM — reason, SourcePath and Since (§8.2);
    // the base moves the module to Error and stamps it.
    _M_AdoptFault(_conn.LinkReason);              // reason + "InfeedUnit.Supply1.Link" path
```

Concrete trace — the supply is unplugged mid-cycle:

```
InfeedUnit  step Nxxx "Energize" ──awaits──▶ Supply1.OUTPUT_ON
Supply1 (FB_SupplyCM)            ──Error────▶ adopts link reason
Supply1._conn (FB_PsConnector)   ──Lost─────▶ LINK_TIMEOUT @ "InfeedUnit.Supply1.Link"
```

The operator sees, on the **Unit's** view, through the unchanged §6.9 walk:

> **Step … Energize stalled → awaiting Supply1.OUTPUT_ON → InfeedUnit.Supply1.Link: heartbeat lapsed**

…with no per-device diagnostic code — only the heartbeat, the standard handshake, and the recursive `GetFaultSummary`.

---

## D.5 HMI (§3.13)

```
Station ▸ Supply1                         (CM tile: state LED ← ExecState; link LED ← Linked)
   └─ Link   last seen 12:04:51 · "heartbeat lapsed"   [Reconnect]
```

| View | Binding |
|------|---------|
| **Tile** | name; state LED ← `ExecState`; **link LED** ← `_conn.Linked`. |
| **Detail** | manual `OUTPUT_ON`/`SET_VOLTAGE` (release-gated, §7.6); **last-seen** ← `LastSeen`; live `LinkReason.Description`; **Reconnect** (release-gated). No auto-resume of the interrupted command — resumption is a deliberate operator/sequence step. |

---

## D.6 What this annex demonstrated

- A **networked smart device** as a first-class Control Module via `I_DeviceConnector`, with the protocol confined to the connector (§3.15).
- **Link supervision**: heartbeat, `LinkTimeout`, and a configured `HOLD`/`ABORT`/`MODE_STOP` reaction — the networked analogue of an interlock.
- **Bounded reconnect with no self-resume** (§3.15, mirroring the safety re-energize rule §9.3).
- A **dead link rolling up the same stall walk** as any sensor fault, naming the exact device with **no per-device code** (§6.9, §8.2).

---

*End of Annex D (draft).*
