# AB SignalTower, native timer and configuration upgrade — 2026-10-18

Non-normative, append-only evidence. Base commit `fa49adcc5`, with exact dirty
source snapshots, logs, native outputs and hashes in the
[payload manifest](AB_SIGNAL_TOWER_2026-10-18/manifest.json). Earlier records
remain unchanged. Scope: the optional semantic tower and the existing local
Part fixture, not physical lamps, horn wiring or a production security policy.

## Implemented ownership and native reuse

`Application.signal_tower=SignalTower(...)` selects one generated scan service,
versioned all-DINT semantic status and private configuration/bookkeeping.
Without the profile, no tower data, timer, scan service or read is emitted.
LAMP_TEST remains refused by name for an absent profile. Public fields are
read-only; configuration, request scratch and the timer have External Access None.

The service consumes the existing active alarm table and pending decision.
Machine-state priorities and upstream/downstream step attribution are now
defined once for both native generation and gateway classification. With the
tower present, the gateway publishes its native MachineState and seven semantic
outputs rather than deriving another state. Shelving removes annunciation but
does not remove the blocking state or DOWN indication. Colour/site choices are
startup configuration, as TC3's SetSignalTowerConfig; no config writer is added.
Only the project hardware driver owns electrical mapping.

Native **TONR with FBD_TIMER** owns elapsed time, reset and completion in ST.
One timer is allocated only for the selected profile and scanned unconditionally.
The runtime defaults nonpositive duration to 3 seconds and clamps to 30 seconds;
request DurationMs cannot replace it. BUSY and already-active tests refuse.
The mailbox's previous POWER_CONTROL gate assignment is corrected to Core
MANUAL, ordinal 2. Existing authentication, action policy and Sequence-last
acknowledgement remain the authority.

Rockwell documents [TONR in Structured Text with FBD_TIMER](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-03/contents-ditamap/instruction-set/timer-and-counter-instructions/timer-on-delay-with-reset--tonr-.html).
This uses the native timer, not the ladder-only TON or a new scan-period clock.
The 5580/v38 compiler and runtime results below qualify this narrow use. Native
module health, alarm-provider migration and the general time-source review
remain separate gates.

The generic HMI now renders a tower even when a health provider is absent,
without inventing health/clock measurements. It retains the existing MANUAL
act-or-explain control and disables test while TestActive. No station page is added.

## Configuration upgrade

Adding runtime fields changes discovery/configuration revision even though the
editable value schema is unchanged. Preflight caught the old live documents
carrying revision **7709123**, while the new declaration carries **15367118**.
The shared set validator now recognizes the exact otherwise identical declaration
without the tower, including its existing supported predecessor variants.
Unrelated revisions and malformed values still refuse; all record validation
and staged atomic commit remain. Longer revision expressions group at most five
AND terms per level, preserving the v33 compiler restriction already recorded
by the binding. This is not blanket acceptance of arbitrary old configurations.

Before download, all five stored station/line/model documents matched the PLC.
The new image restores them through the normal Keeper/broker and controller
LOAD_CONFIG_SET transaction. The native run verifies every value/identity field
while allowing only document revision metadata to advance. Reopened documents
match the resulting PLC values; StorePresent=1, Failed=0, RestoreLost=0.
This records this download upgrade, not power-loss or general schema migration.

## Compiler and read-back

Fixture `fraktal_ab_tower_demo` derives from the previous local Part fixture:
1756-L81E 38.011, 10 ms periodic task, no physical I/O, output updates disabled,
all three AUTO renditions, 16-event host ring and four Part result slots.
Studio **38.00**, Logix Designer SDK **2.1.974**, .NET 8 x86.

Final generated L5X SHA-256:
`03BE7A3D4F16118E328673F096EA06C250D2D64FC14027BE043B824F535A99ED`.
Final source regeneration reproduces these exact bytes.

| Gate | EchoController/prepared ACD | PhysicalController offline |
| --- | --- | --- |
| Native Build / clean import | pass, 0 warnings/errors | pass, 0 warnings/errors |
| Construct inventory | equivalent | equivalent |
| SFC content | equivalent, 21 steps | equivalent, 21 steps |
| Executable bodies | 42, no differences | 42, no differences |
| Authored initial values | 20,446, no differences | 20,446, no differences |

The post-download SDK export also matches all these executable/initial-value
checks. The first compiler run rejected the use of nonexistent alarm members
State/Severity/Shelved. Correcting them to the actual Act-prefixed columns
produces the accepted image; the rejected source/log remain in the payload.
A subsequent source-only revision adds the configuration compatibility gate
before the final image is compiled/prepared/downloaded.

Growth against the preceding Part image: +4,974 ST source bytes, +65 statement
terminators, +112 lines, no new RLL rungs, +844 counted declared data bytes.
The report explicitly excludes the private native FBD_TIMER and AOI storage.
These are source/layout trends, not compiled memory savings or physical fit.
The generated external-access allow-list audit passes, including private timer,
configuration/bookkeeping and the existing public manifest/reports/catalog.

## Authorized deployment and exact target

