# Phase 6 — shared unit-card spacing for inline groups

Date: 2026-10-04 (America/Bogota).

The owner requested the unit card's spacing in the System health card and all
similar cases. The existing unit-card gaps are 8 px in both directions. One
shared visual token, `kInlineItemGap` in `theme_surfaces.dart`, now owns that
spacing across 26 inline wraps in ten consumers. The unit card itself uses the
same token, preserving its geometry.

The update covers health and control-power headings/metrics, counters and state
flags, manual/decision actions, release reasons, overview badges, event/timing
and custom-chart legends, motion/reader/RFID status, custom layers/palette and
compact editor/dialog action groups. Wrapped items also receive the shared gap.
Facet heading separators and signal-tower indicators use it. Event filters no
longer add separate spacer widgets and chip padding on top of the wrap gap.
The HMI contract records the shared inline-spacing policy.

Full HMI: 478 tests pass, 7 expected skips. Analyzer has no issues; release Web
build and Wasm dry run pass. Required AB discovery passes 1,541 tests; root
consistency has zero errors/warnings and root suite passes 33 tests. Existing
widget/layout, control-scale and chart tests cover the affected surfaces.

HTTPS at `https://press.localhost/` serves exact release bytes with 200 responses
for the main script, bootstrap and index. Main script SHA-256:
`0715C5B2EEF7BFA80A3DBF40F2F25550B93506B417B47366E00A29312A2B5928`.
Previous Web release backup: `C:\work\press68_inline_spacing_web_backup_01`. Hard-refresh Chrome to
load the updated client. Browser visual acceptance is pending.

No gateway change/restart, PLC change/generation/download, controller write or
power cycle occurred. PLC memory growth is zero; four users remain the ceiling.
The prior configuration/D6 live acceptance still awaits the owner's gateway
restart and browser/readback checks. Earlier dated spacing records stay intact.

The [JSON record](AB_PHASE6_HMI_INLINE_SPACING_2026-10-04.json) binds source, the 26-group inventory, logs,
deployment and unchanged PLC image by SHA-256.
