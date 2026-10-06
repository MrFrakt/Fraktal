# AB press port - completion sequence

Owner request: finish the AB port, 2026-10-04. This extends the earlier Phase 6
boundary; the September audit's original "Deliberately not planned" list remains
historical. Control power remains deliberately excluded. This is an implementation
plan, not a conformance claim or permission to change the controller.

Read [AGENTS.md](../../AGENTS.md), the
[current guide](../Guides/AB_NEW_PROJECT_GUIDE.md), the
[parity audit](../Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md) and the normative
Core/Part III clauses before each implementation. TC3 is the behavioral oracle;
AB keeps generated composition, DINT contracts and one authoritative declaration.

## Deployment boundary first

Press75 is the owner-confirmed completed-download memory baseline, at 0/0
followed by Run. Online data/logic uses 758,568 / 786,432 bytes, with 27,864
available and a 27,376-byte largest free block. See
[fit evidence](Evidence/AB_LINE_V2_PRESS75_NATIVE_FIT_2026-10-04.md). Press70's historical eleven
native regression suites pass 159 rows with independent restoration, S3 passes
6/6, current M-101 export and the live production HMI repository read pass.
See [native acceptance](Evidence/AB_PHASE6_PRESS70_NATIVE_ACCEPTANCE_2026-10-04.md).
Chrome modal acceptance and physical model/credential upgrade retention remain
separate. Press69 failed Verify; no historical evidence is broadened.

Do not re-download the old press70 three-bank image over owner-created M-101.
Any later artifact requires a fresh expanded modelCodes/all-bank capture; the
[catalog helper](Evidence/AB_PHASE6_CATALOG_IMAGE_2026-10-04.md) preserves stable
indices without layout growth. No disposable native model may be created:
obtain an owner-selected code/source for any append-only creation check.
Guard exact serial/build before every authorized native stage; owner performs
downloads and write-enabled gateway restarts. The next implementation is line
data and weekday/duration shifts, followed by the remaining stages below.

Stage 2 is now loaded as corrective `C:/work/press75.L5X` (SHA
82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5), manifest
94E302F650BA1DB5 / 9757442. It enables a Line owner, four weekly calendar rows,
eight controller-owned history rows and generic weekday/history UI. Fresh,
identical serial-guarded captures preserve M-101/all four banks and current
records. Native fit passes; boundaries/retention/browser have separate acceptance;
mirror/shared-root composition remains unbound. See
[correction evidence](Evidence/AB_LINE_V2_ALARM_MEMORY_FIX_2026-10-04.md).
Press71 reported out-of-memory in LineValidate. Press72 reduces that routine
to six unordered row-pair mask checks; its tags/layouts/manifest remain equal.
Press72 verified/compiled but failed download linking at LineValidate. Press73
reduces discovery reserves and shares ST/SFC step-entry bookkeeping, with
declared data/source/statement totals below accepted press70. All three native
renditions, chart history, four users and permissions remain. Press73 also
fails with a final global memory error; the owner estimates 799,428 / 786,432
data/logic bytes (12,996 over), while I/O uses 2,640 / 1,048,576. Press75 shares
native alarm open/close code, groups rationalized priority branches and emits
restore defaults once. It removes 240 ST terminators without layout/data growth;
fit now passes by owner full-download confirmation and online Capacity. The
799,428 estimate and 758,568 online use have different measurement bases;
their difference is not claimed as measured compiled saving. Fresh complete
manifest/configuration reads preserve the four-model catalog. Future controller
growth is compared with press75, without broadening its acceptance scope.

Press75 native acceptance now supplies 159 successful restored regression rows
across eleven suites and 17 Line assertions. The Line vector covers whole
13-field export/import and atomic validation, effective minimum permissions,
a twelve-hour weekend-only shift and natural end/restoration. It preserves two
actual history closures, restores all captured config/banks/session and passes
S3 6/6 (max scan 8,384 us, no fault/overlap) and fresh gateway health. Three
apparatus corrections add zero PLC growth; interrupted runs remain failures.
See [native acceptance](Evidence/AB_LINE_V2_PRESS75_NATIVE_ACCEPTANCE_2026-10-04.md).
Chrome controls and physical Line retention are separate owner gates, and
mirror/shared-root transport remains unbound. This is not full port closure.

