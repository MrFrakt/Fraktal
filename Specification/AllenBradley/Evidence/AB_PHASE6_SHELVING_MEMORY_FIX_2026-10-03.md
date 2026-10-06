# Fraktal/AB Phase 6 shelving — controller memory correction

**Date:** 2026-10-03, America/Bogota. **Parent:** `e23d401`.
**Stage:** regenerated and tested offline; owner Studio Verify/download and
guarded hardware verification pending. The last confirmed loaded build is
press64. No controller reads or writes, download, gateway restart, clock or
mode changes were performed this turn. The original
[press65 record](AB_PHASE6_SHELVING_BUILD_2026-10-03.md) remains unchanged.
The companion [JSON](AB_PHASE6_SHELVING_MEMORY_FIX_2026-10-03.json) records
artifact/source hashes, comparisons, size reports, gates and mutations.

## Owner result and correction

The owner reported the following Studio Verify result for press65:

```text
Error: Routine 'FRK_PressProgram - FRK_PressHmiMailbox': Out of memory in the controller.
Complete - 1 error(s), 0 warning(s)
```

Press65 expanded character comparisons for seven source paths and 23 reason
descriptions directly into the mailbox. Press66 resolves both through bounded
native byte loops over the existing controller-owned Modules, Localization
and Rationalization tables. ActionKey is generated from the same reason stem
plus `.action`; comparison uses that stem, and the same rationalization row
supplies category/shelvability. Unknown flags/categories fail closed. Header
counts, key indices and string lengths are guarded before array access. No
gateway ordinal authorizes a shelf, and no second identity table is allocated.

One shared `FRK_Press_AlarmShelfRequest` routine owns request processing; the
mailbox calls it after the existing PLC session/gate check. Existing private
scratch fields carry the lookup cursors and then the resolved alarm slot and
duration. No private layout change or additional storage is needed.

| Offline trend measurement | Loaded press64 | Failed press65 | Prepared press66 |
|---|---:|---:|---:|
| Mailbox ST source bytes | 107,805 | 167,942 | 108,735 |
| Mailbox ST statement terminators | 1,511 | 2,727 | 1,529 |
| Mailbox ST lines | 1,845 | 2,562 | 1,863 |
| Shared shelf request ST bytes / terminators / lines | — | — | 5,626 / 71 / 91 |
| Total generated ST source bytes | 291,409 | 354,598 | 301,017 |
| Total generated ST statement terminators | 4,523 | 5,778 | 4,651 |
| Total generated ST lines | 5,551 | 6,312 | 5,704 |
| Declared supported tag data subtotal | 117,400 B | 117,824 B | 117,824 B |

The repair removes **1,127 statement terminators** and **53,581 ST source
bytes** from press65. Mailbox-plus-helper request growth over press64 falls
from 1,216 to 89 terminators. Total press66 growth over the verified baseline
is 128 terminators and 424 declared data bytes. The four-user ceiling remains;
the press allocates its three registered rows, with no reserved fourth row.

These are source growth measurements, not native compiled instruction bytes.
The data subtotal derives allocated DINT/SINT layouts with StringFamily
padding; all seven AOI instances are explicitly excluded, along with aliases,
unsupported types, object metadata and controller reserve. It is not a
free-memory measurement or proof of fit. Every generator result now includes
`GeneratedSize`; `fraktal_ab_generated_size.py <new.L5X> --baseline <verified.L5X>`
reports total/per-routine deltas. The guide and handover require this comparison
for remaining implementations; owner Studio Verify remains the fit gate.

## Artifacts and scope

| | Press | Station template |
|---|---|---|
| File | `C:\work\press66.L5X` | `C:\work\phase6_shelving_memory_template.L5X` |
| SHA-256 | `C566E397760CE4FF621B7CE3C23B8DA7585FE9ED788BC0727901849ADA14DC5B` | `99F5F0A2BC77575C926FF0D6C333CAAE6EC9EBC39F688A6A273954098FF9991A` |
| ContentHash | `832DD0D0F260872B` | `12B6BB5F18F8C282` |
| ConfigRevision | 8596944 | 1226427 |
| Manifest major / bytes | 4 / 80,760 | 4 / 80,760 |
| Fields | 565/768 | 379/768 |
| Localization | 570/768 | 481/768 |
| Rationalization | 23/32 | 19/32 |

Both outputs reproduce byte-for-byte from `C:\work\seed_v33.L5X`. Relative
to press65, only mailbox logic changes and the shelf request routine is added;
data types and controller tags compare equal, including user storage. AOIs,
I/O modules, tasks and sequence routines remain equal. Manifest content/hash
is unchanged from press65: file SHA-256 identifies this logic correction.
Writable tag names remain equal to press64. Shelf work is externally hidden;
alarm flags are read-only. The existing HMI production source/release is
unchanged. No credential provisioning or PIN change was performed.

## Verification and next gate

- AB tools: **1,479 tests pass**; consistency suite: **33 tests pass**.
  `check_consistency`: **0 errors, 0 warnings** across all four checks.
- Generated shelving ST preserves PLC actor/role checks, unique active or
  WAIT_RESET identity, registry restrictions, whole-second capped duration,
  logged expiry, slot reuse and control blocking. The new lookup executes
  every declared source/reason pairing, rejects malformed native lengths,
  indices and counts, and rejects unknown permission metadata. Its statement
  count stays constant as paths/reasons grow.
- **12/12 in-memory mutations** are killed by assertion failures with zero
  mutant errors: the nine original shelving semantics plus native byte
  comparison, unknown shelvable flags and the manifest-count guard.
- The SDK attempts `OpenLogixProjectAsync` on press66 and refuses **No valid
  license** before opening the project. No target compilation, controller fit
  or new runtime result is claimed.

Import **`C:\work\press66.L5X`** into Studio 5000 v33 and run **Verify
Controller**. After a clean result, download to **192.168.100.89**, exact serial
**7036B510**, and restart the gateway. The owner's “done” then arms guarded
`--shelving --execute-fixture` verification and the existing regression set.
All original fixture restoration and serial checks remain in place.

The bench write-enabled decision remains the v33 legacy zone-and-conduit
posture. Shelving widens its mutation surface; this offline correction does
not establish S9. Owner compile/fit, expiry/scan measurements, hardware
regression, physical retention and the write-enabled claim remain pending.
