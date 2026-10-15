# Shared sequence recovery

Core §6.9(d) requires a fault to stop on its raising step. Leaving ERROR rearms
the step's command, delay and event latches. The Unit must accept a deliberate
Start before the chain runs again. The application chooses whether that Start
continues from the retained step or restarts the whole chain.

The generated Unit frame owns private lifecycle epochs for each consumed
sequence-view owner. It captures state before sequence execution and after the
command kernel resolves the scan, including late kernel faults. Sequence
helpers consume those epochs through their existing begin path. MAIN and
project sequences gain no recovery scheduling call. Boot, mode change, both
abort paths and restore quiescence invalidate the retained work.

The GRAPH owner continues shared command-release services while frozen and
withholds the native chart call, preserving the active step. On recovery the
same step reissues its command only after the child's Execute-low reset gap.
Native GRAPH evaluates transitions before the new step actions. Its shared
begin service preserves the preceding active scan's result for that evaluation;
the mandatory step record clears it before the current action decides. Fault,
restart and rearm boundaries discard that result. ST/LD keep their normal
same-scan result handling.
Forced-restart idle scans call GRAPH with OFF_SQ and let INIT_SQ fall before a
new Start, so abort-in-ERROR cannot consume the next reset pulse.
The wired press explicitly restarts on each accepted Start; its optional ST/LD
renditions remain uninstantiated. HELD uses the existing restorable permit and
does not enter this fault-recovery path.

`make_fixture.py` adds a generated three-step GRAPH and simulated child command
to the qualified LOAD_DB/diagnostic/profile bench. Test arguments are copied to
private storage when RequestSeq changes; clients commit that sequence last.
`prepare_plan.py` first compiles the standalone chart with bootstrap Unit frames,
then imports its owner and final frames. `verify_native.py` checks the final
SCL/type/access witnesses and the native GRAPH object. Initialized storage DBs
are excluded from the canonical source witness because native export relocates
their initial values into BEGIN.

`probe_web.py` exercises retained steps, no automatic retry, explicit restart,
command/delay/event rearming, row clearing, the Execute-low interval, HELD,
late kernel faults and both abort paths. Use `Tests/Access/with_credentials.ps1`
and fresh logs. Compile/read back before a separate guarded download, with the
existing approved driver. Preserve the Fraktal simulator and its storage/pin.
The physical press bench is unavailable; its project is compiled offline.

[Qualification](../../../../../Specification/Siemens/Evidence/TIA_SEQUENCE_RECOVERY_2026-10-15.md)
records79 recovery checks and the selected regression/readback scope. `normalize.py`
withdraws committed stimuli, idles both roots and performs a guarded STOP/RUN;
`verify_idle.py` checks45 final values and retained login/logout. The profile
regression starts with fresh volatile statistics because its four-slot test pool
is shared with unrelated synthetic steps.
