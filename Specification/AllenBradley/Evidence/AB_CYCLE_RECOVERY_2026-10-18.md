# AB cycle, verdict and recovery acceptance — 2026-10-18

Non-normative, append-only evidence. Base commit `fa49adcc5`, with dirty source
snapshots, original logs, fixture outputs and hashes in the
[payload manifest](AB_CYCLE_RECOVERY_2026-10-18/manifest.json). Earlier evidence
is unchanged. The owner's current continuation request covers the bounded local
Echo fixture tests below; every native write checks the exact target and manifest.

## Changes and ownership

The carrier-off press previously incremented ScrapCount in its NOK branch and
GoodCount again at the shared finish. The generator now derives one private
eight-byte `FRK_T_CycleVerdictV1` record for looping chains with those existing
marks. The shared finish suppresses good after scrap, increments CycleCount and
clears the verdict latch. The Unit also clears the latch on reset, abort and
mode change, preserving lifetime counters. Projects add no wiring or reset call.
The added InOut parameter versions the Unit AOI with `_CountV1`; existing Unit
context and public counter paths do not change. Consumers must be regenerated
and imported together. The carrier-enabled fixture has its own commit/count
owner and receives no duplicate verdict record.

Part projection now publishes every canonical field for every configured result
slot even when empty. Name is empty, numeric values zero and InTol false until
occupied. Discovery indices therefore remain stable as records appear and clear.
This is a gateway change; PLC measurements remain authoritative.

The implementation reuses native AOI/UDT parameters, ADD/MOV/comparisons and the
existing ST/SFC/LD execution paths. A native counter does not infer the declared
part verdict at a shared finish; the private latch implements that portable
policy. No scheduler, alarm engine, native driver or PLC clock source is added.

## Native compiler proof for the carrier-off correction

Disposable `fraktal_ab_host_demo` declaration, all three AUTO renditions,
1756-L81E 38.011 seed. Studio 38.00, SDK 2.1.974, .NET 8 x86 offline host.
Both rows are offline compiler targets, not physical-controller acceptance.

Accepted source SHA-256:
`B47321FC3883C640BE523F7CF7082081846E37BA66B8918456981F2EF8E5ED22`.

| Gate | EchoController | PhysicalController |
| --- | --- | --- |
| SDK Open/Build/Save As and clean import | pass, 0 warnings/errors | pass, 0 warnings/errors |
| Source unchanged | pass | pass |
| Inventory and native SFC read-back | equivalent, 18 steps | equivalent, 18 steps |
| Executable bodies | 39, no differences | 39, no differences |
| Authored initial values | 18,672, no differences | 18,672, no differences |

Whole-cycle executable models run NOK then OK in ST/SFC/LD: counts progress
from `(Cycle=1, Good=0, Scrap=1)` to `(2,1,1)`. Whole generated Unit AOI tests
prove reset/abort/mode-change cleanup without clearing lifetime counters.
This correction has not been downloaded to a carrier-off or v33 controller.

## Exact live target and image

Local Logix Echo `127.0.0.1:44818`, slot 0, serial **601FC87B**, product
**Emulate 5580 Controller**, firmware **38.011** (pylogix `38.11`), controller
`FraktalPhase0`, GUID `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`.
The already downloaded Part fixture is unchanged, SHA-256
`49C6C33EC270ABC5798B41231F8046527A755A3C5FD91AD99013F4C1CE07A263`.
Manifest major 5, hash `75A1C353B12DF14F`. The
[download record](AB_ECHO_LOCAL_CARRIER_DOWNLOAD_2026-10-18.md) identifies the
backed-up original program and correlated ACD. No download, controller fault
clear, clock change or physical-controller operation occurred in this batch.

The harness requires an explicit arm flag, expected serial, exact selected
declaration, local credential file and new evidence output. Before every write
it checks loopback/slot/product/revision/serial and the native manifest. Writes
are limited to declared simulation inputs, the existing Sequence-last mailbox
and named configuration-set staging members. Private provider/internal tags
are never written. Login is the existing controller session; credentials and
request frames are absent from evidence. No gateway service is reconfigured.

