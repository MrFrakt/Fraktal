# Phase 6 — HMI time-type filters

The owner's requested pause before further Phase 6 work adds time-type filtering
to the generic cycle trend and step Pareto, matching Gantt. Selectable chips cover
Work, Wait upstream, Wait downstream, Wait operator and Wait external when those
classes occur. One shared component owns chip selection, Show all and pruning of
disappeared classes. The three charts retain independent presentation selections;
module-path keys prevent selection from leaking to another Unit.

Filtering removes the selected classes from the chart and rescales its visible
data. Gantt keeps the original start offsets and full-cycle header. Trend keeps
the full-cycle readout, adds the selected-class total as Shown, and omits the
full-cycle best line while filtered. Pareto uses the greatest visible Maximum
for its axis, including when that row has a smaller Avg. Empty selections remain
recoverable through their chips/Show all. Command timing records have no time
class; no work/wait classification is invented for them.

## Validation

- Full HMI suite: 469 passing tests, seven expected skips. The final focused run
  passes 18 tests: eleven existing Gantt checks and seven new filter checks,
  including the additional zero-time history case.
- Rendered-pixel checks prove that hidden trend classes disappear and the
  surviving Work series expands. Widget checks prove Pareto rescaling, unchanged
  aggregates, Show all, all-hidden recovery and selection behavior on refresh.
- Flutter analyzer: no issues. Release Web build and Wasm dry run pass.
- AB tool discovery: 1,535 tests pass. Root consistency: zero errors/warnings;
  root consistency suite: 33 tests pass.
- HTTPS at `https://press.localhost/`: `main.dart.js`, `flutter_bootstrap.js` and
  `index.html` return 200 and match the staged release bytes. TLS host validation
  uses the trusted local certificate for `press.localhost` over loopback TCP.

The served `main.dart.js` SHA-256 is
`BEA7E435570A1CE2827933A0F641A19DA4E3C4EB8CDBF50518CD88B71D8027EC`.
Release output: `C:/work/press68_time_filters_web`. Previous release backup:
`C:/work/press68_time_filters_web_backup_01`. Deployment record:
`C:/work/press68_time_filters_deployment_01.json`. Validation logs use the
`C:/work/press68_time_filters_*_01.log` prefix.

This is a software UI change with zero PLC source/data-memory growth. Press68
remains the downloaded controller build. The agent performed no controller
writes, download, power cycle or gateway restart. Chrome interaction was not
available to the agent; browser acceptance follows the owner's hard refresh.

The owner's separate power-cycle/admin-login observation is recorded in
[credential retention evidence](AB_PHASE6_OWNER_CREDENTIAL_RETENTION_2026-10-03.md).
