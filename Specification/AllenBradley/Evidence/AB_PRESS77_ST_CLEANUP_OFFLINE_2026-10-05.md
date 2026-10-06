# AB press77 — Structured Text cleanup

Recorded 2026-10-05. **Offline PASS; licensed Studio Verify, Capacity Estimate,
completed download and native timing remain pending.** Machine record:
[AB_PRESS77_ST_CLEANUP_OFFLINE_2026-10-05.json](AB_PRESS77_ST_CLEANUP_OFFLINE_2026-10-05.json), SHA-256 `EB71EFCA58225499C2A68FCC45B4FA12A9AE6D42A7AD2F8A19D5CB65C4B82EA1`.
This append-only record does not replace earlier fit or failed-build evidence.

The owner requested clean AB ST, consistent spacing and responsibility-based
routines, followed by committing/pushing main. The source generator now formats
runtime AOI, routine and SFC action/condition ST at one serialization boundary:
four-space indentation, spaced arguments/operators, separate statements/CASE
arms and advisory wrapping. Its lexer checks executable-token identity rather
than rewriting expressions. Frozen Phase 0 fixtures remain unchanged.

The single ordered scan plan emits startup, restore, module calls, Start,
Unit/sequence dispatch, health, diagnostics/alarms, statistics and forcing as
complete program services. Mailbox frame/handler and scan increment keep their
original order. ConfigWrite and ConfigSets run inside the same authorized CASE
arms; ACK and secret wipe remain in the caller. LineStage shares the repeated
calendar copy using existing scratch, with validation/commit timing unchanged.
AOIs retain their owning lifecycle and gain no controller-scope JSR calls.

Prepared artifact: `C:/work/press77.L5X`, SHA-256
`069C81EB94B2BDF5801BDE071CE0A48DC39F04A40CAA7657ED459957247C8A6B`. Regeneration is byte-identical. Comparison against
press76 expands only the twelve new zero-argument service calls and proves
every pre-existing executable token identical, including AOI and SFC bodies.
RLL/SFC graph structure, DataTypes, Tags/initializers, Tasks and Modules are
identical. Manifest remains `026DC8F584CA2D70 / 159176`; equal contract hashes
alone never establish private-code identity.

| Source trend | Press76 | Press77 | Delta |
| --- | ---: | ---: | ---: |
| Declared data bytes | 110268 | 110268 | 0 |
| ST terminators | 4244 | 4216 | -28 |
| ST source bytes | 270379 | 344801 | +74422 |
| ST lines | 5343 | 6776 | +1433 |
| RLL rungs | 20 | 20 | 0 |
| Program routines | 21 | 33 | +12 |
| Maximum program routine depth | 4 | 5 | +1 |

The source increase is layout whitespace. Main is now 13 instructions, with
the work in named routines. No routines are unreachable and no program JSR
cycle exists. Source/terminator/data trends exclude compiled code, AOI storage,
object metadata and reserve; the extra routine objects and call costs are
unmeasured. The last owner-accepted online memory record remains press75:
758568 / 786432 bytes, 27864 available. Do not infer press77 fit or timing.

Immediately before generation, two read-only captures guarded by serial
`7036B510` and the actual V3 header were identical. They preserve M-100/M-200/
M-050/M-101, all four banks, active ordinal 1, minimum air pressure 451, the
calendar and targets. Image SHA-256 `5D044C0A6CEEB15F8AD3B38C108F1A7B3C35C87DBDCC4FC35777E0496055C65D`.
The controller now reports the V3 contract matching prepared press76; no new
Studio Capacity/download acceptance was supplied. The earlier V2 capture guard
refused the changed header before saving an image. No controller writes,
credentials/session capture, gateway restart or HMI changes occurred.

The complete AB suite passes **1623 tests** in 242.635 seconds.
Focused formatting/generation tests pass 59; consistency reports 0 errors,
0 warnings and its 33 tests pass. The first full suite failed one structural
test that still searched Main for rendition dispatch. It now checks the
owning Unit routine and Main's single call, and the complete rerun passes.
The artifact comparison separately guards against executable reordering.

The disposable SDK import attempt against this exact SHA failed opening the
project: **No valid license** (exit 3762504530); no ACD was created and
no controller was contacted. This is an explicit host licensing failure, not a
compile result. The owner must import this exact artifact in licensed Studio,
run Verify Controller and Capacity Estimate, then complete authorized linking/
download and native timing before advancing those claims. AB new-project,
Phase 6 and TC3 handoff guidance describe the ownership/gate lessons.
