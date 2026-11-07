from pathlib import Path
import datetime,hashlib,json,re,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
NAME='AB_S6_COLLAPSE_C5B3_PHASE5_OFFLINE_2026-11-06'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
labels=['ab_suite_01','root_tests_02','phase5_focused_tests_01','phase5_replay_tests_01','phase5_fact_accounting_01','phase5_predicates_01','layout_proof_03','token_proof_03','genealogy_reuse_02','runtime_bindings_01','declaration_import_01','next_hx_inventory_01','input_bindings_01','managed_tools_01','preparation_01','ab_spec_01','ab_contracts_01']
for label in labels:assert read(W/(label+'_exit.json'))['exitCode']==0,label
counts={}
for label in ('ab_suite_01','root_tests_02','phase5_focused_tests_01','phase5_replay_tests_01'):
 matches=re.findall(rb'Ran ([0-9]+) tests?',(W/(label+'.log')).read_bytes());assert matches,label
 counts[label]=int(matches[-1])
assert counts==dict(ab_suite_01=2696,root_tests_02=85,phase5_focused_tests_01=62,phase5_replay_tests_01=27),counts
freeze=read(W/'tools_freeze_01.json');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==freeze['head']
for row in freeze['files']:assert sha(R/row['path'])==row['sha256'],row['path']
for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256'],row['path']
prep=read(W/'preparation_01.json');proof=read(W/'token_proof_01.json');layout=read(W/'layout_proof_01.json')
cap_press=read(W/'prepare_01/press_capacity.json');cap_shelving=read(W/'prepare_01/shelving_capacity.json')
assert prep['passed'] and proof['passed'] and layout['passed']
assert cap_press['VerifiedFit'] and cap_press['SourceUnchanged']
assert cap_shelving['VerifiedFit'] and cap_shelving['SourceUnchanged']
up,ap,totalp,pctp=(cap_press[k] for k in ('UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent'))
us,as_,totals,pcts=(cap_shelving[k] for k in ('UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent'))
deltap=up-read(Path('C:/work/fraktal-ab-c5b3-control-20261106/prepare_01/press_capacity.json'))['UsedStandardBlocks']
deltas=us-read(Path('C:/work/fraktal-ab-c5b3-shelving-control-20261106/prepare_01/capacity.json'))['UsedStandardBlocks']

