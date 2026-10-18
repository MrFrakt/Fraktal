# Annex F — Worked Example: PackML / OPC UA Line-Coordination Profile

*Companion to **Fraktal Core** (Part I) exercised through the **Fraktal/TC3** binding (Part II); slots under Core §12.*
*Core concepts demonstrated: PackML projection of the native state/mode model (§11.7, §6.6, §3.4), Admin group from §8/§8.11 contracts. / TC3 mechanics used: OPC UA server exposure of the `PackMLObjects` folder (TC3 §11.1).*
*Reference implementation — illustrative, not compile-tested; validate against the pinned TwinCAT version and the OPC 30050 companion model.*

This annex projects the Annex C `InfeedUnit` onto the **PackML profile** (§11.7) — the OMAC state machine and PackTags exposed over OPC UA (OPC 30050) — so a line controller coordinates the cell with **no bespoke driver**, while the native `ExecState`/mode model (§6.1, §3.4) stays the internal source of truth. The point: PackML here is a **projection of contracts the standard already has** (state, modes, alarms, counters), not new logic.

```
Line controller ──OPC UA (PackTags)──▶ InfeedUnit/PackMLObjects
                                          │  Command / Status / Administration
                                          ▼
                                   FB_PackMLAdapter  ──reads/calls──▶ FB_InfeedUnit (Annex C)
```

---

## F.1 State-machine mapping (§11.7.1)

The adapter derives the PackML state every scan from the Unit's native execution state and its Stop/Hold/Abort/suspend conditions:

```iecst
METHOD PRIVATE _M_MapState : E_PackMLState
    IF _unit.FaultActive THEN
        _M_MapState := SEL(_clearing, E_PackMLState.Aborting, E_PackMLState.Clearing);  // → Aborted between
    ELSIF _unit.Blocked OR _unit.Starved THEN                                            // §8.11
        _M_MapState := E_PackMLState.Suspended;
    ELSE
        CASE _unit.State OF      // E_ExecState (§6.1)
            E_ExecState.READY:  _M_MapState := E_PackMLState.Idle;
            E_ExecState.BUSY:   _M_MapState := SEL(_starting, E_PackMLState.Execute, E_PackMLState.Starting);
            E_ExecState.DONE:   _M_MapState := E_PackMLState.Complete;     // via Completing
            E_ExecState.ERROR:  _M_MapState := E_PackMLState.Aborted;
            E_ExecState.ABORTED:_M_MapState := E_PackMLState.Stopped;      // via Stopping
        END_CASE
    END_IF
```

| Native (§6.1/§8.2/§8.11) | PackML state |
|--------------------------|--------------|
| READY/idle → Start | `Idle` → `Starting` → `Execute` |
| BUSY cycling | `Execute` |
| Stop-after-cycle (`OnModeExit`, §3.14) | `Completing` → `Complete` / `Stopping` → `Stopped` |
| Hold (§6) | `Holding` → `Held` → `Unholding` |
| Blocked/Starved (§8.11) | `Suspending` → `Suspended` |
| Fault hold (§8.2) | `Aborting` → `Aborted` → `Clearing` |

---

## F.2 Unit-mode mapping & methods (§11.7.2)

`SetUnitMode` / `SetMachSpeed` map onto the native `SetMode` (§3.3) and recipe speed; an unsupported mode reuses the graceful rejection of §3.7:

```iecst
METHOD SetUnitMode : BOOL
VAR_INPUT UnitMode : E_PackMLMode; END_VAR
    SetUnitMode := _unit.SetMode(_M_ToNativeMode(UnitMode));   // FALSE if _M_Supports() = FALSE (§3.7)

// E_Mode → PackML Unit Mode:  AUTO→Producing · MANUAL→Manual · CHANGEOVER/CALIBRATION/HOME→Maintenance
```

---

## F.3 PackTags — projection, not new logic (§11.7.3)

The three groups are read straight from existing contracts:

```iecst
// ── Command (consumed from the line) ───────────────────────────────
Cmd.UnitMode   →  SetUnitMode(...)            // §3.4
Cmd.CntrlCmd   →  Start / Stop / Hold / Reset / Abort  (§3.3 lifecycle)
Cmd.MachSpeed  →  _unit.SetSpeed(...)         // recipe speed (§3.8)

// ── Status (published to the line) ─────────────────────────────────
Sts.StateCurrent     := _M_MapState();        // F.1
Sts.UnitModeCurrent  := _M_FromNativeMode(_unit.ModeActive);
Sts.MachSpeedActual  := _unit.SpeedActual;

// ── Administration (consumed by higher-level systems) ──────────────
Adm.Alarms[i]        := { _alarm.ReasonCode, _alarm.Description, _alarm.Severity };  // §8, §8.8
Adm.StopReason       := _unit.GetFaultSummary().Description;                          // first-out (§6.9)
Adm.ProdProcessedCount := _stationMon.GoodCount + _stationMon.NokCount;               // §8.11
Adm.ProdDefectiveCount := _stationMon.NokCount;                                       // §8.11
Adm.AccTimeSinceReset  := _stationMon.AccTime;
```

The Admin group is precisely where the §8 alarms, the §6.9 first-out stop reason, and the §8.11 counters surface to OEE/line systems — no values are invented for PackML.

---

## F.4 Coexistence & exposure (§11.7.4)

The adapter is exposed in a `PackMLObjects` folder on the cell's OPC UA server (§11.1); the native interface and the ISA-95 host events (§11.6, Annex E) are unaffected and run alongside. A line controller issuing `CntrlCmd := Start` with `UnitMode := Producing` drives the cell through `SetUnitMode`→`SetMode(AUTO)` and `Start`→native `Start` (§3.3) — the AUTO chain of Annex C runs unchanged, and the line reads `Execute`, then live counters, then on a clamp fault sees `Aborted` with `StopReason = "ClampStation.CylB: cylinder did not reach extended"`.

---

## F.5 What this annex demonstrated

- The native model **projected** onto the full PackML state machine and PackTag groups (Command/Status/Admin) — a conformance option (§11.7), not a rewrite.
- `SetUnitMode`/`SetMachSpeed` mapped onto `SetMode`/recipe, reusing **graceful mode rejection** (§3.7).
- The **Admin group sourced from existing contracts** — §8 alarms, §6.9 first-out reason, §8.11 counters — so PackML adds an interface, not logic.
- **Coexistence**: PackML, ISA-95 host events (Annex E), and the native control interface on one server, over the same browse paths (§4.8).

---

*End of Annex F (draft).*
