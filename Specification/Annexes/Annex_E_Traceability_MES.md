# Annex E — Worked Example: Traceability & MES Integration

*Companion to **Fraktal Core** (Part I) exercised through the **Fraktal/TC3** binding (Part II); slots under Core §12.*
*Core concepts demonstrated: traceability & part context (§3.16), ISA-95 host-event mapping (§11.6), shared reason vocabulary (§8.8). / TC3 mechanics used: `SysTime` timestamps (Core §2.7 / TC3 §2.7).*
*Reference implementation — illustrative, not compile-tested; validate against the pinned TwinCAT version and your carrier/host transport.*

This annex builds the **traceability** contract (§3.16) and its **MES/ISA-95 mapping** (§11.6), showing what the recipe-only annexes (A–C) don't: **part identity and results moving up**. It reuses the Annex A–C station, adds a carrier reader at infeed, and shows the **four part-lifecycle events** carrying a NOK whose cause is the **same first-out reason** that would have stopped the machine — written back to the carrier and emitted to MES as an ISA-95 transaction, with **no separate reject-code scheme**.

```
InfeedUnit (FB_InfeedUnit : FB_Unit)                       ← Annex C
 ├─ Carrier   (I_PartCarrier, injected — RFID reader)      ← here
 ├─ Separator1 / ClampStation / FixtureUnit                ← Annexes A–C
 └─ HostEvents (FB_HostEventPublisher; optional sink)       ← here (§11.6)
```

---

## E.1 Part context & the source-agnostic carrier (§3.16)

```iecst
TYPE ST_PartContext : STRUCT
    Uid : STRING(64);  Present : BOOL;  CarrierKind : E_CarrierKind;
    Result : ST_PartResult;  Parents : ARRAY[1..MAX_GENEALOGY] OF STRING(64);
END_STRUCT END_TYPE

TYPE ST_PartResult : STRUCT
    Verdict : E_Verdict;        // NONE | OK | NOK | REWORK
    ReasonCode : E_Reason;      // first NOK reason — same vocabulary as a fault (§8.8)
    Records : ARRAY[1..MAX_RESULTS] OF ST_MeasRecord;
    StationPath : STRING(255);  Stamp : DT;     // synchronized clock (§2.7)
END_STRUCT END_TYPE

INTERFACE I_PartCarrier
    METHOD ReadContext : BOOL (VAR_IN_OUT Ctx : ST_PartContext);   // FALSE → CARRIER_READ_FAILED
    METHOD WriteResult : BOOL (Ctx : ST_PartContext);             // FALSE → CARRIER_WRITE_FAILED
END_INTERFACE
```

The carrier is injected exactly like `I_RecipeProvider` (§3.8), so RFID, Data Matrix, or a host-by-position lookup is configuration, not code.

---

## E.2 The Unit reads, accumulates, writes, and emits

Capture hangs off the existing AUTO mode chain (§6.2) at defined points — no new sequencing:

```iecst
METHOD PRIVATE _M_AutoChain
CASE _step OF
  5:  // ── station entry: confirm identity ──────────────────────────────
      IF NOT _M_PartReceived() THEN RETURN; END_IF           // reads + emits once
      IF Part.Uid <> _expectedUid AND _expectedUid <> '' THEN
          _M_Fault(E_Reason.PART_ID_MISMATCH, 'Part id mismatch');  RETURN;
      END_IF
      _step := 10;

  10: _M_PartStarted();                                      // alarm log + host projection
      _step := 20;
      // … steps 20–40: Separate / Clamp / Process / Unclamp as Annex C …
      // each step that detects a child Error records it into the result:
      //   IF ClampStation.Error THEN
      //       _part.Result.Verdict    := E_Verdict.NOK;
      //       _part.Result.ReasonCode := ClampStation.GetFaultSummary().ReasonCode;  // CYL_NOT_EXTENDED
      //       _M_FinishPart();  RETURN;
      //   END_IF

  50: // ── good completion ──
      _part.Result.Verdict := E_Verdict.OK;
      _M_FinishPart();
      IF NOT _stopReq THEN _step := 5; ELSE _exec := E_ExecState.READY; _step := 0; END_IF
END_CASE
```

`_M_FinishPart` stamps, writes back **before** announcing processed, then emits — OK or NOK by the same path:

