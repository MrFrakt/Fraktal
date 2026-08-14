# Nexeed reference insights for Fraktal

Status: non-normative architecture comparison. The reviewed source is the local
`NexeedReferenceOnly/REF1_Plc.xml` export. This document records structural observations and Fraktal
decisions; it does not reproduce vendor code, define Nexeed behavior, or claim compatibility.

## 1. Objective filter

Patterns are adopted only when they advance the Part I §1.1 objectives—especially low application
effort (O1), learnability (O2), diagnosability (O3), recursive reuse (O4), safety separation (O7),
and platform neutrality (O8). Familiarity with another standard is useful orientation, but it is not
a reason to add a second lifecycle or vendor-specific abstraction to Fraktal.

## 2. What the reviewed program makes clear

### Ownership-first grouping

The export groups application logic below physical/location owners such as a station and its
`Loc...` equipment branches. An owner's primary objects, chains, data, parameters, and add-ons remain
near that owner. This is easier to navigate than an application-wide bucket containing every POU or
every sequence, and it validates Fraktal §4.2's instance-tree layout.

Fraktal adapts this as:

- `00_System` for the composition root and shared infrastructure;
- one numbered branch per peer root Unit;
- child Units/EMs/CMs nested by physical ownership;
- role folders such as `Sequences/Mode|Sub`, `Release`, `Recipes`, and `Io` only inside that owner;
- reusable CM/EM/device implementations kept in reusable libraries, while a deployed Unit's concrete
  modes and cross-module release policy remain visible and replaceable in its application branch.

### Three useful sequence roles

The reference distinguishes station mode chains (`SqM`), finite command chains (`SqC`), and shared
subchains (`SqS`). Fraktal uses the same conceptual separation without importing its boilerplate:

| Reference orientation | Fraktal role | Fraktal ownership |
|---|---|---|
| `SqM_<Owner>_<Mode>` | native mode SFC with real logic in each `Nxxx` action | Unit; continuous until Stop |
| `SqC_<Owner>_<Command>` | EM/CM command dispatch/chain | Module; public only through §6.1 |
| `SqS_<Owner>_<Operation>` | owner-private SFC (default) or justified `_M_Seq<Operation>` ST chain | Private to one owner; no OPC UA identity |

The reviewed chains reinforce explicit init/finish states, stable step identities, error/cancel
routing, and reuse of coherent motion chains. Fraktal obtains those outcomes through the inherited
lifecycle and §6.5 step record rather than repeating state/output/error boilerplate in every step.
The reference's useful lesson is stronger than token ownership: its `Nxxx_active` bodies visibly contain
the command, wait, decision, or result logic for that step. Fraktal's default SFC+ST form follows that
shape. Each sequence step also calls the Fraktal step/condition contract; the Unit adapter only runs
the chart and bridges protected framework services, while `OnCommandStart` owns its one-shot reset.
A token-only SFC plus an external `CASE ActiveStep`
does not satisfy this pattern. The press HOME, CHANGEOVER, and AUTO charts are the concrete reference.

### Layered releases

The reference commonly derives each manual function release as a shared station/manual release AND
function-specific conditions, and defines explicit release logic for each station mode. That layering
is valuable because mode entry, common manual authority, and a direction-specific device action are
different questions.

Fraktal strengthens the pattern for O3: a common Boolean is never enough. Each constituent condition
retains its qualified owner path, localization key, reason, and bypass policy in the release report;
the action consumes
the same `ST_ReleaseReport.Released` predicate the HMI displays. Future sequence waits are step
conditions, not blanket Start blockers.

## 3. Patterns deliberately not imported

| Observed pattern | Fraktal decision |
|---|---|
| Separate `<X>Unit` + `<X>Extension` objects | Use one concrete tier subclass plus §3.14 hooks; lifecycle stays single-sourced. |
| Add-on object per optional concern | Use a narrow interface/provider/event sink when the concern is independently replaceable; otherwise use the owner hook. |
| Repeated per-step action/transition/error wrappers | Keep application steps lean; the base owns handshake, abort, timeout, state mapping, and diagnostics. |
| Summed release Boolean with no condition provenance | Keep every failed condition record and aggregate reports recursively. |
| Direct station-global or raw-I/O reads inside reusable release logic | Consume HAL or explicit semantic child/domain status; the application composition root owns raw mapping. |
| PLC logic deciding HMI button visibility | Publish capability, access, and release data; the generic HMI derives presentation. |
| Ordinary PLC enabling guard bridging/muting | Publish conspicuous read-only safety status and untrusted requests only; certified safety owns the grant (§9.8). |

## 4. Press-demo application of the findings

The press remains one root Unit with reusable cylinder/input/power CMs. Its concrete
`FB_PressDemoUnit`, `Sequences`, `Release`, `Recipes`, and `Io` are owner-grouped under
`01_PneumaticPress`; `00_System` retains only composition, raw I/O/safety aliases, drivers, the
control domain, output authority, and simulation. The Modules library therefore supplies mechanisms,
not a hidden final station program.

`_M_Dispatch` is only a mode router. AUTO, HOME, and CHANGEOVER remain distinct mode chains (ST
`CASE _step OF` on `FB_SequenceBase`, §6.8). Their common ram-up → door-open → slide-outside operation is
one owner-private `FB_PressDemoLoadPosition`; the caller supplies its step-number window so diagnostics
and timing retain mode context. The private chain has no public command surface or module node.

Operating air is an immediate motion-entry permissive for AUTO/HOME/CHANGEOVER, so the project-owned
`FB_PressDemoRelease` exposes one named condition record that is both enforced by `Start()` and returned
by `ReleaseReportStart()`. The same visible Release component evaluates the cross-device collision
permits and appends direction-specific manual release reasons. Part
presence and the two-hand actuation are intentionally not Start permissives: they are future AUTO
step-100 waits and remain visible as live pending conditions while the Unit is running.

## 5. Review checklist

When reviewing a new Fraktal application:

1. Can every file and chain name one structural owner?
2. Is each chain clearly a mode, public module command, or private sub-sequence?
3. If the chain claims native SFC, does each `Nxxx` action visibly contain its real command/wait/decision logic?
4. Does every step-state variable have exactly one writer, with an acyclic call graph?
5. Is repeated coherent motion extracted once without hiding `CurrentStep`?
6. Is an independently commandable/reusable operation promoted to an EM instead of disguised as a subchain?
7. Are common and function/mode-specific releases layered but still individually diagnosable?
8. Does the action consume the exact predicate its release report publishes?
9. Are later-step waits kept out of Start unless they are truly immediate entry/frontier conditions?
10. Are raw I/O, HMI presentation, and certified safety authority kept outside reusable sequence/release logic?
