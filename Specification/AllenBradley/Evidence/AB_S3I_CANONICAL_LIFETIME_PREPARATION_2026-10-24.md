# S3i natural calendar and retained Program/Run preparation

Client date: 2026-10-24, America/Mexico_City. **Prepared offline only; current
owner authorization is required before this session.** No controller access,
tag write, download or mode change occurred in this preparation. The prior
[publication session](AB_S3I_CANONICAL_RUNTIME_2026-10-24.md) is accepted at its
recorded scope, genealogy is restored, and its authorization is consumed.

The next S3i gates are natural closure of populated live history, target
lifetime/deferred calendar application, and retention across one Program/Run
cycle without downloading in that cycle. Physical power retention remains S7.
These gates use the unchanged ACD
`A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42`, generated
from source `0F3A5F6DD762BED3819404025DAF6D5703511807B440C4988EACF5E494EC72C3`.

The original deployment ACD was changed by its SDK save. Three fresh working
copies were made from the still-pristine, hash-checked Capacity review copy:
deployment, review, and a separate mode-control copy. No immutable genealogy
original was opened. This adds no PLC code, data, field, type, bound or policy.
The exact-hash v38 Echo/Physical build/read-back and measured Capacity gates
transfer from the [qualified preparation](AB_S3I_CANONICAL_PREPARATION_2026-10-24.md):
**2,763,512 used / 382,216 available / 3,145,728 total Blocks (87%)**. New native
scan and retention evidence is still required.

## Fixed calendar fixture

`fraktal_ab_s3i_lifetime_execute.py` uses only the existing public mailbox and
the 21 declared Line V3 WRITE_CONFIG capabilities. It requires local serial
601FC87B, the exact genealogy declaration and canonical manifest, current
exact-image authorization, MANUAL/idle, and no existing operator session.
Each primitive write retains the identity/manifest guard and sequence-last
mailbox handshake. An unrelated session is never logged out by cleanup.

The fixture logs in with the existing fixture administrator and requires the
original complete calendar to be empty. It records every original public Line
value, commits the unchanged UTC offset to obtain a fresh **published
`Line.LastUpdate`**, and positions one 12-hour UTC interval to end at the third
minute boundary after that stamp. It reads no private clock tag and sets no
clock. The interval's start-day mask handles midnight, Sunday and year changes;
unsupported controller clock years refuse.

Five day masks are disabled before setup. The temporary first row uses target
**40** and enables its day mask last. Entering it must close the preceding
unscheduled period as a real history row. A public target edit to **99** must
remain pending while the current snapshot stays 40. The complete original
calendar/targets are restored through public capabilities while that interval
is still active; restoration must remain queued until its natural boundary.

At that boundary, the scheduled row must close with target 40, its original
start, the actual boundary minute and ManualReset false. The original empty
calendar must then apply: CurrentShift 0, no next boundary, no pending revision,
target 0 and two newest-first live history rows. Every captured path/type/value
is compared with the independent owner oracle through the unchanged migration
frame. Full V3 history fields, including UInt16 schema, UInt32 counts/buckets,
Float32 factors and DateTime stamps, enter those comparisons.

The normal path makes **38 public Line configuration commits**. A hard ceiling
of **64 commits** covers partial-failure restoration; this counts mailbox
requests, not their constituent tag writes. No direct Line-state/history,
clock, input/simulation or policy write is added. The mailbox kinds are fixed:
LOGIN, LOGOUT, WRITE_CONFIG and page-zero/current-model QUERY_CONFIG. Existing
validated five-document restoration remains inherited. Cleanup restores the
original public values when needed and logs out only the session it started.
The enclosing session always attempts genealogy rollback after deployment.

Seven calendar assertion rows and seven all-path captures are prepared. The
last capture, taken logged out, records every Line/current/history value and
type for retention comparison. The controller's stored timestamp quality is
retained; an unsynchronized clock is not relabelled synchronized.

## Retained cycle and session order

The new guarded SDK helper has one added `cycle-retained` operation. It checks
the completed calendar evidence and exact Line value/type equality before
opening its separate pristine control copy. After opening, it rechecks exact
identity, no fault, MANUAL/idle, logged out and not restoring. It requires Run,
then changes **Program → Run once**. The cycle branch contains no download,
save, tag-write, clock-set or fault-clear call; it proves its control copy is
unchanged after close. The initial session download is separate.

The unchanged bench image reruns its eight first-scan publication vectors on
that retained Run; these again save/restore both Line owners in the same scan.
After MANUAL normalization if required, a read-only verifier requires the full
pre-cycle Line metadata/history **and types** to be identical and checks those
native results. It does not reconstruct missing history on the client.

The proposed session, still **unapproved**, is:

1. Fresh guards, MANUAL normalization if needed, preflight and backup; audited
   Program/download/Run of A5FAFA46…7E36C42.
2. Five-document restoration and the inherited 41 candidate checks, including
   the first eight native publication results; MANUAL normalization.
3. The bounded calendar fixture above; require natural closure and exact public
   configuration restoration/logout. On first failure, stop and roll back.
4. One retained Program/Run cycle, MANUAL normalization if needed, read-only
   retained equality/native results, all-path acquisition and native TASK timing.
5. Genealogy rollback using a hash-checked copy, five-document restoration,
   31 baseline checks, MANUAL cleanup and final saved/live/policy/fault checks.

The session excludes fault clears, clock changes, firmware/network changes,
power operations, hard kills and vendor-state edits. An unexpected fault stops
the guard. Dump checks precede controller changes and follow the session. No
credentials, ACDs, vendor state or dumps are archived. No commit or push is made.

## Offline results

| Gate | Result |
|---|---|
| Focused lifetime tests | **11 tests, OK**, 27.006 s (`focused_05.log`) |
| Full AB suite by discovery | **2,189 tests, OK**, 306.039 s |
| Root tests | **74 tests, OK** |
| Spec / contracts / strict consistency / whitespace | Pass, zero consistency warnings |
| Session helper build | .NET 8 win-x86, SDK client 2.1.974; **0 warnings / 0 errors** |
| Negative authorization | **6 refused cases**: four SDK commands before guard/SDK access, two fixture phases before controller/credential access |
| Image/source compatibility | A5FAFA46…7E36C42 unchanged; generated source byte-identical; **170 inherited source bindings unchanged, two added (172 total)** |
| Historical reader replay | All **88** accepted S3i native pairs decode unchanged |

The model executes the actual emitted calendar and publisher ST. It tests
natural closure/target behavior, intermediate full-calendar validity, failed
assertion restoration, missing published-clock refusal, active-session refusal,
unrelated-principal logout refusal, finite capability/range/budget checks and
exact retained value/type comparison. It does not claim native acceptance.
Earlier failed focused runs are retained; they exposed incomplete legacy model
setup and missing transport stubs, corrected in the new test apparatus. No PLC
implementation was changed to make these tests pass.

Work:
`C:/work/fraktal-ab-s3i-lifetime-20261024/prepare_9af0ac9f71534d89b5be9645bdc6575f/`.
The [append-only payload manifest](AB_S3I_CANONICAL_LIFETIME_PREPARATION_2026-10-24/manifest.json)
binds scripts, source, tests, image/capacity references and disabled approval.
All authorization flags remain false. S3i exit, actual press/rendition proof,
S3j/S3k and S4–S7 remain open.
