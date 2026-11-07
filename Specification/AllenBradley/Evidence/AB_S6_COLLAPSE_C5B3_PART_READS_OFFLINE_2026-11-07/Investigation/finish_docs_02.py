from pathlib import Path
import hashlib,json,re,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B3_PART_READS_OFFLINE_2026-11-07'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
required=('ab_suite_02','root_tests_01','focused_part_06','image_proof_02','layout_proof_01','predicate_proof_01','preparation_01','press_reuse_01','runtime_bindings_01','ab_spec_01','ab_contracts_01','stable_part_01','input_bindings_01','managed_tools_01','freeze_02')
for label in required:assert read(W/(label+'_exit.json'))['exitCode']==0,label
counts={label:int(re.findall(rb'Ran ([0-9]+) tests?',(W/(label+'.log')).read_bytes())[-1]) for label in ('ab_suite_02','root_tests_01','focused_part_06')}
assert counts==dict(ab_suite_02=2707,root_tests_01=85,focused_part_06=62),counts
freeze=read(W/'tools_freeze_02.json');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==freeze['head']
for row in freeze['files']:assert sha(R/row['path'])==row['sha256']
for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256']
prep=read(W/'preparation_01.json');cap=read(W/'prepare_01/capacity.json');proof=read(W/'image_proof_02.json');pred=read(W/'predicate_proof_01.json')
assert prep['passed'] and cap['VerifiedFit'] and cap['SourceUnchanged'] and proof['passed'] and pred['passed']
used,available,total,percent=(cap[k] for k in ('UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent'))
prior=read(Path('C:/work/fraktal-ab-c5-control-20261106/prepare_03/genealogy_capacity.json'));delta=used-prior['UsedStandardBlocks']
report=f'''# S6 C5b3 Part/genealogy acquisition - offline qualification

This slice qualifies the Part/genealogy acquisition path, not the complete
inherited runner or C5 exit. Parent `{freeze['head']}`. The owner authorizes
commit/push on main. No controller connection, download, tag write, mode
change, fault/TASK clear, clock, power or vendor-state operation ran.

## Results

- **2,707 AB tests**, **85 root tests**, **62 focused tests** and the root
  spec/contract/strict-consistency gates pass. All **25 `Run.check` predicates
  and 11 `Run.wait` predicates** are unchanged after equivalent decoded Part
  identity acquisition is normalized.
- The 40-leaf Part result replay equals both the complete canonical subtree
  and the original passed LD `single_reset_restart` result from the same sealed
  S6 host session, including UID, timestamp and value types. This is the same
  retained result, not a new same-scan comparison. The host batch equals **both**
  native bracketing legacy batches from that session. These are replays of
  accepted bytes, not new controller measurements or native coherence proof.
- The genealogy O10 structure grows **1 to 13 facts (+12)**, preserving the
  original mailbox field byte-for-byte. The additions are exactly the seven
  Unit state/count fields, two-hand arming, ram hold, and three access fields
  consumed by the restored Part matrix and its start/login helpers. The
  copy-only executed-ST test preserves hostile signed DINT scalar/array
  patterns; it does not fabricate native genealogy observations.
- Only the observation routine gains **12 copies / 111 ST tokens**:
  **149,276 to 149,387**. All **72 routines** match after those copies are
  removed, with zero AOI renames, numeric-key changes or text-pool moves.
  All other public data and all three manifest hashes are identical. The
  pre-collapse schema gate has zero uncovered or unused declarations.
- Both **v38 targets compile/read back** and pass SDK, native-access and
  default audits. Studio Capacity is **{percent}%**:
  **{used:,} used / {available:,} available / {total:,} Blocks**,
  **{delta:+,} used**. The pinned ACD is unchanged by review-copy measurement.

Prepared source SHA-256: `{prep['pins']['sourceSha256']}`.
Prepared ACD SHA-256: `{prep['pins']['acdSha256']}`.

## Read and guard ownership

Collapsed Part identity waits read only `Present` and `Uid`; result recording
reads the PLC-published Part fields. It does not decode a second native UID,
calculate tolerances, resolve measurement definitions or reconstruct dates.
The published timestamp representation is retained exactly.

HostEvents uses its existing V6.11 owner revision. It reads the planning
metadata, then only occupied ring slots plus matching metadata, retaining the
original three-attempt outer bound. Malformed events and inconsistent planning
headers refuse; no event is dropped to manufacture continuity. Strings,
resource values, timestamps and parent identities are PLC values. Only the
portable batch metadata's Wrapped flag is represented as its historical 0/1.
The existing portable metadata/cursor helper remains until final retirement;
this slice does not claim the Python delivery subject has been retired.

The primitive write guard retains exact Echo family/firmware/slot/IP/serial
checks and a fresh expected-manifest pin. The new declaration-free
`CanonicalRowReader.manifest_identity` discovers the header and reads its
native members using Symbol/Template widths and the existing packet decoder.
It returns no cached bootstrap values and performs no write. Missing,
ambiguous or changed metadata refuses. The pin is static metadata identity,
not a certificate for cyclic row coherence or a whole-program attestation.
The legacy baseline branch remains available until the baseline switch.

Both press profiles regenerate byte-identically to their sealed Phase 5
sources and retain their hash-bound two-target/54% Capacity qualification.
Shipping HMI/Dart sources and both runtime executables match C5b2's bindings;
its 44 Dart tests, analyzer, locked dependencies and host compilation are
reused by hashes. No fresh Flutter build, native scan or retention proof is
claimed. The actual genealogical recovery cases remain S6-Q after C7.

## Provenance correction and failed runs

The preceding Phase 5 report names genealogy source hash `07C771DF...36DB417`.
Its sealed C5a artifact manifest and the retained source instead agree on
`5557604A02885ECE5C67392B552F41F15FDC9B747ED139E275D987064273A95A`.
This qualification checks that artifact pin directly. The earlier report is
preserved unchanged; this record corrects its narrative hash. Press-profile
pins agree with the previous evidence and fresh regeneration.

The first Part tests assumed a numeric timestamp representation, then a
decimal string; the native capture supplies ISO text. Equality now uses the
published value without conversion. The first synthetic manifest-body test
returned four bytes for a symbolic BOOL; the corrected test uses its native
one-byte reply. The first source-proof helper trusted the erroneous narrative
hash; the corrected helper checks the immutable artifact binding. Failed
logs and both source-proof helpers remain sealed. The first full suite found
the old one-field genealogy assertion; that test now checks the declaration
and the generated UDT members. The failed test run was retained, the owned
Python suite process was stopped, and the complete suite was rerun. The
second freeze differs only in that test file, so the unchanged production
build/replay/root gate results remain hash-bound. No production acceptance
predicate, tolerance, retry or proof bound was relaxed.

## Remaining and next

The inherited `tower.execute_fixture` bootstrap/access reads, tower snapshot
and `exercise_common` configuration preservation still need their own
canonical/isolated-medium migration. In particular, `comm.Close()` now closes
owned gateway/host leases: the disconnect case needs an explicit ownership
boundary while preserving its 3.2-second quiet interval and four-second
expiry/acquisition bound. It must not silently restart a failed lease or use
stale metadata to make that case pass. The standalone canonical press
launcher and any remaining inherited consumers also remain C5b3 work.

Then C5c removes Frame/staged endpoints and publishes V6.12; C6/C7, native
S6-Q, final deletion/import census/gates and specification activation follow.
O5 already selects host FileMedium. O2 defers hardware-only S7 without a date
as a declared exclusion; software CIP Security is reconsidered after S6 exit.
Owner edits in `.vscode/settings.json`, the Siemens Manifest README and root
`analysis_options.yaml` remain excluded. No credentials are archived.

[Payload and hashes]({NAME}/artifact_manifest.json) bind source, outputs
and failures. L5X/ACD/EXE artifacts remain private and hash-bound.
'''
with (R/'Specification/AllenBradley/Evidence'/f'{NAME}.md').open('x',encoding='utf-8',newline='\n') as out:out.write(report)
notes=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md'
with notes.open('a',encoding='utf-8',newline='\n') as out:out.write(f'''

## C5b3 Part/genealogy acquisition slice - 2026-11-07

The [acquisition record](Evidence/{NAME}.md) passes offline: 2,707 AB tests,
85 root and 62 focused tests; 25 checks/11 waits preserved; 40-leaf Part/native-result and
HostEvents replays; both v38 target/read-back/access/default/SDK gates; {percent}%
Capacity ({used:,} used / {available:,} available / {total:,} Blocks,
{delta:+,}). O10 grows from one to thirteen facts for the Part recovery matrix.
Twelve exact copies add 111 ST tokens; all 72 routines otherwise match.
Other public data and the three manifest hashes remain identical. Both press
profiles regenerate byte-identically and reuse their 54% qualification.
The lightweight fresh manifest pin uses discovered native Templates; no
cached activation value substitutes for the read. Shipping Dart is unchanged.

This is the acquisition slice, not a complete runner/C5 exit. Next are the
inherited tower bootstrap/snapshot/configuration reads and document-preserving
isolated host lifecycle, including the explicit disconnect boundary, then the
canonical press launcher. Existing predicates and disconnect time bounds stay.
The previous Phase 5 narrative genealogy hash is corrected by this new record:
the artifact-bound source is `5557604A...273A95A`, not `07C771DF...36DB417`.
The old evidence stays immutable. No controller operation ran. C5c/V6.12,
C6/C7, native S6-Q and final retirement/spec activation remain open; O2/O5
remain decided as recorded in the plan.
''')
plan=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text=plan.read_text(encoding='utf-8');marker='C5 continues in two dependent increments without changing its exit gate:'
assert text.count(marker)==1
addition=f'''**C5b3 Part/genealogy acquisition slice done offline, 2026-11-07** ([evidence](Evidence/{NAME}.md)).
Part identity/result and HostEvents acquisition use canonical rows, and native
access facts use O10 (genealogy: 1 -> 13 facts). All 25 checks and 11 waits
remain; 2,707 AB, 85 root and 62 focused tests pass, as do both v38 target
build/read-back/access/default/SDK gates. Capacity is {percent}% ({used:,} Blocks,
{delta:+,}). Twelve copies add 111 ST tokens; all 72 routines otherwise match,
with no other public-data or manifest-hash changes. Press artifacts are
byte-identical to Phase 5. This is not the inherited runner's exit: tower
bootstrap/access/snapshot, common configuration preservation and the explicit
disconnect/service-ownership boundary remain, followed by the standalone
canonical press launcher. Native acceptance stays S6-Q after C7. The new
record also corrects the earlier Phase 5 narrative genealogy source hash from
the sealed artifact pin; it does not rewrite historical evidence.

'''
plan.write_text(text.replace(marker,addition+marker),encoding='utf-8',newline='\n')
with (W/'finish_docs_02.json').open('x',encoding='utf-8') as out:json.dump(dict(passed=True,counts=counts,capacity=cap,deltaBlocks=delta),out,indent=2)
print(json.dumps(dict(passed=True,counts=counts,capacityPercent=percent,deltaBlocks=delta)))
