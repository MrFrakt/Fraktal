# Shared sequence view, 2026-10-13

This report records generator 0.16 on TIA V20 and S7-PLCSIM Advanced V7, simulated
CPU1516 instance Fraktal. It is evidence for the draft binding, not a declaration
that the entire Siemens port is complete.

The Core 3.13 types remain unchanged. Optional `sequence_view` capacities allocate
definitions, per-leg cursors, PLC-owned history and sparse annotations only for
deployed consumers. A private consumed-size pool owns the work; the Unit frame
publishes readonly mirrors and supplies the config manifest's static definitions.
The pool breaks the native dependency cycle between GRAPH helpers and a root FB
that cannot compile until its GRAPH adapter exists. No application scheduling
call is added. Committed mode changes clear the chart; same-mode visits keep
history. Deeper sub-chain cursors take priority over their composite parent.

Sequence helpers record visits/waits and diagnostic annotations. Row flags remain
authoritative if the sparse note table fills. Warning notes clear on a new visit;
error notes clear on an authorized operator reset. Guards can update from config
and advance the manifest revision after the Core quiet interval. Working arrays
and static definitions are private; published tables/counts/cursors are readonly.

The wired press declares 23 rows, two parallel legs and four annotation slots.
The load-position sub-chain projects local 240/260/280/300 to 600/620/640/660 via
one declared offset. Main GRAPH numbers and transitions are preserved. This
avoids collisions with main 240 and parallel demonstration 300. GRAPH/ST remain
wired; optional ST/LAD twins are uninstantiated; MAIN remains three calls.

The native synthetic fixture passed **122/122 checks** through the pinned Web API.
It exercises the direct view services and actual sequence helpers, fast history,
main/per-leg clocks, dynamic guards, static manifest facets, no revision churn,
sub-chain priority, slot reuse/overflow, row bounds, reset, mode change, root and
nested isolation, privacy/readonly access, and STOP/RUN. The reset test raises a
real blocking occurrence before requesting OPERATOR_RESET, preserving the shared
release gate. No physical press movement is exercised.

Runtime compile: **0 errors, 0 warnings**. The separate press passes both compile
stages at **0/0**. Native readback matches **19 AUTO + 4 HOME GRAPH steps** and
**161 LAD networks / 155 calls**. The final press package replays **168 sources**;
the default structural package replays **24 sources**. Tool suite: **183 tests**;
cross-artifact suite: **35 tests**. Shipped source lint and consistency pass.

Failed raw attempts are retained. They include rejected time literals in LAD
import, a fixed-array UPPER_BOUND rejected by SCL, the initial root-FB dependency
cycle, and using LinkPath instead of Core ST_Diagnostic.SourcePath. The final LAD
uses a private typed zero-time operand; fixed condition bounds derive from Core.
Harness corrections include the Core reset request name, authentication/reset
eligibility, and waiting for the latest metadata change's revision. Lint now gets
the published view members from the generator's own map. That Python refactor
leaves every compiled press source byte-identical, checked in the archive.

Current runtime: `%LOCALAPPDATA%/Fraktal/TiaStations/Sequence_View_Runtime_20261013/FrkS12/FrkS12.ap20`.
Current offline press: `Sequence_View_Press_Offline_20261013/FrkS12/FrkS12.ap20`
under the same station directory. The runtime fixture uses LOCAL_RETAIN config;
the offline press combines the view with selected LOAD_DB. Earlier persistence
projects and [903-check consumer evidence](TIA_PERSIST_MEDIUM_2026-10-13.md) are
preserved; those regressions were not rerun on this sequence fixture.

Final owner read verifies RUN, physical mappings zero, both roots MANUAL/READY,
logged out, empty charts, no blocking alarm and no pending/failed config commit.
Keeper PID12728 and the approved driver are preserved.

Remaining work includes native generic-HMI table hydration/rendering, combined
LOAD_DB restore-barrier publication, complete diagnostic walks/stall reporting
and profiling, provider/line-config facets, module/HAL expansion and deployment
acceptance. Physical/torn-write/endurance and changed-layout/full-download gates
remain separate. No native HMI claim is inferred from PLC compilation or existing
mapper support.

[Immutable raw archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_SEQUENCE_VIEW_2026-10-13/)
and [SHA256SUMS](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_SEQUENCE_VIEW_2026-10-13/SHA256SUMS)
bind attempts, native exports, packages, source snapshots, JUnit, owner facts and
gate results. Older reports and sealed archives are unchanged.
