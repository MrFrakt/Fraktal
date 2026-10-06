# Press75 time-filter navigation follow-up - 2026-10-05

The owner reported a silent return to the plant overview while changing
time-type filters, after confirming two minutes of idle-view stability in the
[earlier cycle-detail record](AB_PRESS75_HMI_CYCLE_DETAIL_2026-10-05.md).
This follow-up preserves that earlier result and records the additional defect.

## Reproduced path and correction

The full-bootstrap regression switches off all six choices across cycle trend,
Gantt and Pareto, withdraws the forest on STALE and restores it on LIVE before
the next painted frame. Before the correction, AppState sets showOverview=true
on the empty forest. This exactly reproduces the silent navigation reset.
With the correction, the unit path and local tree scope survive; the same
mounted tab controller and all filters remain selected after recovery.

Only navigation intent survives withdrawal. The forest is empty, the selected
module is unavailable, session level is NONE and detail demand is deactivated.
A sustained loss still removes the interactive shell and shows the connection
page. A populated replacement forest that no longer contains the selected
module still resets selection to the overview. Good/expiry limits and PLC
permissions are unchanged. The owner browser console was unavailable, so this
is a demonstrated reset mechanism, not an independently captured filter-specific
transport failure on Chrome.

## Validation and deployment

- Machine record: [AB_PRESS75_HMI_FILTER_NAVIGATION_2026-10-05.json](AB_PRESS75_HMI_FILTER_NAVIGATION_2026-10-05.json), SHA-256 B77A7B1C6F7CE5D58A62E2CA975CD27C3A328B41E301174FA11147E7A9507EF8.
- Baseline regression fails on showOverview=true; corrected focused suite
  passes 47 tests. Three new tests cover sub-frame recovery, sustained loss and
  an actually removed selection.
- Full HMI: 524 pass, seven deployment-gated skips. Analyzer is clean; web
  release passes. Root consistency has zero errors/warnings.
- Published HTTPS assets match the staged release at https://press.localhost/.
  Main JavaScript SHA-256 DB20AC81DAE12603150055A4746BD082783B1828CD53C027CDCA74D52FB86616.
  Previous assets are retained at C:/work/press75_filter_navigation_web_backup_01.
- No gateway restart, PLC source/generator change, download or memory growth
  is required. Press75 remains loaded with the identity in the machine record.

The additional live widget harness failed before its filter loop when a sample
expired; its real-zone retry stalled and was cancelled. Neither is an automated
live filter PASS. Browser tools exposed no Chrome surface. Owner filter
acceptance was requested after publication and is pending when this record is
created. The earlier two-reader/idle-view production result remains scoped to
the earlier repair. Safe inert QUERY_CONFIG reads were the only permitted native
transactions; anonymous NONE cleanup remained refused. No operator mutation was
performed and no write-enabled gateway was started by the agent.

The shared HMI contract, AB guide and TC3 handoff document this navigation rule.
The remaining AB port and physical/other-target acceptance remain separate work.