## Configuration restore and initial negative runs

`live_ST_01` correctly refuses HOME START with diagnostic key 731,
`std.release.configRestoring`. Following the preceding fresh download,
StationCfg.SchemaVersion is zero. The gate is not relaxed or stamped directly.
`live_ST_02` completes the normal Keeper/broker LOAD_CONFIG_SET transaction under
the controller-authorized admin session; the station load completes restore.
The medium is first-commissioned at
`%LOCALAPPDATA%/Fraktal/ConfigSets/601FC87B-Press/live` and preserves station,
line and all three model documents. Reopening the medium matches all five
documents against actual PLC values; StorePresent=1, Failed=0, RestoreLost=0.
This is file reopening and successful restore, not a power/download-retention test.

The second run passes OK and handled NOK, then its hold assertion times out
because the harness queried `Held` instead of `OutImm_Held`. Native HeldScans
advances; correcting the harness makes the acceptance pass. Both negative runs
restore stimuli and logout; their original outputs remain in the payload.

## Live matrix

`live_ST_03.json` and `live_SFC_LD_01.json` contain **21 passing rows**, with
successful final restoration in each run:

| Case | ST | SFC | LD | Checked behavior |
| --- | --- | --- | --- | --- |
| OK | pass | pass | pass | received/started/processed order, one UID, Good +1, measured ram position 100 |
| Handled NOK | pass | pass | pass | ram fault decision, committed NOK reason, Scrap +1, Good unchanged |
| HELD/resume | pass | pass | pass | 750 ms held exceeds 500 ms timeout without fault; same part resumes and counts once |
| Abort | pass | pass | pass | one aborted event, no processed event or verdict count |
| Mode change | pass | pass | pass | present part closes once, no verdict count |
| Adopted child fault | pass | pass | pass | slide fault adopted; aborted event retains the Unit first-out |
| One-reset restart | pass | pass | pass | clear injected defect, one OperatorReset, next START processes normally |

These are simulation acceptance checks using the fixture's declared fault/hold
inputs. They do not establish functional safety or physical motion behavior.

## Live read and durable local sink

The final read-only acquisition records 16 actual events. A rejecting sink leaves
no cursor. Durable JSONL acceptance uses flush/fsync before cursor persistence;
reopening the cursor and delivering the same batch emits zero repeated records.
The first read explicitly reports the actual overwritten interval 1–101,
then acknowledges through sequence 117. No claim is made that those older
events were recovered. The retained publisher epoch is `[796037025,205869]`.
The sink is local; continuous network delivery and gateway-process restart
acceptance remain separate.

Final controller read: MANUAL, idle, Error/ErrorID/Aborted zero; all ten
simulation inputs restored to zero, rendition ST, access level zero. Scans
advance 152070→152101; the generic projection has 4,377 paths. Echo API reports
IsFaulted=false and Run. Lifetime counts are Good=10, Scrap=4, Cycle=14,
including the two completed cycles in the second initial run. The controller
clock reports 1998 timestamps with TimeSynchronized=false; no clock correction
or uniqueness-under-clock-replay claim is made.

## Regression gates and remaining scope

- Full AB suite: **1,782 tests pass** in 239.322 seconds. Expected refusal/CLI
  diagnostics are retained in the successful original log.
- Final targeted carrier/counting/harness suite: **28 tests pass**, including
  whole-Unit cleanup, stable measurement paths and wrong-target/manifest/private
  write refusals. This follows the final harness additions.
- Root specification/contracts/strict consistency gates pass; **74 root tests**
  pass. Final whitespace validation passes.

This closes the local Echo lifecycle/recovery acceptance and the two identified
source defects. Device carriers, genealogy, resource-change producers,
SignalTower/LAMP_TEST, native alarm/health provider qualification, browser
acceptance and physical power/download/upgrade retention remain open. The AB
port is not complete relative to every TC3 capability.
