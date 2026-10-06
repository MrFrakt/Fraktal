# Fraktal/AB Phase 6 item 4 — data classes, offline build

**Date:** 2026-10-02, America/Bogota. **Parent:** `7823c2b`.
**Stage:** generated and tested offline; owner Studio v33 Verify/download,
gateway restart and guarded hardware verification pending. The owner confirmed
that the corrected HTTPS login now works and authorized continuing item 4.
No controller writes, download or gateway restart were performed for this build.
The last verified controller build remains press62. The companion
[JSON](AB_PHASE6_DATA_CLASSES_BUILD_2026-10-02.json) records source hashes,
artifacts, checks, mutations and HMI deployment without credentials.

## Artifacts and scope

Both declarations reproduce byte-for-byte from `C:\work\seed_v33.L5X`.
No L5X, SFC or ladder was hand-edited. Press63 is an intermediate offline
artifact; the owner deployment artifact is **press64**.

| Property | Press | Station template |
|---|---|---|
| File | `C:\work\press64.L5X` | `C:\work\phase6_data_template.L5X` |
| SHA-256 | `A07AC994DAA8EC27F181FB52333364F9BBABAD7B2E0896ADFE5DB8A42830A339` | `C3B85261CB5D880250B04237AF5E16B2C056E0648D98779ABCB67E2F9948CDB6` |
| ContentHash | `7E0EC4F58C126852` | `901092E69808D94A` |
| ConfigRevision | 8261316 | 9441426 |
| Manifest major / bytes | 4 / 80,760 | 4 / 80,760 |
| Fields | 563 / 768 | 377 / 768 |
| Localization | 565 / 768 | 476 / 768 |
| WriteCapabilities | 9 / 64 | 4 / 64 |

Manifest major 4 preserves the V3 capability prefix and appends ClassKey,
MinReadLevel and MinWriteLevel. AccessAudit V3 preserves the V2 prefix and
appends two 64-row metadata arrays for refused value/required level. Policy
has a separate retained V1 tag; AccessState V3 and private user registrations
are byte-identical to press62. This adds 1,480 declared bytes for the press:
40 policy, 128 effective levels, 32 private work, 512 audit and 768 manifest
capability storage. Compiled code and platform bookkeeping are excluded;
controller fit and scan cost still require Studio and hardware evidence.

XML comparison against press62 confirms unchanged module AOIs, I/O modules,
tasks and existing mode-chain routines. Only Main, the mailbox and the audit
routine change; two shared data-access routines are added. Public policy/levels
are externally read-only and work is private. The only externally writable
operator surface remains HmiRequest. The artifact retains the prior physical
I/O configuration: embedded I/O is not inhibited and task output updates are
enabled. No I/O was operated for this offline item.

## PLC authority and TC3 semantics

Core §3.8d and TC3 §138/M_DataLevel are the oracle. The press and template
declare `public` and `commissioning`, both defaulting to read/write NONE.
Station number uses `public`. Pressure calibration uses `commissioning` and
an immutable ENGINEER write minimum; the template applies that minimum to
its dwell calibration. An empty ClassId retains DATA_READ/DATA_WRITE.

One PLC resolver raises class policy to each value's minimum. Unknown classes,
invalid class counts and corrupt levels require ADMIN. SET_CLASS_LEVEL checks
ACCESS_POLICY and native ClassId bytes, direction and level on the controller.
Startup does not reset edited class policy. The physical power-cycle/download
retention claim remains unproved.

QUERY_CONFIG always retains metadata; unreadable values have blank ValueText
and Readable=FALSE. Typed writes and captures check the effective write level
before candidate sampling or commit. Set load checks all staged records before
any commit; export checks all records before returning any line, including the
header. Both name the first inaccessible record. A refused export clears its
previous line. SAVE/DELETE retain CONFIG_SET alone. The gateway copies PLC
levels/readability and does not calculate another policy. Configuration page
revision changes with values, permissions and visibility. Denial audits name
the actual controller actor, value key and required level.

Resolved levels refresh when the session changes and before/after committed
requests, avoiding resolver work during unchanged cyclic scans. One-shot
requests are still lowered before the mailbox sequence check. The existing
generic HMI renders classes and effective value permissions; its only source
change adds the two project labels in English and Spanish.

## Offline checks and client deployment

- AB tool suite: **1,448 tests pass**.
- Consistency: **0 errors, 0 warnings**; its suite **33 tests passes**.
- Eleven in-memory permission mutations are killed by assertion failures;
  each targeted baseline passes. They remove minimum/unknown-class protection,
  write/capture/load/export guards, PLC-projected visibility, policy gating,
  export staging or stale-line clearing. No source-file mutant is retained.
- Flutter: **439 tests pass, 6 skipped**; analyze reports no issues; release
  Web build succeeds.
- The SDK attempts `OpenLogixProjectAsync` on press64 and refuses
  **No valid license** before opening the project. It performed no online
  operation. Owner **Verify Controller** on the licensed Studio desktop is the
  compile gate; this record does not claim a clean compile.

The tested release at `C:\work\press64_hmi_web` is deployed to Caddy's actual
`FraktalCore/HMI/build/web` root for `https://press.localhost/`. All 42 resource
hashes match. Main JavaScript SHA-256 is
`6CD7739CA101CE1054244FB26FFABA57ABBE39374D296315AF773F06A4DD2D7F`.
The prior release is retained at
`C:\work\phase6_data_hmi_https_backup_20261003_035041`. Proxy configuration
and authentication are unchanged; an unauthenticated loopback HTTPS request
still returns 401. Hard-refresh Chrome after the coordinated deployment.

## Owner deployment and remaining gate

Import **`C:\work\press64.L5X`**, run Studio v33 **Verify Controller**, download
to serial **7036B510**, and restart the gateway. After the owner's “done”, run
the manifest/health readback, the guarded Phase 6 `--data-classes` fixture and
the applicable regression set. The prepared harness checks actual values,
native impersonation refusal, calibration minimums, hidden metadata and atomic
set load/export refusals. Its finally restores class/action policy, timeout,
station values and anonymous session; the parent restores mode/style/baseline
and disarms fixture inputs. Stores are isolated disposable directories.

The 2026-09-29 decision enables writes on this v33 legacy zone-and-conduit
bench. Item 4 widens the permission surface with class edits and per-value
checks. These offline results do not establish the **write-enabled S9 claim**,
physical retention, controller fit or measured scan budget. S9 remains owed.
