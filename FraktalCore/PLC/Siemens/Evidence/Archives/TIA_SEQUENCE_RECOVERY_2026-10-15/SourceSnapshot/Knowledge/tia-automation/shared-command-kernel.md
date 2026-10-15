# Shared Fraktal/TIA command kernel (2026-10-10)

Scope: TIA V20, simulated1516-3 V3.0, Advanced7/API5 compatibility shim.
Evidence: C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_CORE_LIFECYCLE_2026-10-10.md.

- **[measured]** Generator0.2 --shared-runtime emits27 sources, including the
  actual shared Framework/Core kernel. The test package adds4 sources and
  replaces OB1 only for fixture reset/clock injection/assertions.55 cases,
  238 assertions pass after full download and after guarded STOP/RUN. Test
  resets do not establish production retention/restart policy.
- **[measured]** Command ids/labels and a ParCfg TIME timeout are declared once;
  every runtime type requires them. The frame latches ParCmd, validates and
  tags the accepted command, then invokes CommandStart. Init precedes it;
  management and child calls precede abort routing; dispatch uses the latch.
  Frame replay rejects changed kernel bytes even when their hash is rewritten.
- **[measured]** Dropping Execute during BUSY does not cancel. A terminal reached
  with Execute already low is visible for one call and resets next call.
  Same-call completion closes a zero-ms timing row. Command terminals reset
  on Execute drop; non-command faults latch and retry on a fresh command edge.
- **[measured]** Abort is a level while BUSY: already-high Abort cancels a new
  command. Error-abort is an edge of Abort AND ERROR; it keeps ERROR latched.
  Abort while HELD clears Held and withdraws the test output.
- **[measured]** HELD beyond the configured100ms stays BUSY/LOW, preserves Since
  and resumes without reset. Active progress timeout excludes held/release
  intervals; wall-clock timing includes them (2010ms in this fixture).
- **[measured]** Pending timeout preserves original path/text/I/O/time/quality;
  severity/category follow reason_rationalization.json. PERMISSIVE_NOT_MET
  remains LOW even when timeout changes command state to ERROR. A test that
  expected MED failed211/212 before correction; do not duplicate priority policy.
  An unregistered project reason defaults to MED. Fault adoption is verbatim.
- **[measured]** UDInt clock rollover gives10ms; command rows update once
  and use Core MAX_CMD_STATS. The compiled source guards positive TIME overflow
  and count saturation; extreme-value runtime controls remain unmeasured. Integer incremental
  averaging matches the Core algorithm; this is not exact arithmetic mean.
- **[measured]** A CM with declared Cyclic management takes the full path every
  scan. A CM without it retains the prior quiet guard. The older lowercase
  cyclic region remains unconditional derived/output work after status.
- **[measured]** Native public100/private7 reads pass original pin and mask24;
  latched parameters, Core, Device state, HAL, registry, clock and fixture defaults are private.
  47 blocks/18 interfaces compare to native export and ordered reimport/export.
- **[measured]** TIA moves inline DB variable initialization into BEGIN in its
  source export. The fixture moved -1 setup to Initial_Call; no canonical ignore
  rule was added. A retry before the driver had exited hit the project lock.
  Await process completion, not merely the plan-complete log, before reopening.

The production RUNTIME clock runs after deterministic cases; RD_SYS_T stamps
LDT with TimeSynchronized FALSE. No UTC quality/hardware drift claim follows.
Current saved image/project:
%LOCALAPPDATA%/Fraktal/TiaStations/Core_Lifecycle_20261010/FrkS12/FrkS12.ap20.
Older projects, DPAPI secret and pin/certificates are preserved. No physical CPU
changes or driver rebuild. Full Unit mode/mailbox/Part, generic capability/
rollup selection, alarms/state flags/recipes, retention, GRAPH integration and
native HMI rendering/commands remain subsequent work; press excludes power control.

- **[measured]** Software's initial9 own-OutImm-read warnings were caught during
  final log review; driver success had been misreported as warning-free. Declared
  private Device storage now holds test state and publishes OutImm without reads
  of output parameters. Both software/hardware compiler events explicitly report
  0 errors/0 warnings. The generator rejects own-output reads before import.

- **[measured]** run_plan.py --require-clean-compile checks every compile event
  and rejects any warning/error or an absent compiler result. Its regression
  control rejects software9 warnings followed by hardware0/0.108 tool tests pass.
