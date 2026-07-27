# Pneumatic press reference example

Status: non-normative worked example of the normative Core contracts. The executable TwinCAT
application is `FraktalCore/PLC/Fraktal_Press_Demo`; reusable device types live in `Fraktal_Modules`.
The concrete Unit, sequences, and station release policy live in the application project.

## 1. Objective and module tree

The example is deliberately built from small reusable capabilities. One root
`FB_PressDemoUnit` owns:

```text
PneumaticPress                         FB_PressDemoUnit (project Unit)
├── PressRam                           FB_CylinderCM (CM)
├── Door                               FB_CylinderCM (CM)
├── PartSlide                          FB_CylinderCM (CM)
├── TwoHand                            FB_TwoHandStartCM (read-only/start CM)
├── PneumaticPower                     FB_PowerGroupCM (CM)
├── PartPresentSensor                  FB_DigitalInputCM (CM)
└── AirPressureMonitor                 FB_AirPressureMonitorCM (CM)
```

The HMI discovers this tree through the ordinary module contract. There is no press-specific HMI
screen. All captions, steps, diagnostics, safety descriptions, commands, and interlocks are
localization keys resolved by the HMI catalogs.

## 2. Mechanical rules

The slide's extended position is **inside** the press; retracted is **outside** for loading. The
door's extended position is closed; retracted is open. The following direction-specific conditions
are authored visibly in the project `Release/FB_PressDemoRelease` and injected into each reusable
`FB_CylinderCM`, so typed and manual commands use the same device enforcement:

| Movement | Functional release condition |
|---|---|
| Door close | slide confirmed inside and not moving |
| Door open | permitted |
| Slide inside or outside | door confirmed open and not moving |
| Ram down | door closed, slide inside, certified two-hand alias active, pneumatic power proven |
| Ram up | permitted |

A rejected manual command uses `releaseReportManual(unitPath,targetPath,value)` so the generic HMI
can identify the exact directional condition. These are collision/process interlocks, not certified
safety functions.

## 3. AUTO, HOME, MANUAL, and changeover

The project Unit source mirrors these responsibilities explicitly: `_M_Dispatch` only routes to
`_M_SequenceAuto`, `_M_SequenceHome`, or `_M_SequenceChangeover`. The project sequences under
`01_PneumaticPress/Sequences` own both progression and the real step actions, written as the Core §6.8
ST `CASE _step OF` skeleton. Each `_step` branch visibly contains its Fraktal step/condition record,
child command or wait, timer/decision/result behavior, and transition result. All four extend Core
`FB_SequenceBase`; `FB_UnitBase` supplies the one `I_SequenceHost` implementation, and the chains share
`_retVal : E_StepResult` committed by `M_Advance` at the end of each branch. No project-private host
interface or per-step transition Boolean set is required. `_M_Sequence*` only reset/run the corresponding
chain. This keeps the inherited lifecycle single-sourced while making each application sequence
independently reviewable and replaceable in the TwinCAT tree. A token-only body plus an external
`CASE ActiveStep` is explicitly not used.
AUTO, HOME, and CHANGEOVER all embed the owner-private `FB_PressDemoLoadPosition` for the coherent
ram-up → door-open → slide-outside operation. Its internal branches contain those commands and waits;
the caller supplies a different step-number window, so reuse does not hide mode context from diagnostics
or cycle timing.

AUTO waits for a newly armed two-hand edge, establishes ram-up/door-open, transfers the part inside,
settles, closes the door, presses for the active recipe dwell, retracts, opens, and returns the part
outside. The Unit increments its good counter at end of cycle. Both buttons must be released before a
new safe-result rising edge can create another functional start request. A **physical two-hand edge**
is accepted only with part presence and valid operating air pressure. Operating air is also the Unit's
immediate Start permissive and is enforced from the same report the HMI displays. Part presence and
the two-hand actuation remain AUTO step-100 pending conditions rather than over-gating an HMI Start;
an already-running AUTO sequence can therefore explain live what it is waiting for.

HOME establishes ram up, door open, and slide outside. MANUAL routes the published command catalogs
of the three cylinders through the Unit, preserving access checks, diagnostics, timing, and the same
direction interlocks. Control power is intentionally not exposed through the MANUAL gate.

Changeover uses the Core transactional `SetModel` path. Project engineering data lives in
`FB_PressRecipeCatalog`, which configures the generic `FB_LocalRecipeProvider` and publishes the
finite model catalog through the Unit. The application supplies fallback plus three model recipes
keyed by `PneumaticPressUnit`:

| Model | Press dwell | Transfer settle |
|---|---:|---:|
| ALUMINUM | 300 ms | 80 ms |
| PLASTIC | 650 ms | 120 ms |
| STEEL | 1200 ms | 150 ms |