```iecst
METHOD PRIVATE _M_FinishPart
    _M_PartProcessed(Verdict := _part.Result.Verdict,
        Reason := _part.Result.ReasonCode);             // write-before-event, host + NOK projection
```

The inherited helpers own both the §8.3 lifecycle entry and its §11.6 host
projection; application chains do not call a host transport directly. On Unit
ERROR entry the base emits `EVENT_PART_PROCESSING_ABORTED` and
`PROCESSING_ABORTED`, adopting the first-out reason when needed — the part leaves
*known-incomplete*, never silently.

---

## E.3 NOK carries the machine's own first-out reason

When `CylB` never reaches its sensor (the Annex B trace), the clamp EM rolls up `CYL_NOT_EXTENDED @ "InfeedUnit.ClampStation.CylB"`. Traceability **adopts that same reason** as the part verdict — no parallel reject taxonomy:

```
ClampStation ──Error──▶ CYL_NOT_EXTENDED @ InfeedUnit.ClampStation.CylB
   ↓ (recorded into _part.Result)
ST_PartResult = { NOK, CYL_NOT_EXTENDED, StationPath="InfeedUnit", Stamp=… }
   ↓ WriteResult → carrier ; Emit(EVENT_PART_PROCESSED) → host
```

So the reject analysis on the MES reads *"NOK — cylinder did not reach extended @ ClampStation.CylB"* — the operator's HMI message and the quality record are the **same sentence**, generated once.

---

## E.4 MES / ISA-95 mapping (§11.6)

Every Unit publishes the bounded `HostEvents : FB_HostEventPublisher` ring. A
deployment that also needs push delivery injects `I_HostEventSink`, mapping the
same fixed records to ISA-95 (IEC 62264) transactions; OPC UA A&C, socket/REST,
or MQTT delivery is composition, not application sequence code:

| In-PLC event (§3.16) | Host / ISA-95 transaction |
|----------------------|---------------------------|
| `EVENT_PART_RECEIVED` | material/product tracking — arrival at resource (StationPath) |
| `EVENT_PART_PROCESSING_STARTED` | production-response start |
| `EVENT_PART_PROCESSED` | production response + quality (Verdict, ReasonCode, genealogy) |
| `EVENT_PART_PROCESSING_ABORTED` | production response — aborted, with reason |

Each payload carries `StationPath` (§4.8), `Uid`, the synchronized `Stamp` (§2.7), `Verdict`, and `ReasonCode` (§8.8) — a self-describing, reason-coded record an ISA-95/B2MML MES consumes without a bespoke driver. Commands **into** the cell (work order, expected Uid) arrive through the recipe/type path (§3.8) and are treated as untrusted input (§14).

---

## E.5 Genealogy

A consumed component (e.g. a sub-assembly scanned at a feeder) is appended to `Parents` before `EVENT_PART_PROCESSED`, so the production response carries the as-built genealogy:

```iecst
_part.Parents[1] := _componentScan.Uid;   // built-into-this part
```

---

## E.6 HMI (§3.13)

```
InfeedUnit   mode: AUTO ▾   State ● BUSY
  part: VIN-…7F3   ● NOK · "ClampStation.CylB: cylinder did not reach extended"
```

| View | Binding |
|------|---------|
| **Tile** | live part `Uid`; `Present`; **verdict LED** ← `Result.Verdict`. |
| **Detail** | result record (`Records`), genealogy (`Parents`), and the `ReasonCode` line — the same sentence the diagnostic walk shows; drill-through to the offending child (`ClampStation.CylB`). |

---

## E.7 What this annex demonstrated

- A **source-agnostic part carrier** (`I_PartCarrier`) mirroring the recipe provider — RFID/Data-Matrix/host as configuration (§3.16).
- The **four canonical lifecycle events** raised at fixed mode-chain points, with carrier write-back **before** "processed" (§3.16).
- **NOK reuses the machine's first-out reason** — one vocabulary for faults and rejects, one sentence on HMI and MES (§8.8, §6.9).
- A **fixed host-event set mapped to ISA-95** transactions, self-describing and reason-coded, consumable by a B2MML MES (§11.6), with host commands treated as untrusted input (§14).

---

*End of Annex E (draft).*
