# Fraktal/AB Phase 6 press67 — live readback and fixture readiness

**Date:** 2026-10-03, America/Bogota. **Parent:** `02b8ce9`.
**Scope:** serial-guarded controller reads and the existing gateway health
endpoint. No controller write, fixture command, download, gateway restart,
provisioning, fault clear or mode change was issued by the agent.
The owner confirmed the HTTPS recovery and asked to continue. Current
authorization for active fixture writes was requested under AGENTS.md §3a
and is pending at this snapshot. The companion
[JSON](AB_PHASE6_PRESS67_READINESS_2026-10-03.json) retains the full read results.

## Readback

Target `192.168.100.89` answers as exact serial **7036B510**, model
`1769-L24ER-QB1B/A`, revision 33.014. Its complete live manifest is coherent
and every declared table row equals the current declaration. The header is
valid, not truncated, and has:

| Field | Observed |
|---|---|
| ContentHash / ConfigRevision | `832DD0D0F260872B` / 8596944 |
| Manifest major / bytes | 4 / **68,472** |
| Fields | 565/640 |
| Localization | 570/640 |
| Rationalization | 23/32 |
| Write capabilities | 9/64 |
| Complete read time | **148.642 ms** |

These dimensions/content match the prepared press67 contract; manifest
identity alone does not prove its changed command logic. The artifact on disk
remains SHA-256
`C07886CC6C490B46A2DDCD90B5F6AF494CF2722D611020C1295DC728522ACD2F`.
The owner's existing gateway returns `status=ready`, `plcReady=true`.

## Health and read-only preflight

S3 passes **6/6**, with a 10,000 µs task period, last scans 624–817 µs,
median 658 µs, maximum **5,238 µs**, zero task overlaps and zero major/minor
fault bits. Time synchronization/PTP remain 0/0 as on this bench. No fault or
timing counter was cleared.

The shelving parent's read-only path passes **4/4**. The press is stopped
and error-free. Alarm active/history schemas are V2, the standing metrics
event is present and no active shelf exists. The current known level-4
session has no pending login; all twelve access thresholds and idle timeout
are zero, so the prepared fixture can restore that session/policy.

The prepared active run will exercise shelf/unshelf, identity and role
refusals, expiry after logout, unshelvable defects, controller history and
the configuration/Start regression set. These commands have not run in this
snapshot. Successful restoration, active command behavior, physical retention
and write-enabled S9 are not established by this read-only record.
