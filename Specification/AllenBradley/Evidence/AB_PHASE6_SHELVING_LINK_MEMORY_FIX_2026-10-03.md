# Fraktal/AB Phase 6 shelving — link/download memory correction

**Date:** 2026-10-03, America/Bogota. **Parent:** `e21daad`.
**Stage:** prepared and tested offline; owner Verify, completed download and
guarded hardware verification pending. Press64 is the last confirmed successful
download. Controller state after the cancelled press66 download is unverified.
No controller reads or writes, download, gateway restart, provisioning, clock
or mode change was performed this turn. The earlier
[press65 build](AB_PHASE6_SHELVING_BUILD_2026-10-03.md) and
[press66 correction](AB_PHASE6_SHELVING_MEMORY_FIX_2026-10-03.md) remain unchanged.
The companion [JSON](AB_PHASE6_SHELVING_LINK_MEMORY_FIX_2026-10-03.json) binds
owner output, artifacts, source hashes, comparisons, size reports and checks.

## Owner result

The supplied Studio output progresses through verification, compilation,
downloading and linking all routines of press66, then ends:

```text
Error: Out of memory in the controller.
Cancelling download...
Complete - 1 error(s), 0 warning(s)
```

This is a failed download, not a successful deployment or authorization for
live fixture writes. Verify alone did not establish controller fit. Future
memory baselines advance only after the owner completes the link/download.

## Correction

Press67 removes two further copies of Start release logic and eight additional
copies of configuration audit logic. One `FRK_Press_ReleaseStart` routine runs
at the original cyclic point and on START/RELEASE_START requests, preserving
the immediate policy recheck. One `FRK_Press_ConfigRecordAudit` routine runs
after each accepted configuration write or capture. Existing private candidate
and wipe storage are reused; no new scratch tag is allocated. Capability,
captured machine value, model scope, revision, capture source, clock and actual
controller actor remain in the existing audit row. Short actors zero the tail.
Validation, readiness, typed ranges and data-class permissions remain before
the write and audit.

Fields and Localization keep their 768-row ceilings but allocate the declared
count plus 64 rows of reserve, rounded up to a 64-row block and capped at the
ceiling. Press67 needs 640 rows of each instead of 768, saving **12,288 bytes**:
4,096 in Fields and 8,192 in Localization. It retains 75 unused Fields and 70
unused Localization rows. The header and native tag dimensions carry the actual
capacity; content/hash are unchanged by capacity alone, and the reader checks
capacity independently. Overflow and the 100 KiB budget still refuse generation.
The template receives the same rule rather than paying for press-sized reserve.

| Offline trend | Last successful press64 | Failed press66 | Prepared press67 |
|---|---:|---:|---:|
| Mailbox ST source bytes | 107,805 | 108,735 | 88,224 |
| Mailbox statement terminators | 1,511 | 1,529 | 1,269 |
| Main ST source bytes | 72,251 | 75,192 | 72,082 |
| Main statement terminators | 956 | 994 | 951 |
| Total ST source bytes | 291,409 | 301,017 | 282,562 |
| Total ST statement terminators | 4,523 | 4,651 | 4,416 |
| Total ST lines | 5,551 | 5,704 | 5,451 |
| Declared supported tag data subtotal | 117,400 B | 117,824 B | 105,536 B |

Press67 removes **18,455 ST source bytes and 235 statement terminators** from
press66. Its total trends are also below press64 by 8,847 source bytes, 107
terminators and 11,864 declared data bytes. The new Start helper contains
3,140 source bytes / 44 terminators / 55 lines; the audit helper contains
2,026 / 24 / 33. All three renditions remain; the ladder retains 20 rungs.

Source counts are growth indicators, **not compiled instruction memory or
proof of controller fit**. The data subtotal includes supported allocated
DINT/SINT layouts and StringFamily padding, but excludes AOI instance storage,
aliases, unsupported types, object metadata and controller reserve. It is not
a free-memory measurement. The owner-selected **four-user ceiling** remains;
the press allocates three registrations and the empty template one inert row.
Alarm active/history capacities remain 16/64; profiler/OEE history remains 60.

## Artifacts and scope

| | Press | Station template |
|---|---|---|
| File | `C:\work\press67.L5X` | `C:\work\phase6_link_memory_template.L5X` |
| SHA-256 | `C07886CC6C490B46A2DDCD90B5F6AF494CF2722D611020C1295DC728522ACD2F` | `632900553C7E7AA368BBE853574F27AA131E605C3EB57DA0F1B6B98FF4C57A98` |
| ContentHash | `832DD0D0F260872B` | `12B6BB5F18F8C282` |
| ConfigRevision | 8596944 | 1226427 |
| Manifest major / bytes | 4 / 68,472 | 4 / 58,232 |
| Fields | 565/640 | 379/448 |
| Localization | 570/640 | 481/576 |
| Rationalization | 23/32 | 19/32 |
| Write capabilities | 9/64 | 4/64 |

Both outputs reproduce byte-for-byte from `C:\work\seed_v33.L5X`, including
a fresh generation against the final source. Against press66, AOIs, tasks,
I/O modules, data types, sequences, access state, user storage and writable
tag names compare equal. Only Main/mailbox routines change and the two shared
routines are added. Only MfHeader, MfFields and MfLocalization tags change.
Native manifest row types remain unchanged; two array dimensions shrink and
the header reports their new capacities. Relative to press64, the shelving
schema additions from press65 remain. The HMI production source and release
are unchanged. Credentials were not changed.

## Checks and next gate

- **1,484 AB tests and 33 consistency tests pass.** `check_consistency` reports
  **0 errors, 0 warnings** across inventory, localization, parity and readsurface.
- **21/21 in-memory mutations are killed by assertions**, with no mutant errors.
  They cover the twelve prior shelving guards plus machine-value audit,
  authenticated actor, cleared actor tail, model/source metadata, immediate
  request policy refresh, capacity headroom/ceilings and station-sized reserve.
  The policy vector changes and clears the required level between requests,
  without a cyclic refresh; both changes appear in that request's report.
- Shared audit tests execute every declared capability and bounded wraparound.
  Platform-limit checks include both new helper bodies. Capacity tests exercise
  growth, ceiling and budget overflow, actual dimensions and reader mismatch.
- The local SDK attempts `OpenLogixProjectAsync` on press67 and refuses **No valid
  license** before opening the project. New Studio compilation, fit, manifest
  readback and runtime behavior therefore remain unverified.

Import **`C:\work\press67.L5X`** into Studio 5000 v33 and run **Verify
Controller**. After a clean result, download to **192.168.100.89**, exact serial
**7036B510**, and confirm the download completes through linking. Then restart
the gateway and reply “done”. This permits the guarded
`--shelving --execute-fixture` run and existing regression suites, including
complete manifest capacity/row readback and scan measurements. The existing
serial checks and fixture/session/policy restoration remain in place.

Physical retention and the write-enabled S9 claim remain owed on the recorded
v33 legacy zone-and-conduit bench. This offline repair does not establish them.