report=f'''# S6 C5b3 Phase 5 metrics and reports - offline qualification

Work started on 2026-11-06; final gates completed on {datetime.datetime.now().date()}
(America/Mexico_City). UTC process times are retained in the receipts.

The Phase 5 metrics, OEE, profiler, command-timing, state-flag, system-health
and run-style harness (`fraktal_ab_phase5_execute.py`) passes offline on
canonical CIP rows and O10 private observations. Parent `{freeze['head']}`. The
owner authorizes commit and push on main. No controller connection, download,
tag write, mode change, fault/TASK clear, clock, power or vendor-state
operation ran.

## Results

- **{counts['ab_suite_01']:,} AB tests** by discovery from tools, **{counts['root_tests_02']} root tests**, **{counts['phase5_focused_tests_01']} focused
  Phase 5/policy/capture/document/schema checks**, **{counts['phase5_replay_tests_01']} native-capture replay
  and storage checks**, and all root gates pass.
- **All 21 Phase 5 `px.row(...)` predicates and all 16 wait predicates** are
  preserved without weakening tolerances, logical operators or value checks.
  Direct legacy projection and layout calls in `fraktal_ab_phase5_execute.py`
  drop from **18 to 0**.
- **O10 grows from 102 to 141 private facts (+39)** across `Unit`, `Door`,
  `PartSlide`, `PartPresentSensor`, `PressRam`, `Profiler`, `AlarmActive`,
  `AlarmRing` and `Oee`, shared by `fraktal_ab_press_s6_collapse_echo38` and
  `fraktal_ab_press_s6_shelving_echo38` (`{layout['newUdtName']}`). All 39 new
  facts replay across all **86 accepted native press captures**; canonical
  metric/report views (`oee_card`, `machine_summary`, `run_style_offer`,
  `profiler_summary`, `timing_row`, `alarm_ring_entry`, `state_flags` and
  `system_health`) match the native projection across all 86 capture pairs.
- **Both v38 press profiles build and read back** on `EchoController` and
  `PhysicalController` and pass SDK, native access and default audits:
  - Normal press (`fraktal_ab_press_s6_collapse_echo38`): **{pctp}%** Studio
    Capacity (**{up:,} used / {ap:,} available / {totalp:,} Blocks**,
    **{deltap:+,} used** versus prior C5b3 press). Prepared source SHA-256
    `{prep['profiles']['press']['sourceSha256']}`; prepared ACD SHA-256
    `{prep['profiles']['press']['acdSha256']}`.
  - Shelving acceptance profile (`fraktal_ab_press_s6_shelving_echo38`):
    **{pcts}%** Studio Capacity (**{us:,} used / {as_:,} available / {totals:,}
    Blocks**, **{deltas:+,} used** versus prior C5b3 shelving profile, **+36**
    versus the normal press). Prepared source SHA-256
    `{prep['profiles']['shelving']['sourceSha256']}`; prepared ACD SHA-256
    `{prep['profiles']['shelving']['acdSha256']}`.
- **Exact token and schema proof:** after removing the 39 appended O10 copy
  statements (+552 ST tokens) in `FRK_Press_CopyFixtureObservation` and
  normalizing C4c's code-derived AOI signatures (`FRK_M_CylinderR8C4633CD7D0Rev`,
  `FRK_U_Press_CountV1R8C4_C4C17B3C23`), V5 localization key renumbering and
  four equivalent text-pool slices, all **66 routines** match the prior C5b3
  sources token-for-token (`125,551 -> 126,103` ST tokens on the normal press;
  `125,560 -> 126,112` on the shelving profile). Between the two profiles, **65
  routines are identical** and `FRK_Press_ScanHealth` differs only by the 9
  tokens of `FRK_Press_SystemHealth.Bad[2] := 1;`. Public schema, initial
  values and all three derived manifest hashes match between both press
  profiles and pass the pre-collapse schema-identity gate with zero uncovered
  differences or unused declarations.
- **Genealogy (`fraktal_ab_genealogy_s6_collapse_demo`) is byte-identical** to
  its sealed C5a source (`07C771DF2BEBAAD59CE33611579F70ACFE92B76BB0A658783A761614E36DB417`),
  reusing its hash-bound v38 builds, read-backs and 60% Studio Capacity.
  Shipping HMI/Dart sources (84 files) and both prepared runtime executables
  match the committed C5b2 bindings, reusing its 44 Dart tests.

## Ownership and scope

In collapsed images (`canonical_collapse=True`), C1/R3 removes `TimCount`,
`TimLast`, `TimMin`, `TimMax` and `TimAvg` from module contexts because the
cylinder AOI writes directly to its canonical leaf `Timing.Rows[0..1]`.
`fraktal_ab_fixture_reads.py` therefore exposes `TimCount` and `TimLast` on
cylinder surfaces (`Door`, `PartSlide`, `PressRam`) as canonical public aliases
backed by `{{module}}/Timing/Rows[1..2]/Count` and `Last` under the same scan
proof, while `Busy`, `DoneCount`, `OutImm_Extended`, `OutImm_Held` and
`RunCount` on cylinders, `OutImm_Value` on `PartPresentSensor`, and `HoldRun`,
`Issued` and `StepPending` on `Unit` are observed through O10. Because C4c
derives AOI parameter/local classification from `fixture_observation`, observing
those five cylinder fields promotes them from `Local` to `Output` parameters on
the cylinder AOI and updates the derived C4 signature hashes and V5 field
tables; `fraktal_ab_phase5_execute.py` resolves refusal diagnostic keys from
the deployed PLC command table (`views.numeric_key`) rather than generator-side
ordinals.

Canonical `SupportedRunStylesPublished` on the PLC root uses a 0-based lower
bound (`0..2`), whereas the legacy Python projection indexed it `1..3`;
`views.run_style_offer` handles each representation without changing the case
assertion. `views.state_flags` validates `StateFlagCount` before and after
reading the active rows, and `down_time_row` brackets its canonical OEE read
with `read_oee` so `DownMs` remains paired with the native `Epoch`, `DownS` and
`DownRemUs` sample counter.

Phase 5's `health_rows` requires both the published `SystemHealth` facet and a
standing reason-21 (`CONTROLLER_METRICS_UNAVAILABLE`) warning in `AlarmActive`
with `Blocking == 0`. That precondition is satisfied by
`fraktal_ab_press_s6_shelving_echo38` after its second health sample, while
`fraktal_ab_press_s6_collapse_echo38` preserves the platform exclusion
(`require_controller_metrics=False`). Dedicated executed-ST tests in
`test_fraktal_ab_phase5_canonical.py` prove both behaviors offline. In S6-Q,
Phase 5's `health_rows` runs during the dedicated shelving acceptance phase or
with its precondition explicitly accounted, while the normal press keeps its
platform exclusion.

## Failed runs and remaining work

All failed control runs are retained in the sealed evidence:
- The first three `run_logged.py` invocations passed full paths and `--` as the
  label/command arguments; `run_logged.py` rejected the non-alphanumeric label
  before opening a log file.
- `generate_press_01`, `generate_shelving_01` and `generate_genealogy_01`
  invoked the declaration modules directly instead of `fraktal_ab_generate.py`,
  producing empty logs and causing `layout_proof_01`, `token_proof_01` and
  `genealogy_reuse_01` to fail with `FileNotFoundError`.
- After generating the L5X files in `*_02`, `layout_proof_02` assumed the 39
  new facts were appended at the tail of the flat UDT rather than grouped per
  surface in declaration order, and `token_proof_02` indexed `DECLARATIONS`
  directly for `fraktal_ab_press_s6_collapse_echo38` instead of `.get(...)`.
  Corrected `layout_proof_03`, `token_proof_03` and `genealogy_reuse_02` pass.
- `root_tests_01` passed `-t .` to `unittest discover -s tools`, which requires
  `tools/__init__.py`; `root_tests_02` omits `-t .` and runs all 85 root tests.

The updated source inventory (`next_hx_inventory_01.json`) confirms **0 direct
legacy calls across 21 row sites** in `fraktal_ab_phase5_execute.py`, leaving
3 direct legacy calls in `fraktal_ab_part_execute.py`, the genealogy wrapper
(`fraktal_ab_genealogy_execute.py`), inherited runners and the standalone
canonical press launcher (`fraktal_ab_press_canonical_execute.py`). Frame and
staged-service retirement with V6.12 follow in C5c, then C6/C7, native S6-Q,
final deletion/census and specification activation. Under O2, hardware-only S7
acceptance remains deferred without a date as a declared exclusion.

Owner edits in `.vscode/settings.json`, the Siemens Manifest README and root
`analysis_options.yaml` are preserved and excluded. No credentials are archived.

[Payload and hashes]({NAME}/artifact_manifest.json) bind source inputs,
outputs and failures. ACD/L5X/EXE artifacts remain private and hash-bound.
See the [working notes](../AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md)
and [plan](../AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).
'''
with (R/'Specification/AllenBradley/Evidence'/f'{NAME}.md').open('x',encoding='utf-8',newline='\n') as out:out.write(report)

