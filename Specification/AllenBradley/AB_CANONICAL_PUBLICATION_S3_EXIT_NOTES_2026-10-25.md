# S3 exit notes - path census passed; press accepted on Echo

Non-normative working notes, 2026-10-25. S3k passed on the genealogy bench
([runtime](Evidence/AB_S3K_CANONICAL_RUNTIME_2026-10-25.md)). The S3 exit
([plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md) "Exit") still needs the
actual press declaration in ST, SFC and LD on Echo, physical I/O evidence and
a consumer census before S6. No controller operation was performed for these
notes; Echo remains on the restored genealogy baseline. No commit or push.

## Path census - passed

[`AB_CANONICAL_PUBLICATION_S3_PATH_CENSUS_2026-10-25.json`](AB_CANONICAL_PUBLICATION_S3_PATH_CENSUS_2026-10-25.json)
checks every frozen genealogy path against the 91 accepted S3k native
comparisons (idle plus 90 paired captures), with every input bound by hash.

| Result | Paths |
|---|---:|
| Frozen genealogy paths | 4,437 |
| Compared natively, no differences, native type equal to the stage-approved type | 4,087 |
| ...of which via approved spellings (30 D2 indices, 122 report rows) | 152 |
| Frozen config entries 17-30: page-1 rows 1-14 of the Core 16-entry window, matched in 2 captures | 350 |
| Unexplained types or paths | 0 |
| Compared paths outside the frozen set: S3j fieldbus product / S3f missing Core fields / Line status | 327 / 12 / 2 |

Carried paths by approving stage: S2-S3e 2,154, S3f 451, S3g 1,055, S3h 278,
S3i 16, S3k 133. The census covers path, spelling, window and type
correspondence; values are proven by the comparisons themselves against the
live oracle. Dynamic rows absent from the frozen sample (shift history V3, alarm
ring, sequence rows) were proved at their own stages.

## Press S3 exit candidate - offline gates pass

Layering, one responsibility each:

- `fraktal_ab_press_echo38`: the press declaration retargeted to Echo (existing).
- `fraktal_ab_press_rendition_echo38`: AUTO carried in ST, SFC and LD. The L24ER
  carries ladder only to fit its memory (owner, 2026-10-07); the AUTO graph is
  one declaration, so that selection is a subset. This is the legacy oracle.
- `fraktal_ab_press_canonical_echo38`: the five S3k canonical choices accepted
  on genealogy, and the press I/O catalog bound to a sampled-word source as at
  S3j (Echo emulates no electrical I/O).

Tests pin that each layer changes only those fields and that the press S3k path
contract is the genealogy contract minus Part, HostEvents, Nameplate,
SignalTower and the smaller alarm/step surfaces (8 fewer rationalized reasons,
3 fewer steps): 4,058 idle paths, the same 133 mailbox/report paths.

| Gate | Result |
|---|---|
| As-declared press (AUTO ladder only), both v38 targets | Build and strict read-back pass |
| Candidate source `6FD00A48...30FBB02` | Builds on EchoController and PhysicalController, 0 warnings/errors; read-back equivalent: 61 bodies, 54,267 initial values |
| Effective access, both exports | Pass, 117 types, no findings |
| Offline ACD `15E89025...CFD76F` | Prepared, read-back equivalent |
| Automatic Studio Capacity | **1,669,892 used / 1,475,836 available / 3,145,728 Blocks, 53%** |
| AB suite / root / spec / contracts / consistency / whitespace | 2,300 tests pass; all clean |
| Accepted S3k genealogy image | Regenerates byte-identically (`B5433362...`) |

The equivalence gate is now declaration-parameterized: `s3k_equivalence.run`
takes a candidate factory and oracle declaration (genealogy defaults unchanged),
`fraktal_ab_press_s3k_equivalence` pins the press oracle before any legacy module
binds its APP, S3h reads Part and tower owners only where declared, and the shared
runner refuses an oracle already bound to another declaration. That guard would
have caught the earlier S3k idle-equivalence run that bound the default station.

## Press walk and session - prepared offline

