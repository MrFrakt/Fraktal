# PROFINET node health

`make_fixture.py` checks Part IV §10.5 node health against the CPU's own
PROFINET view. Its project carries one IO system with an ET 200SP (`IM_1`, a DQ
module `PnDQ` at slot 1) and a central DQ module (`DQ_1`); `HARDWARE` lists the
driver lines, which the gate passes to `compile_fresh` after the CPU exists.
The ET 200SP server module is added after the last module and nothing may
follow it, so I/O modules are plugged from slot 1.

The suite runs across scans, eight assertions:

1. the device the CPU reports present makes its node `OPERATIONAL` and its
   input good;
2. its present module (`ModuleStates`, slot from `LOG2GEO`) is `OPERATIONAL`;
3. `D_ACT_DP` disables the device from the program;
4. the next sample (at most every 250 ms) takes the node and its input `OFFLINE`;
5. the module is `OFFLINE` with its device;
6. `D_ACT_DP` re-enables it;
7. the node returns to `OPERATIONAL` within a bounded wait;
8. and its module with it.

Device numbers and slots come from the hardware identifiers (`LOG2GEO`), so
the declaration names the hardware constants only. `FB_ProfinetTest.LedReturn`
records what the `LED` instruction reports for STOP/RUN, ERROR and MAINT; it
asserts nothing and serves the force-job detection spike.

Reserved bench `FrkProfinetTest`, `169.254.212.58`, unmapped. A real station
failure (OB86) is injected only from the host through the simulator API
(`RackOrStationFaultEvent`), which this autonomous suite does not use.
