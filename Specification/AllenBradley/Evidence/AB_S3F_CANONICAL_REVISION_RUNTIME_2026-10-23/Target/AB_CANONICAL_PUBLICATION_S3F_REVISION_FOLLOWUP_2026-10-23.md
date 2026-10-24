# S3f retained revision and active-model follow-up

**Latest, 2026-10-23: S3f exit passes on Echo.** The authorized revision
follow-up completed 74 accepted checks (42 candidate, one retained Program/Run,
31 restored genealogy), with 93 independently replayed paired captures and
2,114 AB / 74 root tests passing. Revision changes 745193095 → 1646242802 across
the no-download restart; retained configuration/banks/policy/page stay equal.
Both model CHANGEOVERs and exact restoration pass. Capacity is 73%, 2,298,448
used / 847,280 available / 3,145,728 total Blocks. Candidate scan is 835 µs
median / 4,573 µs maximum; restored genealogy 99 / 1,168 µs; zero overlaps.
Read [revision runtime evidence](Evidence/AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23.md).
All failed attempts are retained (125 actual rows, 74 accepted); four read-only
connections and fixture mode-application waits leave the PLC image and generic
reader unchanged. Echo is restored to genealogy, Run/not faulted/Remote,
MANUAL=1/idle/logout, five saved/live documents equal, policy/preflight equal.
Current sources: 143. This session approval is consumed; V2 remains inactive.
S3g inventory/review is next; further native changes need their own current approval.

## Preparation history


Offline preparation after the [accepted S3f session](Evidence/AB_S3F_CANONICAL_RUNTIME_2026-10-23.md).
Echo remains on the restored genealogy baseline. No follow-up controller
operation has run or been authorized. V2 remains inactive.

The retained-state model reproduced a collision: previous revision 10,000,000,
new boot seed 9,999,999, published revision 10,000,000. The code selected a
non-equal seed, then its ordinary changed-data increment returned that seed
to the previous retained value. The fix marks first scan as initialization,
avoiding that second increment. The seed's explicit inequality guard then
guarantees a different valid token, including lower/equal/zero/wrap boundaries.

The generated delta is exactly **one DINT assignment in one ST body and one
ST line**. Public/private layouts, initial values, all other code and the SFC
graph remain identical. This implements the already approved revision rule;
it introduces no new contract exception or numeric tolerance.

Work: `C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009/`.
ACD: `BD030AEB01D58469D452D877A9CFF2868B79DE45055A3795D1D1479BB2771183`.
Source: `B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3`.
Both v38 compilers/read-backs/access, prepared ACD and **2,111 AB / 74 root
tests** pass. Automatic Capacity is **73%, 2,298,448 used / 847,280 available /
3,145,728 total Blocks**, +36 versus the first S3f image. No feature was cut.

The next native session is concrete: full inherited S3f coverage, one active
model round trip through the existing simulated CHANGEOVER/tooling decision,
and one retained Program/Run cycle with no download. The model, live recipe,
banks, fixture inputs and mode must restore exactly. Retained configuration,
policy and page content must remain equal while the revision changes. Private
model selection state is never written. Planned checks total **74**: 42
candidate fixture rows, one retained restart and 31 restored-baseline rows.
The new helper refuses both additional vectors without their explicit current
authorization flags. Fault clearing and clock setting remain outside scope.

The [preparation evidence](Evidence/AB_S3F_CANONICAL_REVISION_PREPARATION_2026-10-23.md)
binds 142 sources, the exact image, guarded runbook, failed audit attempts and
unchanged predecessor seals. Native acceptance is pending; S3g has not started.
