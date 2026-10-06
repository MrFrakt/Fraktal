# AB press78 — configuration memory reduction

Recorded 2026-10-05 after press77's final-link memory failure. The owner now
reports **"its good now, please commit and push on main branch"**. This records
reported resolution and commit/push authorization; the statement does not name
the downloaded artifact or provide new Studio Capacity values. Press75 remains
the last measured online memory baseline. Historical evidence is unchanged.

The generated correction is `C:/work/press78.L5X`, SHA-256
`6063EE0B2E15B9E4C162765701D88E24D58340C1D1D83C4B45E469DFC4735168`. Two generations are byte-identical. Its public
manifest remains `026DC8F584CA2D70 / 159176`; that contract hash cannot distinguish
press76/77/78 private executable code. The fresh serial-guarded read of
`7036B510` produced two identical configuration captures, preserving four model
banks including M-101, minimum air pressure 451 and the current V3 schedule.
The capture excludes accounts, sessions and history; no PLC writes were made.

## Change and behavior

Only `FRK_Press_ConfigWrite` and `FRK_Press_ConfigSets` differ from press77.
One shared generator groups capabilities with equal immutable bounds and flags
or type facts into multi-label CASE arms. Sampling, per-value access checks and
commit addresses remain separate. SAVE/EXPORT selects each record kind once,
copies its fields and applies the validated inactive-model override in one
guarded block, publishing count last. Validation, audit, ACK and secret wipe
retain their existing order and owners. No tags, types, reserves or features
are added or removed; all three AUTO renditions and the 33 program services stay.

| Generated measure | press78 | Delta from press77 |
| --- | ---: | ---: |
| ST source bytes | 332428 | -12373 |
| ST statement terminators | 4060 | -156 |
| ST lines | 6460 | -316 |
| Declared data bytes | 110268 | 0 |
| RLL rungs | 20 | 0 |

Declared layouts/initializers, AOIs, tasks, modules and existing ST/RLL/SFC
structure compare unchanged. Expanding grouped fact labels reproduces the old
writer AST. Executing actual press77 and current transaction bodies across
205 boundary, permission, root, operation and record-kind cases preserves every
tag, including scratch, replies, records, model banks, snapshots and audit.
These are executable-model comparisons, not measured controller timing or fit.

## Validation

The full AB suite passes **1625 tests** (305.037 s).
The 47 routing tests pass; boundary/snapshot matrices pass, including inclusive
bounds, invalid-value nonmutation, distinct write addresses, station values
with a model selector, unselected snapshot kinds and inactive-model selection.
The consistency suite passes 33 tests; the cross-artifact check reports 0 errors
and 0 warnings. Reproduction:

```powershell
& C:/work/venv_gw/Scripts/python.exe -B -m unittest discover -s FraktalCore/PLC/Allen-Bradley/tools -p 'test_*.py'
& C:/work/venv_gw/Scripts/python.exe -B tools/check_consistency.py
& C:/work/venv_gw/Scripts/python.exe -B -m unittest tools.test_check_consistency
```

Two original comment-dependent tests failed in the first full run after fact
labels were grouped. They now execute generated writes and check address/model
isolation. The second full run above passes; the first failed run is not
reported as a success.

The exact-artifact native SDK import again reports **No valid license**, exit
3762504530, creates no ACD, leaves the input unchanged and contacts no PLC.
The licensed-desktop gate cannot run through that SDK in this session. The
owner's follow-up reports resolution but supplies no exact-artifact native
Verify/download transcript, measured memory saving or new free-memory margin.
Source reductions do not establish compiled savings. Record native Capacity
and timing before further growth; no attribution of the press77 excess to
whitespace, comments or routine overhead is established.

Machine record [AB_PRESS78_CONFIG_MEMORY_REDUCTION_2026-10-05.json](AB_PRESS78_CONFIG_MEMORY_REDUCTION_2026-10-05.json), SHA-256 `DC6D203655A74C0B20C82545BC400540C669F2ABEAC55C34821641F053D7225F`,
contains source/log hashes, generation deltas and all 205 comparison rows.
Read the [native failure](AB_PRESS77_NATIVE_LINK_MEMORY_FAILURE_2026-10-05.md)
and [prior cleanup proof](AB_PRESS77_ST_CLEANUP_OFFLINE_2026-10-05.md) separately.