notes=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md'
with notes.open('a',encoding='utf-8',newline='\n') as out:out.write(f'''

## C5b3 Phase 5 metrics and reports - offline qualification

The [Phase 5 migration record](Evidence/{NAME}.md) passes offline:
{counts['ab_suite_01']:,} AB tests, {counts['root_tests_02']} root tests, {counts['phase5_focused_tests_01']} focused checks and {counts['phase5_replay_tests_01']} native-capture
replay/storage checks pass. `fraktal_ab_phase5_execute.py` has zero direct
legacy projection or layout calls; all 21 row predicates and 16 wait predicates
are preserved. O10 grows from 102 to 141 facts (+39) in `{layout['newUdtName']}`,
shared across the normal press and the shelving acceptance profile. Cylinder
`TimCount`/`TimLast` are read as canonical public aliases from `Timing/Rows[1..2]`
because C1/R3 removed duplicate timing arrays from collapsed module contexts.
All 39 added private facts and all canonical metric/report readers (`oee_card`,
`machine_summary`, `run_style_offer`, `profiler_summary`, `timing_row`,
`alarm_ring_entry`, `state_flags` and `system_health`) match across all 86
accepted native press captures.

Promoting the five asserted cylinder fields to AOI `Output` parameters under
C4c updates the derived C4 AOI hashes and V5 field/localization numbering;
refusal keys in Phase 5 resolve from the deployed PLC command table via
`views.numeric_key`. After removing the 39 appended O10 copy statements (+552
ST tokens) and normalizing C4c AOI names, V5 numeric keys and four equivalent
text-pool slices, all 66 routines match the prior C5b3 sources token-for-token
(`125,551 -> 126,103` ST tokens on the normal press; `125,560 -> 126,112` on
the shelving profile). Both v38 profiles build/read back on both targets, pass
SDK/access/default audits, and fit at {pctp}% Studio Capacity ({up:,} Blocks on
normal press, {deltap:+,}; {us:,} Blocks on shelving profile, {deltas:+,}).
Genealogy remains byte-identical to C5a (60% Capacity), and shipping HMI/Dart
sources and runtime executables remain hash-bound to C5b2 (44 Dart tests).

Phase 5's `health_rows` requires standing reason 21 (`CONTROLLER_METRICS_UNAVAILABLE`),
which `fraktal_ab_press_s6_shelving_echo38` supplies after its second health
sample while `fraktal_ab_press_s6_collapse_echo38` keeps `require_controller_metrics=False`.
Next in C5b3: migrate `fraktal_ab_part_execute.py` (3 direct legacy calls),
`fraktal_ab_genealogy_execute.py`, inherited runners and
`fraktal_ab_press_canonical_execute.py`, then retire Frame/staged endpoints and
publish V6.12 in C5c before C6/C7 and native S6-Q.
''')