`fraktal_ab_press_canonical_execute` is the press walk. Its base run proves the
Part fixture's six machine cases - normal cycle, handled NOK, hold and resume,
hold then STOP, hold then mode change, adopted fault with one-reset restart -
from the Unit's own counters and state, in all three AUTO renditions. The S3a-S3k
capture layers, the access, configuration, set-store and provider vectors and the
14 typed/collision rows run unchanged on top, through an additive `base` parameter
(genealogy remains the default). The tower orchestrator's declaration-neutral rows
(configuration restore/preservation, logged-out refusal) are now one function the
tower bench and the press share; its tower-only cleanup runs only where a tower is
declared. A scripted-Unit test drives all six cases and their checks offline.

The shared equivalence runner now accepts either its oracle declaration or the
candidate as the bound legacy oracle, and refuses anything else. That is the
configuration the accepted S3k walk actually ran with: the walk binds the
candidate first because its identity guard needs the exact legacy manifest.

`C:/work/fraktal-ab-s3-exit-20261025/press_session_01/` is generated from the
accepted S3k orchestration by asserted substitutions only (pins, candidate
declaration, walk/equivalence entry, folder and tool names). It pins ACD
`15E89025...CFD76F` and source `6FD00A48...30FBB02`, binds 406 sources by hash,
builds its session tool with 0 warnings/errors, and refuses before any controller
contact while its authorization is the all-false template; so does the walk.
2,303 AB tests and root gates pass; both pinned images regenerate identically.

The session, once authorized: fresh backup; guarded MANUAL normalization;
Program/download/Run; five-document restore; the press walk; read-only idle
equivalence, generic acquisition and scan; then pinned-copy genealogy rollback,
exact host-document restoration, the 31 baseline cases, MANUAL cleanup, final
checks and preflight. Paired-capture replay runs offline afterwards. No fault
clear, clock change or power operation. It needs a current exact-image owner
authorization.

## First native attempt and correction

The approved session downloaded the press image and stopped at the walk's first
capture: the legacy oracle had no `MachineState` for a declaration without a
signal tower, while the PLC publishes it from its own classifier. Rollback, the
31 baseline cases and every final check passed; see the
[attempt record](Evidence/AB_PRESS_S3_EXIT_ATTEMPT_2026-10-25.md). The S3h oracle
now derives `MachineState` through the same classifier when no tower is declared,
and a repository test replays the press oracle over recorded native inputs: all
4,058 contract paths. 2,305 AB tests pass; the image is unchanged.

The [retry](Evidence/AB_PRESS_S3_EXIT_RETRY_ATTEMPT_2026-10-25.md) passed its
five access captures and stopped at the live-document restore: the host medium
is keyed by serial and root name, shared with genealogy, and the press correctly
refused documents at the genealogy revision. Rollback and all 31 baseline cases
passed again. The press walk now commissions the press as a new station: an
isolated, empty medium beside its output, seeded with the downloaded image's own
documents at the press revision, then the ordinary restore. 2,308 AB tests pass.

The [third attempt](Evidence/AB_PRESS_S3_EXIT_THIRD_ATTEMPT_2026-10-25.md) ran
most of the scope natively, all passing: medium restore, 2 access, 8
configuration and 14 typed rows (collision refused on both mailboxes), the first
four ST core cases and 49 paired captures. It stopped at the held mode-change
case, which waited for `Running`; the run level keeps it after a mode change
while the chain stands at step 0. The case now waits for the applied mode and
step 0, as the generated Unit behaves. Rollback and 31/31 baseline passed again.
The fourth session **passed**: 47/47 candidate rows, 85/85 paired captures,
86/86 independent replays, exact idle equivalence on 4,058 paths, generic
acquisition and scan (MaxScan 7,246 us, zero overlaps); rollback and 31/31
baseline again. See the [runtime record](Evidence/AB_PRESS_S3_EXIT_RUNTIME_2026-10-25.md).

Physical I/O identity/offline proof needs the real controller and modules and
stays separate from Echo. The consumer census (tools/tests reading legacy
surfaces) is due before S6. S4-S7 remain. V2 is inactive.

Work: `C:/work/fraktal-ab-s3-exit-20261025/` (`census_01/`, `press_01/`).
