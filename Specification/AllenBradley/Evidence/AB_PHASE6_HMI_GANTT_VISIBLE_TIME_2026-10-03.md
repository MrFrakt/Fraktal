# Phase 6 — linear Gantt axis excluding filtered time

The owner clarified that the timescale should remain linear and omit filtered
time entirely. The filtered Gantt now starts at zero and concatenates only the
visible step durations. Hidden intervals contribute neither positions nor axis
extent, including waits between visible steps. Start cells follow this same
filtered axis; tooltips preserve original cycle starts. An explicit filtered-axis
label distinguishes it from the full cycle. Total/Work/Wait and PLC data remain
authoritative and unchanged. Show all restores the complete cycle axis.

Validation passes: 20 focused timing-chart tests; full HMI suite 472 passing with
seven expected skips; AB tool discovery 1,535 tests; root consistency zero
errors/warnings and 33 tests; Flutter analyzer clean; release Web build and Wasm
dry run successful. Rendered-pixel checks prove that a hidden 60-second interior
wait leaves two 1-second bars occupying the retained 2-second axis. Zero-duration
survivors also remain bounded. A separate Flutter widget capture confirms the
layout and eliminated gap.

The release is served at `https://press.localhost/`. Trusted HTTPS checks return
200 and exact release bytes for `main.dart.js`, `flutter_bootstrap.js` and
`index.html`. Served `main.dart.js` SHA-256:
`5E3B3332276E48F2982A3C8843B7F0906B7EB9694F3618BFC4553814425D7E2B`.
Output `C:/work/press68_gantt_visible_web`; previous release backup
`C:/work/press68_gantt_visible_web_backup_01`; deployment record
`C:/work/press68_gantt_visible_deployment_01.json`; validation logs
`C:/work/press68_gantt_visible_*_01.log`.

No controller source/memory growth, writes, download, power cycle or gateway
restart occurred. Live Chrome interaction was unavailable to the agent; the
owner can load the new release by hard refresh. Previous dated time-filter
evidence remains historical and unchanged.
