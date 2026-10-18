# Press with the Line profile

This isolated integration fixture uses the saved offline press project and the
reserved unmapped CPU1516 at `.56`. The original Fraktal and physical 1214C are
outside its target profile. Compile/import/read-back finishes before hosting
the simulator; `run_live.py` downloads once and always closes that test CPU.

The press composition declares `line_config` beside its station/model config.
The shared `calendar_contract` helper derives flat V3 calendar fields, bounds,
canonical keys and localization labels from the Core row capacity. The same
helper is used by the operations fixture. The Line engine owns defaults,
validation, revision, named sets and persistence. Main remains a calling routine;
projects add no per-scan Line wiring.

The live probe checks complete root-scoped LINE_CFG discovery, ordinary writes,
calendar overlap refusal, atomic named Line sets/current export, coexistence
with model activation, actual restart and unchanged original-instance state.
It reads both configured and active values: changing a calendar target changes
future config while the current interval keeps its latched target (Core §8.5.2).
Afterward the existing HOME/CHANGEOVER GRAPH jump and pacing checks run against
the same deployed press.

Normal declaration admission requires the complete V3 calendar and production
accounting on every referencing root. Mirror declarations require a bound
`F_` image provider. The explicit `line_workbench` API remains available for
partial engine experiments; its marker is emitted only when actually requested.
The provider's transport remains a deployment choice. OUC TCP is the separately
selected P12 implementation and is not supplied by a synthetic test provider.
