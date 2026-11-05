# S6 — Echo re-baselined onto the genealogy pin after a factory reset

2026-11-04, America/Mexico_City (03:04–03:07 UTC on 2026-11-05). Repository
head `7c4689d48`, with the tools tree clean. One guarded session on the local
Echo `601FC87B` (127.0.0.1, slot 0, v38.011) under the standing owner decision
O3. The owner's instruction for this work was "go on, echo is available".

## Why

Earlier that day (13:32 local) Echo had been factory-reset. Its previous
storage is archived on the host under
`Documents\EchoFactoryResetBackup\Root_20261104_133216`. A read-only check
before this session found the identity guard passing, but no controller-scope
tag and no program list: an empty project, not the verified genealogy baseline
the S5 exit left. Every plan §4 session starts from that baseline and rolls
back to it, so it was re-established first. No S6 candidate was downloaded.

## What ran

The plan §4 rollback sequence, run forward from an empty controller, from a
fresh workspace `C:/work/fraktal-ab-s6-rebaseline-20261104/session_01/`. The
runner verified 19 bound input hashes and the repository head, and that the
tools tree was clean, before its first controller call. Stages, all passing:

| Stage | Result |
|---|---|
| Guard | Identity `0x601FC87B`, revision 38.11, Emulate 5580 (product code 288), listener owned by the emulator process, not faulted, keyswitch 0 |
| Dump check | No `.dmp` file in the controller's storage |
| Factory-empty precondition | 0 controller tags and no program list. Checked again inside the SDK program immediately before Program mode |
| Download | A hash-checked copy of the genealogy pin (`D67561C4…ED4084`), Program, Download, Run. The pinned original was never opened and is unchanged |
| SDK log audit | Open project, Download, Save, Save As |
| Access audit | 109 tags conform, and they equal the sealed genealogy reference exactly |
| Medium check | The five host documents equal the S5 baseline record. The image is idle, logged out and restoring |
| Baseline cases | 31/31 pass. The configuration was restored from the medium; nothing was rewritten |
| MANUAL, preflight | MANUAL and idle. The fresh preflight record equals the verified S5 baseline record (`session_19/preflight.json`) with no differing key |
| Final checks | Scan advancing, MANUAL, idle, logged out, not restoring, saved equals live, policy restored |
| Timing | 20 samples, TASK maximum 1,167 µs, 0 overlaps |

The SDK program is a cut-down copy of the S5 session's `restore-genealogy`
step. It accepts only that command, the armed O3 record and the exact pin. The
exported image differs from the one the S5 rollback exported only in its
export dates.

The session made no backup upload: the controller was empty, and its earlier
storage is the owner's archive. There were no fault or TASK-counter clears,
clock changes, power or vendor-state operations, or Echo hard kills.

## Artifacts

`AB_S6_ECHO_REBASELINE_2026-11-04/Session/` holds the session's logs, JSON
records, scripts and SDK program source (57 files).
`withheld_artifacts.json` records, by SHA-256 only, what is not archived: the
ACD copy and its `.BAK`, the L5X export and the built program. The fixture
credential's secret appears in no archived file.

## State left

Echo holds the verified genealogy baseline again: MANUAL, idle, logged out,
not restoring, with the five host documents equal to live. The next S6
native session starts from here.