The owner explicitly answered **“Download and run the checks”** for this new
fixture after the prepared native result and current backup were available.
Every controller-changing operation checks the exact local target immediately
before use: **127.0.0.1:44818, slot 0, Echo serial 601FC87B**, product Emulate
5580 Controller, revision 38.011, GUID `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`.
The emulator owns the local listener. Controller `FraktalPhase0`, chassis
`FraktalPhase0Chassis`. The SDK changes Program→download→Run; no fault clear,
clock set or physical-controller operation occurs.

Current-program upload backup, retained locally:
`C:/work/fraktal-ab-tower-20261018/echo_before_tower.ACD`, SHA-256
`88C9A33A6C6B13C925EBA85C2659BD8FDEA2931408F6BDC9D4708D4E9108D2FE`.
It captures the preceding Part image and runtime state. The ACD backup and its
companion upload L5X remain outside the repository.

Prepared ACD SHA-256:
`2DE65D944D6A589D3FD6E876703CF83D33E2E99F9FC9DFCDE1CDBC360E40010E`.
Correlated post-download `tower_03.ACD` SHA-256:
`04D23EF06D698259823947A85DD22A6DFEDB168641537D116637EC3A6E9530D9`.
Native SDK reports DownloadCompleted=true, FinalMode=Run. Manifest major 5,
hash **EA7BCE24FDA311EB**. No gateway service is reconfigured; a gateway for
this lab image must select `FRAKTAL_AB_DECLARATION=fraktal_ab_tower_demo`.
The major-4 direct-CIP spike remains incompatible.

## Live acceptance

Final `live_05.json`: **31 passing rows**, restored=true and policyRestored=true.
The named fixture uses only the existing guarded mailbox, declared simulation
inputs and ordinary configuration staging. No private provider/timer/output
tag is written. The local PIN file and transient login proofs/frames are not
included in evidence. Provisioned verifier data remains part of the exact fixture.

| Tower/upgrade case | Result |
| --- | --- |
| Configuration preserved | all five documents retain values; old-revision upgrade observed in live_02 |
| Logged-out MANUAL refusal | ordinary SET_ACCESS_LEVEL sets MANUAL=1; level 0 receives accessDenied |
| MANUAL independent of POWER_CONTROL | MANUAL=0 / POWER_CONTROL=4 accepts level-0 lamp test |
| All outputs active | five colours plus horn and TestActive true |
| Already-active refusal | refuses without refreshing the timer |
| Logout/disconnect timeout | connection closed with no reads/writes for 3.2 s; first reconnect read is off, observed 3.214 s |
| Producing | native Green follows running/held AUTO state |
| BUSY refusal | lamp test refused while the Unit runs |
| Rationalized fault | adopted 10101 gives DOWN/red, green off and horn off, matching its MED priority |
| Operator decision | pending decision drives Blue |

The remaining **21 rows** run the existing Part matrix against this new image,
seven each for ST/SFC/LD: OK, handled NOK, HELD/resume beyond the command timeout,
abort, mode change, adopted child fault and successful restart after one operator
reset. Verdict counts, event/identity continuity, measurements and recovery pass.
HIGH/horn and white-versus-blue site choices additionally match the actual TC3
mapper across the executable-model matrix; normal HIGH annunciation is not
claimed from the MED cylinder injection. The horn is exercised natively by lamp test.

Initial native harness failures are retained. `live_01` assumed the fixture's
zero-level action policy required login; it records failure and restored=false
because the accepted test was still active at its short cleanup boundary.
Later cleanup waits for native expiry. `live_02` completes the cross-revision
restore and gate/timeout checks but incorrectly expects a horn for reason 10101;
the registry correctly defines MED. It restores successfully. The corrected
check consumes the registry priority; live_03, live_04 and final live_05 pass.
No rationalization is changed to make an assertion pass. live_05 strengthens the
disconnect case to leave the connection closed for the complete test interval.

## Final read and regressions

Final independent read: Run and IsFaulted=false, MANUAL/idle, Error/ErrorID/
Aborted and scan-order failure zero. All ten simulation inputs and the original
twelve gate requirements are restored to zero; session level zero. The test
and all semantic outputs are off; Part is absent. Scans advance **64464→64506**,
major/minor fault bits zero, native task maximum scan **1,167 µs**. Projection
contains **4,384 paths**. The host ring is healthy and has wrapped after the
tests; its bounded history is not represented as complete lifetime history.
The clock remains unsynchronized; no clock/time-source qualification is inferred.

- Full AB suite: **1,791 tests pass** in 252.281 s. Two new harness CLI guard
  tests added afterward are covered by the final targeted run.
- Final targeted tower/harness/set-validation suite: **50 tests pass**.
- Generic HMI widget/card tests: **19 pass**; targeted analyzer reports no issues.
- Root spec/contracts/strict consistency gates and **74 root tests** pass;
  final whitespace check passes.

The source and local Echo SignalTower/LAMP_TEST gap is closed. Electrical/HAL
mapping, physical lamps/horn, browser acceptance, device carriers, genealogy,
resource-change producers, native alarm/health-provider qualification and the
broader account/power/upgrade retention matrix remain open. This is not full
TC3 parity or a physical v33/v38 deployment claim.