plan=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
plan_text=plan.read_text(encoding='utf-8')
target='''**C5b3 shelving acceptance profile, offline follow-up.**
`fraktal_ab_press_s6_shelving_echo38` inherits the collapsed press and changes
only `SystemHealth.require_controller_metrics` to true. This is an
acceptance-only requirement: the existing health/alarm owner opens reason 21
after its first-sample guard. The normal press retains its exclusion. The
original shelving eligibility and restoration guards remain unchanged. See
the [offline qualification](Evidence/AB_S6_COLLAPSE_C5B3_SHELVING_OFFLINE_2026-11-06.md).
Positive native shelving remains S6-Q after C7; this profile is not a native
acceptance result. Its exact image must be regenerated and qualified after
the remaining collapse increments.'''
replacement=target+f'''

**C5b3 Phase 5 metrics and reports done offline, 2026-11-06** ([evidence](Evidence/{NAME}.md)).
`fraktal_ab_phase5_execute.py` reads OEE, machine state, run styles, profiler,
command timing, state flags and system health from canonical CIP rows and O10
observations (141 facts total, +39 in `{layout['newUdtName']}`), with zero
direct legacy projection or layout calls and all 21 row predicates and 16 wait
predicates preserved. Cylinder `TimCount`/`TimLast` read from canonical
`Timing/Rows[1..2]` aliases; all 39 added private facts and all Phase 5
canonical metric/report views replay identically across all 86 accepted press
captures. Both v38 press profiles (`fraktal_ab_press_s6_collapse_echo38` and
`fraktal_ab_press_s6_shelving_echo38`) build/read back on both targets, pass
SDK/access/default/schema/token proofs, and fit at {pctp}% Studio Capacity
({up:,} and {us:,} Blocks, +{deltap:,}). Phase 5's `health_rows` reason-21
precondition is proven offline on the shelving profile while the normal press
retains its metrics exclusion. Part, genealogy/inherited runners and the
canonical press launcher remain in C5b3 before C5c/V6.12, C6/C7 and native S6-Q.'''
assert target in plan_text
plan.write_text(plan_text.replace(target,replacement,1),encoding='utf-8',newline='\n')

with (W/'finish_docs_01.json').open('x',encoding='utf-8') as out:
 json.dump(dict(passed=True,counts=counts,pressCapacity=cap_press,shelvingCapacity=cap_shelving,pressSourceSha256=prep['profiles']['press']['sourceSha256'],shelvingSourceSha256=prep['profiles']['shelving']['sourceSha256']),out,indent=2)
print(json.dumps(dict(passed=True,counts=counts,pressBlocks=up,shelvingBlocks=us)))
