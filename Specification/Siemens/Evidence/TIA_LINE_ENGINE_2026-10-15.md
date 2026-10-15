# Typed line owner/mirror engine — 2026-10-15

P1 of the [remaining-features plan](../Reports/TIA_REMAINING_FEATURES_PLAN_2026-10-15.md)
has started. The shared engine is implemented and tested independently of the
press. P1 and the optional Core Line profile remain open.

## Implemented

The [engine and bench](../../../FraktalCore/PLC/Siemens/Tests/Line/README.md)
reuse the station/model config capability resolver, metadata emitter, typed
assignments and scalar/decimal validator. Existing shipped press generation
replays byte-for-byte after that refactoring. Identity widths, value widths,
ordinals and capacities derive from Core. The line capacity is independent of
the per-module capability capacity, so the later V3 calendar can exceed twelve
values without changing the module limit.

The infrastructure has no module registration, parent, HAL or command lifecycle.
An owner checks capability revision, access, readiness and native/domain bounds,
advances its own nonzero revision and builds a complete image. A mirror validates
the whole staged image before changing working values. Wrong identities, counts,
keys, revisions, domains and invalid last records leave prior values intact.
Backward revisions are refused; wrap is supported. A same-revision heartbeat
must describe the same typed values, allowing equivalent numeric spellings.

Restore always reapplies the image's typed values and does not invent freshness
or clock quality. Source errors preserve working values. Staleness uses modular
milliseconds, publishes status and raises a deduplicated LOW/SYSTEM AUTO_RESET
event, which remains nonblocking and closes on recovery. Manifest entries retain
the root scope, use `Line/` items and make mirror values read-only; read access
conceals unauthorized values.

## Gates

| Check | Result |
|---|---|
| Native program compile, final native06 | 0 errors, 0 warnings |
| Native incremental hardware compile, final native06 | 0 errors, 0 warnings |
| Native canonical source/type read-back | 244 blocks match |
| Native member/type/access read-back | 62 interfaces match |
| Isolated CPU1516 runtime | 51 assertions, 0 failures |
| Siemens Python engineering tools | 225 tests pass, including five line declaration tests |
| Siemens source lint | 0 findings |
| Cross-tree consistency | 0 errors, 0 warnings |
| Candidate V1 contract gate | clean; existing 31 records / 22 enums unchanged |
| Existing press replay | 216 sources; GRAPH 19/4 steps and optional LD parity preserved |

The native tests include owner edits/refusals, local source copy, whole mirror
apply/refusal, stale event raise/deduplication/automatic close, access-filtered
manifest, unsigned wrap, and native image serialization/reapplication after
clearing working values. The test supplies clock quality explicitly. It does
not qualify UTC synchronization, cross-controller networking, LOAD_DB durability,
actual CPU restart persistence or a live HMI Line page.

The first compile found an incorrect elapsed-time parameter name and a missing
test event sink. Both were corrected. A delta import after that failed session
had no persisted type dependencies; the next full import saved before compiling.
Subsequent native checks also cover canonical comparison of equivalent numeric
text and successful owner-image rebuild publication.

The first full hardware compile retained the isolated baseline's two existing
security warnings: no configured protection level and no display password.
Final incremental hardware compile is clean. This is a functional bench;
R6/security commissioning is not qualified by this record. R3/R4/R5 remain open.

## Isolation and remaining work

Only `FrkLineTest`, TCP/IP 169.254.212.52 (second interface 172.31.254.52),
received this bench image. All three physical adapter mappings were zero. The
approved Openness executable was reused without rebuilding it. The helper
powered off/unregistered only its own test registration and retained its storage.
The saved `Fraktal` CPU1516 remained RUN/TCPIP at 169.254.212.49 and 192.168.1.1,
with zero physical mappings. The physical 1214C was not targeted.

Next P1 work is production composition and one-host scheduling, root manifest and
mailbox/access/audit routing, referencing-root ConfigRev propagation, owner line
sets and mirror refusals naming the owner, a shared LOAD_DB document consumer,
press declaration and live generic-HMI verification. This engine is not yet
accepted as a top-level station declaration feature; no partially wired line
profile is offered by the shipped generator. P2 shifts and P12 cross-controller
source selection remain separate.

## Raw evidence

The [immutable archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_LINE_ENGINE_2026-10-15_R1/)
contains the generated native06 package, compiler/read-back/runtime records,
earlier attempt logs, owner-state preservation and a replayable source snapshot.
Its `SHA256SUMS.txt` binds every payload; the sibling seal records its digest.
Engineering projects, simulator storage, credentials and the private KB backup
are excluded. SiemensAgent knowledge is updated separately, with backup and
database integrity verification.