The project Unit validates bounded times during prepare and commits only after the complete subtree
accepts the model. Invalid or mismatched records fault `RECIPE_INVALID`; partial application is not
allowed. The guided CHANGEOVER sequence then establishes ram-up/door-open/slide-outside and asks the
operator to confirm that tooling and material match the active model. The HMI starts this flow by
selecting CHANGEOVER, applying the selected catalog entry, and starting the sequence; it renders the
published step and decision records generically.

The application tree applies §4.2 ownership-first grouping: the concrete Unit and its `Sequences`,
`Release`, `Recipes`, and `Io` roles are all under `01_PneumaticPress`. `Fraktal_Modules` retains the
reusable device CMs; `00_System` contains only composition and shared/deployment infrastructure.

## 4. Control power and functional safety boundary

Pulse `PneumaticPress.ReqControlOn` or `ReqControlOff`. `FB_UnitBase` consumes the write, applies the
`POWER_CONTROL` access gate, and emits a one-scan coordinator request. This one-Unit example consumes
the request locally and commands `PneumaticPower`; a multiple-Unit cage would route the same pulses to
one shared control-domain coordinator.

The simulation also exposes ordinary local `SimControlOnButton` / `SimControlOffButton` inputs. Their
rising edges use the application-only `RequestLocalControl` method; Off wins if both occur. This local
seam is intentionally not OPC UA data and is not a safety channel. A shared-domain deployment maps
physical buttons to its single coordinator rather than to every member Unit.

`MAIN` contains simulation controls for a normally closed E-stop circuit, the two physical buttons,
fieldbus health, and a safety-valve result. Names beginning `Safe` represent aliases produced by a
certified safety application in a real machine. The ordinary PLC does not calculate two-hand
simultaneity, anti-tie-down, PL/SIL, guard locking, safety reset, or safe output switching.

For virtual commissioning, the simulated safety layer is the final writer before the plant model:
loss of pneumatic power removes all cylinder requests, and ram-down is independently removed unless
the guard is closed and the evaluated two-hand result is active. Ram-up and the assessed low-risk
loading axes remain available. This zoning is an example only; the machine risk assessment determines
the real safe valve/island mapping and must be validated in TwinSAFE/FSoE.

No power or cycle request is replayed after E-stop, fieldbus, safety-permit, or HMI communication
recovery. A deliberate Control On and a new two-hand actuation are required.

## 5. Run styles, traceability, rationalization, and access

**Run styles (§3.4.2).** The Unit advertises CONTINUOUS, SINGLE_STEP, and HOLD_TO_RUN. Every motion
boundary in AUTO, HOME, and CHANGEOVER passes through `_M_StepGate`, so the HMI step toggle paces the
sequence one commanded motion at a time; the transfer-settle and press-dwell timers are process steps
and run through. Pacing is NON-SAFETY — the direction interlocks and the certified safety layer are
unaffected.

**Part traceability (§3.16).** `MAIN` injects the shipped `FB_LocalPartCarrier` (BY_POSITION:
station-local serials `PRESS-2026-<n>`). The AUTO chain raises the four canonical lifecycle events:
RECEIVED when the start conditions confirm a present part, PROCESSING_STARTED when the transfer
begins, PROCESSED (verdict OK, with the applied dwell as a measured record) after the completed
cycle — the result is written to the carrier before the event — and PROCESSING_ABORTED on abort or
fault while a part is present (raised automatically by the Unit base on ERROR entry). The live
context is published as `Part : ST_PartContext`; produced results accumulate in the carrier's
bounded ring. An RFID/DataMatrix/host carrier substitutes behind `I_PartCarrier` without touching
the sequence.

**Alarm rationalization (§8.9).** The application registers operator action + consequence metadata
for its main reasons (interlock dropped, air pressure lost, invalid recipe, cylinder position
timeouts) so the HMI alarm rows state what to do, not only what happened.

**Access (§7.7).** Commissioning users `operator`/`1111`, `tech`/`2222`, `admin`/`9999` are
registered through the persistent `FB_LocalAccessProvider`. The shipped policy remains fully open;
raising per-action thresholds is station configuration done from the HMI (gated by ACCESS_POLICY).

## 6. Commissioning and tests

Build/install `Fraktal_Core`, then `Fraktal_Modules`; add
`Fraktal_Press_Demo/Fraktal_Press_Demo.plcproj` as an executable PLC application. The application
README lists the simulation controls. `Fraktal_Tests` adds coverage for:

- direction interlocks on the normal typed-command path;
- two-hand release-before-rearm and one-pulse behavior;
- Start-release/report equivalence for the operating-air entry permissive;
- transactional press model changeover;
- an AUTO cycle returning through the shared load-position sub-sequence.

Before physical commissioning, replace every simulated `Safe*` expression with validated safe-I/O
aliases, verify output ownership and valve zoning, perform the required safety validation, and archive
the safety checksum and test evidence with the machine documentation. The supplied CX2030 terminal
mapping and its unresolved electrical/safety items are detailed in `CX2030_PRESS_IO_MAPPING.md`.
