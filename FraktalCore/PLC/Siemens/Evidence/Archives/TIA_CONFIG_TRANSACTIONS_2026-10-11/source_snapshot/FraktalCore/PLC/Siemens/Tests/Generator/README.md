# Generated contract frames and registry fixture

`tools/fraktal_tia_generate.py` now consumes the shared
`../Declaration/two_root_forest.json`. The one declaration supplies reusable
types, roots, application records, four contract record types, CM leaf HALs,
optional capability masks and authored reactions/dispatch/cyclic regions.
Composite HAL bundles derive from the child tree; wiring is never repeated.

The generator emits dependency-ordered, ASCII/LF source and a replayable
manifest. This sample has24 source files, three reusable FBs and eight module
instances. Core status/timing types, enums, widths, capacities, defaults and
publication flags come from Core DUTs. The S7-1500 map uses LDT and preserves
wide strings. Registry indices are DInt; row0 is reserved. The fixture declares
16 slots for eight instances, independently of the1214C budget.

```powershell
python FraktalCore/PLC/Siemens/tools/fraktal_tia_generate.py FraktalCore/PLC/Siemens/Tests/Declaration/two_root_forest.json --out "$env:TEMP/Fraktal-frames-new"
python FraktalCore/PLC/Siemens/tools/fraktal_tia_generate.py --verify FraktalCore/PLC/Siemens/Tests/Generator/generated
python FraktalCore/PLC/Siemens/tools/tia_lint.py
```

Generated directories are exclusive. Change the declaration, regenerate into a
new directory, then review the replacement. The source gate replays the model
and compares source bytes and metadata; rewriting the manifest hash cannot
legitimize an edited frame. It checks containment, typed HAL wiring, identity
widths and generated regions at this manifest scope. The broader source rules
remain pending for fixtures without declarations and for later generator facets.

Each root has a separate instance DB with direct `Status`, allowing Web API
root discovery and exact `GetInstancePath` identity. `FB_FraktalMain` owns their
unconditional calls; its own DB is not a module. Setup precedes begin/reactions,
children and end. CMs use the measured quiet guard; their derived-data region
still runs every scan. Composites remain unconditional pending full lifecycle
and Unit idle-predicate integration. The cyclic region is post-lifecycle
derived/output work; it is not the full framework OnCyclic hook.

`FRK_Core`, `FRK_Begin` and `FRK_End` are explicit runtime dependencies.
**Boundary/ supplies test-only probes, not a Core runtime library.** The
registry services are generated from one template; they reject bad parent
indices/overflow before array access and disable dispatch on setup failure.
Full initialization diagnostics, generic walks, retention and GRAPH integration
remain future work. Shared command and Unit service tests are separate fixtures
under Tests/Lifecycle and Tests/Unit.

`make_probe.py <new-package> <new-frames>` adds the separate test boundary and
103 runtime assertions. `build.plan` takes project/generated/export variables;
use a copied station. `download.plan` uses the existing guarded S12 runner and
only169.254.212.49 on the virtual adapter with zero physical mappings. First
registration trust is an explicit driver option, never stored in a plan.
`verify_exports.py` checks exact canonical code, member classes/types and access
flags; `prepare_roundtrip.py` orders native source for reimport.

The2026-10-10 station/image belongs to
`%LOCALAPPDATA%\Fraktal\TiaStations\R4_Frame_20261010\FrkS12\FrkS12.ap20`.
Original DTL and LDT stations remain preserved. This fixture passes103/103
runtime assertions, native public reads/private exclusions and STOP/RUN setup;
see [evidence](../../../../../Specification/Siemens/Evidence/TIA_R4_FRAME_REGISTRY_2026-10-10.md).


Generator0.2 also latches ParCmd, assembles management-before-abort order and
includes the shared command kernel with --shared-runtime. That mode requires
command catalogs and ParCfg TIME timeout members on all types. This Boundary
fixture stays a structural/order probe; Tests/Lifecycle supplies the actual
kernel integration tests. Generator0.3 also accepts a Unit mode profile and
assembles the shared mailbox, mode, recursive release and local Part services.
The current saved FrkS12 image belongs to
TiaStations/Unit_Runtime_20261011/FrkS12/FrkS12.ap20; Tests/Unit documents its
103 native API checks and remaining scope.


The subsequent generator0.4 nested Unit/manual bench passes120 native checks
and104-block/40-interface canonical reimport. Current saved FrkS12 image:
TiaStations/Routing_Runtime_20261011/FrkS12/FrkS12.ap20. Previous Unit/lifecycle/type
projects remain preserved. Full native HMI rendering and Core services remain open.

Generator0.7 adds the [state/alarm fixture](../StateAlarm/README.md). Unconditional
FRK_State calls in the derived `cyclic` region declare bounded unique literal
indices/keys; the generator supplies context and allocates state facets only on
consuming types. Unit frames own alarm sweep/capture/reset assembly. Projects may
raise/gone/message events but cannot write published authority or invoke assembly.
Optional top-level `event_sink: "F_ProjectEventSink"` requires a separate composition
function taking `Ev : ST_AlarmEvent` as input; it is a generated external dependency.
Omitting it emits no callback dependency. The composition root controls private
SinkEnabled. No durable adapter or retained log is implied by this seam.

Generator 0.8 adds [station config and model config](../Config/README.md).
Declare `station_config` and the typed `config` member/key/revision metadata on
each consuming type; declare the offered models and initial model in the
top-level `model_config`. One definition generates the manifest, typed writer,
restore and model transaction participants. The generator owns staging and
assembly; project code supplies no extra call for correctness. The current
scalar/local-retain prototype and its remaining scope are recorded in the
[dated evidence](../../../../../Specification/Siemens/Evidence/TIA_CONFIG_TRANSACTIONS_2026-10-11.md).
