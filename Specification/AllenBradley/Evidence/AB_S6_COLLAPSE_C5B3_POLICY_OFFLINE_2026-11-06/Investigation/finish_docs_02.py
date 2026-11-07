from pathlib import Path
import hashlib,json,re,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B3_POLICY_OFFLINE_2026-11-06'
def read(p):return json.loads(Path(p).read_bytes())
assert read(W/'ab_suite_01_exit.json')['exitCode']==0
assert re.findall(r'Ran ([0-9]+) tests?',(W/'ab_suite_01.log').read_bytes().decode('ascii','ignore'))[-1]=='2681'
assert read(W/'root_suite_01_exit.json')['exitCode']==0
assert re.findall(r'Ran ([0-9]+) tests?',(W/'root_suite_01.log').read_bytes().decode('ascii','ignore'))[-1]=='85'
assert read(W/'prepare_press_01.json')['passed']
notes=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md';s=notes.read_text(encoding='utf-8');a='Qualification is in progress in `C:/work/fraktal-ab-c5b3-control-20261106/`.';assert s.count(a)==1
s=s.replace(a,'C5b3 policy qualification passes offline: 2,681 AB tests, 85 root tests and\n63 focused checks pass, along with 25 replay/storage checks and the separate\nannotation replay. Records are in `C:/work/fraktal-ab-c5b3-control-20261106/`.');notes.write_bytes(s.encode())
plan=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';s=plan.read_text(encoding='utf-8');a='C5 continues in two dependent increments without changing its exit gate:';assert s.count(a)==1
paragraph='''**C5b3 policy slice done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C5B3_POLICY_OFFLINE_2026-11-06.md)).
The Phase 6 access/data-class/shelving fixtures use O11, independent canonical
policy/configuration/text reads and 27 additional exact O10 fields (102 total).
The original 43 case-site predicates retain all value, no-change and timing
conditions after acquisition/lookup normalization. Native serials/extents and
all 27 additions replay from the 86 accepted captures; annotation/annunciation
replay also passes. All 2,681 AB, 85 root and 63 focused tests pass, as do both
v38 builds/read-backs/default/access/SDK audits. Studio Capacity is 54%
(1,713,204 used / 1,432,524 available / 3,145,728 Blocks), +9,532 used. Exactly
27 fixture copies add 411 ST tokens; 65 other routines are unchanged.
Genealogy remains byte-identical with its hash-bound 60% qualification; the
unchanged shipping Dart packages retain C5b2's hash-bound 44-test qualification.
No controller operation or scan measurement ran. This completes the policy
slice only: Phase 5 metrics/reports, Part/genealogy/inherited runners and the
standalone canonical press launcher still need C5b3 accounting/migration.
Frame/staged removal remains C5c, then C6/C7 and native S6-Q. The base press
excludes controller metrics, so the original/migrated shelving preflight both
refuse its required reason-21 event. A dedicated shelving acceptance profile
remains before positive native shelving acceptance; no guard is relaxed.

'''
s=s.replace(a,paragraph+a);plan.write_bytes(s.encode())
report=R/'Specification/AllenBradley/Evidence'/(NAME+'.md');assert not report.exists()
body='''# S6 C5b3 policy fixtures - offline qualification

The access, data-class and shelving slice of C5b3 passes offline. Other HX
consumers remain open; this is not C5's exit. Parent
`f68314e3b2d46d4497be5e204818ae5df5bd26f0`; the owner authorizes commit/push
on main. No controller connection, download, tag write, mode change, fault or
TASK clear, clock, power or vendor-state operation ran.

## Results

- **2,681 AB tests** by discovery from tools; **85 root tests** by full tools
  discovery; **63 focused checks**; the **25-check replay/storage run** and
  separate **native annotation replay** pass. All three root gates pass.
- All **43 case-site predicates** retain logical operators, value comparisons,
  no-change checks and time bounds after acquisition/key/capability lookup
  normalization. Typed requests replace the direct Frame protocol subject;
  the CIP acknowledgement and machine results remain independently observed.
- Both **v38 targets build/read back** and pass SDK, native access and default
  audits. Studio Capacity is **54%**: 1,713,204 used / 1,432,524 available /
  3,145,728 Blocks, **9,532 more used** than C5b2. The canonical ACD remains
  unchanged by the review-copy measurement.
- Schema identity has zero uncovered differences and unused declarations.
  The only executable delta is **27 exact fixture copies**, with **65 other
  routines unchanged**. ST tokens: 115,596 to 116,007 (**+411**).
- Genealogy's source remains byte-identical and reuses its hash-bound C5a
  two-target/read-back/access/default/**60% Capacity** record.
- Shipping HMI/Dart sources and both prepared runtime executables match the
  committed C5b2 bindings. Its **44-test Dart** suite, analyzer, locked
  dependencies and host compilation are reused by hashes. No fresh Flutter
  suite, UI build or Dart compilation is needed for unchanged shipping files.

Press source: `72FF5A69A8B2163D9EC954FE02B3DAAF5076768CFA3E1D00F8F700D9E131631F`.
Press ACD: `FB26A19C14D3F0EAE5CF2666B132C92F9A21B7CECECE7D922F1987ED3208A641`.
These are prepared artifacts, not a claim of a downloaded image.

## Reads and lifecycle

O10 appends exactly the 27 selected access/session, audit-slot, alarm and
Start-report fields, retaining native DINTs and full array extents. All 27
exist in every one of the **86 accepted press captures**. Packed audit actor
storage is not reconstructed: public audit descriptions come from the PLC.
The older six ConfigAudit fields still lack archived native bytes; their
native acceptance remains S6-Q.

Public class policy, selected configuration metadata/values, alarm identity
text and shelving flags come from canonical rows. Configuration acquisition
uses only the active values of the three consumed keys; other bank payloads
are not read. Single-slot audit checks acquire one description; lifecycle
history uses separate row proofs, never a whole-ring certificate. The saved
native projection and published text/annunciation replay equal each other.

The shared command-side-table reader validates native Symbols/Templates,
published counts, packet bounds and root revision around metadata acquisition.
Sparse IDs, duplicate/malformed rows and failed acquisitions are tested. Only
complete immutable metadata is cached for one guarded connection; no cyclic
state is supplied from it. Configuration probes use Core names, text and live
revisions. A typed probe does not create another legacy writer or reinitialize
the adapter. PIN/result correlation and consumed-versus-authenticated checks
remain, including uint32 wrap; the login budget comes from the published
status, and an invalid budget refuses before transmitting a PIN.

Client ownership encloses original snapshots. Every independent policy,
class, timeout, value and session restore still runs after a failure. The data
fixture explicitly deletes its own named set before logout instead of relying
on disposal of the old temporary Python store. Common finalization verifies
all original raw records, original medium hashes and every kept document, and
closes owned helpers even after a check fails. The identity-only primitive
stimulus guard remains an HL helper; legacy branches/imports retire at WP6.7.
The fixture seed-copy workflow chooses no production persistence medium.

## Native shelving eligibility

The base press deliberately has `require_controller_metrics=False`. The
original shelving fixture requires the metrics-unavailable event (reason 21),
which the accepted idle input does not contain. The parent and migrated
preflights produce identical verdicts: shelving contract false, restorable
session true. This is a pre-existing eligibility gap, not a transport failure.
The migration's offline proofs do not qualify positive native shelving on
this base image. Preserve its metrics exclusion and the original guard; a
dedicated acceptance profile/event precondition remains before that native
case. The source/capture-bound analysis is in `shelving_eligibility_01.json`.

## Failed and pending work

The first focused run exposed an outdated cleanup test double without the new
context/close boundary. Its corrected test retains every restoration check
and additionally verifies closure. The first predicate helper lacked one
acquisition alias; the corrected proof covers all 43 sites. The first schema
summary printer used `unused` instead of `unusedDeclarations` after an already
passing comparison; the fresh corrected run passes. All failed logs remain.

Native policy/security and scan/retention, exact original document restore/
keep, and the complete HX walk on the collapsed image remain **S6-Q after C7**.
No acceptance, freshness, proof, retry, write-vector or fault-clear gate is
weakened. Owner edits in `.vscode/settings.json`, the Siemens Manifest README
and root `analysis_options.yaml` remain excluded.

Next are remaining Phase 5 metrics/reports, Part/genealogy/inherited runners
and the standalone canonical press launcher. Frame/staged retirement/V6.12
remains C5c; C6/C7, native S6-Q, final Python retirement/spec activation and
S7 physical hardware/CIP Security acceptance still follow.

[Payload and hashes](AB_S6_COLLAPSE_C5B3_POLICY_OFFLINE_2026-11-06/artifact_manifest.json)
record exact inputs, sources, outputs and failures. ACD/L5X/EXE files stay
private and hash-bound. See the [working notes](../AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md)
and [plan](../AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).
'''
with report.open('xb') as f:f.write(body.encode())
print('Completed scoped notes, plan and evidence report')
