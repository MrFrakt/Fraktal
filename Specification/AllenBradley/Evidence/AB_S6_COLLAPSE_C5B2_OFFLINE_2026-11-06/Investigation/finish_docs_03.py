from pathlib import Path
import json,re
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B2_OFFLINE_2026-11-06'
assert json.loads((W/'ab_suite_02_exit.json').read_bytes())['exitCode']==0
assert json.loads((W/'dart_tests_01_exit.json').read_bytes())['exitCode']==0
assert '+44: All tests passed!' in (W/'dart_tests_01.log').read_text(encoding='utf-8')
assert re.findall(r'Ran ([0-9]+) tests?',(W/'ab_suite_02.log').read_bytes().decode('ascii','ignore'))[-1]=='2664'
notes=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md';s=notes.read_text(encoding='utf-8');a='Qualification is in progress in `C:/work/fraktal-ab-c5b2-control-20261106/`.';b='C5b2 is complete offline: 2,664 AB tests, 85 root tests, 75 focused checks and\n25 native-capture replay/writer/storage checks pass. The fresh Dart gateway\nsuite has 44 passes; locked dependencies, analyzer, host compile and CLI check\npass on Dart 3.13.4. Records are in `C:/work/fraktal-ab-c5b2-control-20261106/`.';assert s.count(a)==1;s=s.replace(a,b).replace('O10 grows 40\u219275: all 34 record\nmembers, set SchemaVersion/AuditSequence, and RestoreLost join the earlier', 'O10 grows 40 to 75: the remaining 32 record\nmembers, set SchemaVersion/AuditSequence, and RestoreLost join the earlier');assert 'all 34 record' not in s and 'O10 grows 40 to 75' in s;notes.write_bytes(s.encode())
plan=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';s=plan.read_text(encoding='utf-8');a='C5 continues in two dependent increments without changing its exit gate:';assert s.count(a)==1
paragraph='''**C5b2 done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C5B2_OFFLINE_2026-11-06.md)).
The set fixture and shared collapsed restore branch use the Dart V6.11
adapter, an owned pinned child and an isolated copy of original documents.
Operator commands use O11; canonical reads and raw O10 records independently
verify results, store receipts and restoration. All 2,664 AB / 85 root tests,
75 focused checks, 25 replay/writer/storage checks and 44 Dart tests pass.
The press enables the approved V6.11 host jobs (75 O10 facts), passes both v38
builds/read-backs/access/defaults and fits at 54% (1,703,672 used / 1,442,056
available / 3,145,728 Blocks). A frozen flag-only reference has 65 unchanged
other routines and the fixture's exact 35 fact copies. Genealogy remains
byte-identical and retains its hash-bound 60% qualification. No controller
operations or scan measurements ran. Remaining HX migrations are C5b3;
Frame/staged retirement and V6.12 remain C5c. C6/C7 and native S6-Q still follow.

'''
s=s.replace(a,paragraph+a);a="its set clients still need the host-service publication and Dart adapter lifecycle.";b="its Phase 6 set client and shared restore branch now use the host-service publication\nand Dart adapter lifecycle. Other HX consumers still need migration.";assert s.count(a)==1;s=s.replace(a,b);plan.write_bytes(s.encode())
report=R/'Specification/AllenBradley/Evidence'/(NAME+'.md');assert not report.exists();report.write_bytes(('''# S6 C5b2 - Dart set/document workflows, offline

C5b2 passes at its offline scope. C5 remains open. Parent
`ca786c6c9e549a9ff60287cba4c290afca9ac289`; the owner authorizes commit/push
on main. No controller connection, download, tag write, mode change, fault or
TASK clear, clock, power or vendor-state operation ran.

## Results

- **2,664 AB tests**, discovered from tools; **85 root tests** and all three
  root gates; **75 focused checks** and **25 replay/writer/storage checks** pass.
- **44 Dart gateway/host-adapter tests**, locked dependencies, analyzer and
  native adapter compilation pass on Dart 3.13.4 from the pinned Flutter
  3.47.5 SDK under `C:/work/fraktal-toolchains`. The executable's help check
  exits with its expected usage code 64 without connecting to a controller.
- The press builds/read-backs for **both v38 targets** and passes the SDK log,
  native access and initial/default audits. Studio reports **54% Capacity**:
  1,703,672 used / 1,442,056 available / 3,145,728 Blocks. This is 149,244 more
  used than C5b1; the pinned ACD remains unchanged.
- Schema checks have zero uncovered differences/unused declarations. A frozen
  C5b1 reference with only the approved host-services flag enabled has **65
  identical other routines**; the fixture's exact 35 fact copies are the sole
  executable delta. Existing set-case predicates match after acquisition-only
  normalization. Genealogy is byte-identical and reuses its hash-bound C5a
  two-target/read-back/access/default and **60%** Capacity evidence.

Press source: `ED3EF9501A3F52B05509720ED2CFF316B540C8F2DD6F02DB397219D2C5872054`.
Press ACD: `974F012101A86809EA63E1122219A960ED3249B2F1A6E135E72469469C72D24A`.
The files are prepared offline artifacts, not a claim of a downloaded image.

## Ownership and acceptance

The collapsed Phase 6 set client sends typed Core commands through O11 and
observes export lines, catalog rows and named rejections independently over
canonical CIP. It waits for the PLC's ConfigPersist receipt after ACK. A failed
adapter blocks set commands; explicit ordinary cleanup can still run. Only
the Dart adapter stores or applies documents; Python reopens files read-only.

The shared collapsed `Run.restore_configuration` branch delegates to Dart,
requires a prepared original-medium seed, waits for the owner restore and
verifies every expected live document against the read-only configuration
view, active/catalog identities and configuration revision. Missing/masked
values, bank inconsistencies, losses or changed epochs refuse. The native
host status follows published Symbols/Templates in one CPS-protected reply;
fragmentation refuses and no canonical freshness certificate is invented.

An owned adapter lease pins executable, serial/slot/root and a new isolated
store. It checks for another recognized Echo adapter, verifies serving roots,
latches failure and never restarts. Gateway and adapter share one cleanup
implementation and connection-close hook; every child is closed even after
a cleanup error. No other process is stopped.

The read-only seed recorder selects confirmed live documents; named sets
are explicit opt-in, unrelated data/unconfirmed leftovers are excluded.
Hash-bound bytes are copied into a new store. Originals remain untouched and
are checked afterward. The original directory is never opened by the Dart
child. No live credentials or source medium files are archived. This fixture
copy chooses no production persistence medium.

Original values are captured only after restoration. The existing independent
station-value and four-name cleanup remains; final checks add every raw
record, original source hashes and every kept live document. Failure of one
check does not skip the others or child closure. The Python actor-state
negative test becomes the real packaged read-only policy case; refusal and
unchanged sequence remain its predicate. Operator model loads still refuse;
live restoration is a different owner route.

The press enables the existing V6.11 HostServiceBindings and its eight set
operations advertise `RequiresSetStage=false`. Frame/staged endpoints remain
for the migration. O10 grows 40 to 75 with the 32 remaining record members, set
schema/audit extent and restore-loss flag. All 35 additions replay from the
old 86 accepted raw captures. The earlier six ConfigAudit fields have no old
raw capture and still require native S6-Q.

## Failed and skipped work

Final review found that a valid document file could precede its confirmed
index entry. The verifier now requires every expected key in that authority
index; the regression removes the index while leaving valid files behind.
The in-progress full suite was stopped before qualification and restarted
against the corrected frozen bytes. An exploratory focused command also
named an absent test module; its corrected 75-check invocation passes.
Those failed/superseded logs are retained.

The first access audit required HostRingRevision on every host-enabled image.
The press advertises no HostEvents; that tag is correctly absent. The corrected
audit derives the expectation from advertised services. All actual tag/member
access checks remain. The first token helper compared a list to a tuple;
the fresh corrected proof passes. Failed runs are retained.

Shipping HMI/gateway/client sources are unchanged; the full Flutter suite and
UI builds are not rerun. Fresh Dart adapter/package checks run because this
increment prepares its executable. Owner edits in `.vscode/settings.json`,
the Siemens Manifest README and root `analysis_options.yaml` stay excluded.

Native set receipts, document restore/keep, permissions, scan/retention and the
complete HX walk on the collapsed image remain **S6-Q after C7**. This is not
a claim that the whole Part/genealogy/access/data/shelving suite migrated.
Next is C5b3's remaining HX readers and launchers, then C5c Frame/staged
retirement/V6.12, C6 exposure/tables, C7 production AUTO, native S6-Q and S7
physical CIP Security acceptance.

## Records and runtime inputs

[Payload hashes](AB_S6_COLLAPSE_C5B2_OFFLINE_2026-11-06/artifact_manifest.json)
bind the exact sources, receipts, failures, raw logs and prepared artifacts.
ACD/L5X/EXE/ZIP files stay private and are hash-bound. See the
[working notes](../AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md) and
[plan](../AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

S6-Q preparation supplies `FRAKTAL_HARNESS_HOST_ADAPTER` / `_SHA256`,
`FRAKTAL_HARNESS_HOST_SEED` / `_SHA256`, the existing gateway pins and optional
`FRAKTAL_HARNESS_OUTPUT`. The seed tool records the explicitly chosen original
store outside its source directory. No implicit deployment folder is used.
''').encode())
print('Updated C5b2 notes, plan and evidence report')