## Implementation order after acceptance

The owner now prioritizes missing line data. Implement stage 2 before Part
traceability once the current fit/native acceptance boundary is established.
Refresh the TC3 handoff and AB new-project guidance at final port closure.

| Stage | Work and owning level | Acceptance needed |
| --- | --- | --- |
| 1. Part traceability | Core 3.16; opt-in carrier declaration, bounded native Part context and framework-owned event plumbing; press chains request canonical received/started/record/processed/aborted events through their normal services | Exact ST/SFC/LD outcome parity, unique BY_POSITION identity, verdict/count consistency, abort behavior, fail-closed read/write errors; generic Part HMI projection |
| 2. Line data and shifts | Core 3.8e/8.5.2; composition-owned line beside roots, referenced by roots, never a child/super-root; retained data, current shift and bounded history; owner-requested weekday selection and explicit limited shift duration | Owner/read-only access semantics, root sharing, complete write validation, weekly/overnight boundaries, inactive intervals, history bounds, clock quality and retention |
| 3. Signal tower | Audit the TC3 press declaration and optional profile; reusable type derives lamp/sound requests from authoritative machine/alarm state; enable LAMP_TEST only for a real declared capability | Type tests and test timeout, no arbitrary output write, verified electrical/HAL mapping before physical claim; absent hardware stays visibly unclaimed |
| 4. Host event projection | Existing frozen host-event contract, fed by controller event authority; gateway transport/projection owns northbound delivery | Ordering, sequence gaps/overflow, reconnect and no double counts; documented transport delivery limits; no HMI accumulation replacing PLC history |
| 5. Description and probes | Audit Nameplate/IDTA and I/O connection-state omissions; version any frozen contract extension, reuse existing fieldbus identity and health owners | Canonical manifest/projection agreement, version refusal, named supported GSV attributes on the actual family; unsupported CPU/free-memory remains unavailable |
| 6. Running-model set integration | Audit the shared AB/TC3 deliberate refusal; use prepare/readiness/commit recipe path, never direct live ParCfg overwrite | Complete validation before application, ordinary Changeover gates, abort rollback and no partial recipes; extend capabilities only after this route exists |
| 7. Final closure | Current feature census, targeted security/retention regressions, browser acceptance and deployment guidance | Updated AB_ABSENT/refused-command reasons, scoped S9 rerun, packaged AB deployment acceptance, exact artifacts/hashes and remaining platform exclusions |

Each native stage follows the established loop: one offline implementation,
meaningful tests and mutations, generated artifact with size comparison, commit,
owner Verify/completed download, guarded hardware evidence and browser acceptance.
Gateway-only stages still prove live activation and freshness; they need no PLC
download when emitted PLC bytes are unchanged. Generic HMI features are shared,
never AB-specific screens. Extend the new-station template where applicable.

## Added shift-calendar requirement

The owner additionally requests per-shift active weekdays, including a special
12-hour shift only on weekends. This is implemented offline in stage 2; press70
does not add line data or this editor. The released TC3 ST_ShiftCalendar is daily,
start-only and gapless: every used shift ends at the next used start. Merely
hiding weekday labels cannot implement a 12-hour interval followed by off time.

Core 8.5.2(a) now defines the additive V2 contract before its binding. The
versioned representation gives each shift Monday-Sunday selection plus start and
duration; seven-bit day selection and bounded duration are PLC-validated data.
All days selected preserves the daily scheduling use case. Migration from the
old start-only calendar preserves its next-start end semantics; never silently
convert it into a different duration. Preserve the existing UTC offset policy.
The final type/version/migration belongs to the shared contract, not an AB-only
screen. Do not mutate a released structure without the required schema/version.

