# Phase 6 — matching timing-legend action height

The owner reported that Show all was taller than the time-type legend chips,
changing the card height when it appeared. The shared timing-chart legend now
renders Show all as an ActionChip with the same label typography as its
FilterChips. Chip geometry comes from the existing theme for all three charts.

The existing Flutter capture harness measured 48 px for both controls and
48 px for the legend row before/after Show all appeared, at compact, medium and
large control settings. The capture confirms matching painted heights. Geometry
record: `C:/work/press68_legend_size_geometry.json`. The 29 existing chart and
control-scale tests pass; Flutter analyzer is clean; release Web build and Wasm
dry run pass. Root consistency reports zero errors/warnings and 33 tests pass.
The handover's AB regression gate also passes all 1,535 tests.

The update is served at `https://press.localhost/`. Trusted HTTPS checks return
200 and exact release bytes for the main script, bootstrap and index. Served
`main.dart.js` SHA-256:
`9E3854ABBFF8326D04A1B052DC2EB5BA8E0409453C50C45C9C328ADF34C8BFB5`.
Deployment record: `C:/work/press68_legend_size_deployment_01.json`; previous Web
release backup: `C:/work/press68_legend_size_web_backup_01`. No controller writes,
download, power cycle or gateway restart occurred.
