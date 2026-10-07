# AB press80 running, live documents kept; press81 health exclusion (offline)

Recorded 2026-10-07.

## Press80 on the bench, read-only

After the owner's press80 download, serial-guarded reads of `7036B510`
(1769-L24ER-QB1B, 33.14), with no write:

- The manifest reads coherent and equal to source, `E5F914E06055CD3B / 15071508`
  (`C:/work/press80_after_download_manifest_read_01.json`).
- `FRK_Press_ScanCount` advances 30718 → 30818 over one second: the program scans
  at the 10 ms period. The HMI shows the press READY in AUTO on model M-100.
- Probe: interval 9,986 µs, jitter 14 µs, window maximum 230 µs (threshold
  2,000 µs); clock unsynchronized (no CIP Sync; not required on this press).
- System health: Present 1, TaskAvailable 1, and **Healthy 0 only because
  `CONTROLLER_METRICS_UNAVAILABLE` is set**; every other condition is clear. The
  "Task jitter high" rows the HMI showed are closed AUTO_RESET events.

No owner transcript or Capacity Estimate accompanies the press80 download, so
press80's memory figures are still to be recorded; the running image establishes
that press80 fits.

**Live documents kept.** The write-enabled gateway at `127.0.0.1:8099` reports
`liveDocuments.state = kept`. `…\ConfigSets\7036B510-Press\live\` holds the index
and six documents (`Press.station`, `Press.line`, `Press.model1`–`model4`), written
12:05. A fresh twice-identical capture of the running controller
(`press81_source_capture_01.json`; image SHA `5D044C0A…C65D`, identical to the
press79/press80 seed) renders documents whose content equals each kept document.
This is the first owner gate of the [press79 record](AB_PRESS79_LIVE_DOCUMENTS_OFFLINE_2026-10-07.md);
the restore itself is not yet exercised on hardware.

## Why the health card stayed red

The generator set `CONTROLLER_METRICS_UNAVAILABLE` on every scan
(`fraktal_ab_generate.system_health_logic`), copying TC3's rule. TC3's IPC always
has CPU and memory (IMPLEMENTATION_NOTES §161); this controller has no `GSV` source
for either (S3), so the event could never clear: a permanent LOW/System event, the
HMI banner, and System health `ATTENTION` with nothing an operator can do. The
owner's direction: a metric the controller cannot provide is not a fault.

## Press81

- `decl.SystemHealth.require_controller_metrics` (default off), beside the
  time-sync, fieldbus and distributed-clock requirements. Off, CPU and memory are a
  declared platform exclusion: published unavailable, never healthy, never an
  event. On, the station is told on every scan. Part III AB §8.12 records the
  exclusion from Core §8.12's "shall monitor".
- The HMI needs no change: the card's colour follows `Healthy`, and the CPU/memory
  chips are already hidden when unavailable.
- `C:/work/press81.L5X`, SHA-256
  `AC0B8A7BB962611D95CC062D1E2FA4F04DFE9AA9DAB2E9F7B30AB70C7F36C1FE`, seeded from the
  fresh capture; generated twice byte-identically. Against press80 only
  `FRK_Press_ScanHealth` changes: −113 ST source bytes, −1 statement, no data. Tags,
  types, AOIs, tasks and modules are identical and the manifest is unchanged, so
  the running gateway accepts it as it is.
- `C:/work/press81_restore_test.L5X`, SHA-256
  `309852CF047D8ACF5B6444ADEFD8C5972058CBE49ECEB506A118C46C7AA2E7C1`: the same
  build **unseeded**, for the live-document restore acceptance only. Downloaded,
  the controller starts restoring; once a user with the set-gate level logs in,
  the gateway re-applies the six kept documents, recreates M-101 and re-selects
  M-100. If anything goes wrong the documents are untouched and `press81.L5X`
  restores the captured values.
- Rendition gate equal; the full AB suite passes **1671 tests** (
  `press81_ab_tests_01.log`); strict consistency and contract gates clean.

## Owner steps

1. Download `press81.L5X` (or `press81_restore_test.L5X` to also accept the
   restore). Expect System health HEALTHY and no "Controller metrics unavailable".
2. Record press81's Capacity Estimate / online memory as the new baseline.
3. For the restore test: after the download, log in as `phase6_admin`, then check
   `/healthz` `liveDocuments.state = restored` with no losses, Start released, and
   the configuration (station, line, M-100…M-101 banks, active model) equal to the
   capture.