Scheduling/editor acceptance includes:

- Seven weekday checkboxes for each shift, persisted as line configuration and
  mirrored whole to every referencing root. Use the existing interaction preset
  sizing/spacing; explain the selected days and end time in the generic editor.
- Example: Saturday and Sunday, 08:00 start, 12 hours duration ends at 20:00 on
  each selected day. Weekday and 20:00-08:00 intervals are unscheduled; they
  must not be counted as a continuation of the preceding scheduled shift.
- Overnight selection applies to the shift's starting day. Sunday 20:00 for
  12 hours can end Monday 08:00 even when Monday is unchecked. Prove week wrap,
  adjacent boundaries, duplicate starts on different days and weekly overlap
  rejection with half-open intervals; validate the complete calendar before commit.
- Represent unscheduled time explicitly in current statistics/accounting instead
  of inventing an active shift or discarding production totals. Finalize its
  record/reset policy in Core 8.5.2 alongside the extension.
- Calendar edits take effect at the defined next boundary; closed history remains
  immutable. Unsynchronized boundaries still carry the existing time-quality
  warning; do not stop accounting, invent a valid clock or set the clock.
- Test retained edits, full-week/default migration, no selected days, invalid
  masks/durations, shift history truncation and per-root counter/OEE attribution.

This supersedes the old daily-only assumption for the requested implementation;
it does not claim native AB acceptance or a compiled TC3 V2 implementation.

## Memory and evidence rules

Keep the four-user ceiling and proportional manifest reserves. Reuse private
scratch, bounded native loops and optional declarations. Record declared data,
per-routine ST source/statements/lines and RLL deltas against the last completed
download. These are trends, not compiled memory. If an item exhausts memory,
optimize its owning implementation before growing another feature; do not weaken
permissions, freshness, input validation or condition reports to obtain fit.
Record Studio Capacity Estimate for both I/O and data/logic areas after Verify
of the exact artifact, before another download. Track estimated remaining
headroom against the native completed-download baseline; code/source counts
cannot predict compiled saving. Press73 exceeds data/logic by 12,996 bytes.
Do not grow Part/storage features until this deficit and native fit are resolved.

Native snapshots, audit/alarm events, visited steps and verdict records remain
controller-owned. Fast events cannot be reconstructed by gateway/HMI polling.
Publish only consumed profiles; omit absent capabilities rather than rendering
successful-looking placeholders. Keep released layouts additive/versioned.

Evidence is append-only. Distinguish offline checks, Studio Verify, completed
download, native command results, owner browser acceptance and physical retention.
Keep exact failed runs and restoration results. Never edit old PASS records to
broaden scope. No transient seed, alias or private credential may become a write
surface. Capture commissioned configuration before generating a replacement;
configuration seeding does not prove credential/download migration.

## Platform exclusions and completion criteria

The L24ER has no Integrated Motion: an axis/PartFeed claim requires another
supported controller and S14 proof. The TC3 press itself leaves PartFeed unbound;
do not simulate successful axis support. MANUAL_HELD needs an actual hold-to-run
target contract; finite pneumatic manual commands do not establish it.
Control-power and certified safety remain excluded/unclaimed; ordinary process
two-hand/air permits do not acquire a safety certification through this port.

The S1 clock probe, full persistence/durability/upgrade matrix and other
family/firmware acceptance are separate gates. Time synchronization is observed
read-only until the owner authorizes a clock operation. Packaging/signing/source
distribution follows the deployment guide and [LICENSING.md](../../LICENSING.md).

The press port is complete only when the requested applicable stages have native
and browser evidence, with a current gap census and explicit hardware/profile
exclusions. Passing a source suite or the first corrective download is not that
completion claim. Next gate: restored native Line/browser/retention acceptance
on loaded press75; then continue the remaining stages.
