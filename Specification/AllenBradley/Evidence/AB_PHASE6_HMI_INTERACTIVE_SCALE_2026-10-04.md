# Phase 6 HMI interactive size presets and time-quality ordering — 2026-10-04

The selected size preset now applies to time/event filters and the other
interactive chip families, checkbox/radio glyphs, switches and editor icon
actions. The time-quality indicator starts the system-health metrics row,
before Task and Jitter, including when time is synchronized.

## Implementation and scope

`UiMetrics` remains the size authority. `PresetChip` sizes all eight existing
filter, choice, action and input-chip sites, keeping Material selection,
tooltips and deletion behavior. `PresetToggle` scales the native toggle and
its hit region while reserving the enlarged layout bounds. Native checkbox
and radio list tiles use the same derived scale. Four shared switch rows keep
whole-row activation, merged semantics and a single keyboard focus; their
toggle sits beside the text tile because Material caps its trailing slot.

Timing labels, color markers and chip glyphs follow the preset. Show all keeps
the timing-filter height at every preset. Read-only status badges keep their
compact layout, so overview tiles still fit during navigation-tree resizing.
Nine editor icon actions no longer impose compact density or a fixed glyph
size. The picture toolbar reserves the preset height and scrolls horizontally
on a narrow layer. Authored custom-grid fitting remains the existing policy.
The shared inline spacing from the previous change is retained.

## Validation

Before implementation, three initial rendered-chip checks reproduced a medium
filter height of 48 dp instead of the preset target. Seven new widget tests
cover all chip families, outer-edge taps, deletion, real time/event filters,
Show all alignment, disabled/keyboard toggles, language checkboxes and narrow
picture-toolbar actions. The full HMI suite passes **485 tests with 7 expected
live-environment skips**. Existing navigation/layout tests pass at all three
presets. Analyzer is clean; the release Web build and Wasm dry run pass.
The full AB suite passes **1,541 tests**; root consistency reports **0 errors,
0 warnings**, and its **33 tests** pass.

An isolated render probe uses real Material/Roboto fonts and the actual
health, timing-filter and event-filter widgets at each preset. The images
were inspected for alignment and clipping. Timing filter / Show all heights
are both 48 dp compact, 64 dp medium and 79.4 dp large; standalone checkbox
targets are 48, 62 and 76 dp. These are observations from the rendered probe,
not additional size-policy constants. JSON records source, log, probe, image
and artifact hashes.

## Deployment and remaining bench work

The validated release was reversibly deployed to the existing Caddy Web root.
Trusted HTTPS GETs at `https://press.localhost/` returned 200 and exact local
bytes for main.dart.js, flutter_bootstrap.js and index.html. Previous main
SHA-256: `0715C5B2EEF7BFA80A3DBF40F2F25550B93506B417B47366E00A29312A2B5928`.
New main SHA-256: `AEE6C8998142E0B0167FB2FBE58EEC402DBFD009B74C5E0C98FF4E2EAC4BC80B`.
Backup: `C:/work/press68_interactive_scale_web_backup_01`.

Chrome Ctrl+Shift+R loads the update. No gateway restart, PLC generation,
download or controller write occurred. PLC memory growth is zero; the loaded
press68 image and four-user capacity are unchanged. The configuration and D6
live activation/readback checks in the handover remain open. Earlier evidence
remains historical and unchanged.

Machine record: [AB_PHASE6_HMI_INTERACTIVE_SCALE_2026-10-04.json](AB_PHASE6_HMI_INTERACTIVE_SCALE_2026-10-04.json).
