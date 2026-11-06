"""Seal C4c after every exact-source gate, then commit only this checkpoint."""
from pathlib import Path
from collections import Counter
import datetime,gzip,hashlib,json,re,shutil,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).resolve().parents[1];G=P/'Gates'
W=Path('C:/work/fraktal-ab-s6-host-20261104/prepare');C=Path('C:/work/fraktal-ab-c4-control-20261106')
load=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
assert load(G/'gate_summary_04.json')['passed']
assert load(G/'qualification_17.json')['passed']
assert load(G/'full_ab_source_bindings_result_04.json')['sourcesUnchangedDuringSuite']
assert load(W/'prepare_candidate_17.json')['passed']
log=(G/'full_ab_04.log').read_bytes().decode('ascii','replace')
count=int(re.findall(r'Ran (\d+) tests? in',log)[-1]);assert count==2584,count
# A primary tree mirror proved that worktree compilation and full discovery
# bind precisely the sources being committed here.
bindings=load(G/'source_bindings_04.json');assert not bindings['defects']
for row in bindings['files']:assert sha(R/row['file'])==row['sha256'],row['file']
assert not (P/'manifest.json').exists()
prep=G/'Prepare';prep.mkdir()
for file in sorted(W.iterdir()):
 if file.is_file() and file.suffix in ('.py','.json','.log') and (any('_'+str(i) in file.stem for i in (14,15,16,17)) or file.name in ('run_logged.py','audit_access_06.py')):
  shutil.copyfile(file,prep/file.name)
old=P/'Investigation/Continuation';old.mkdir()
for file in sorted(C.glob('c4c_*')):
 if file.is_file() and file.suffix in ('.log','.json'):
  shutil.copyfile(file,old/file.name)
for file in (C/'c4c_superseded_encoding').glob('*.py'):
 target=P/'Investigation/SupersededEncoding'/file.name;target.parent.mkdir(exist_ok=True)
 shutil.copyfile(file,target)
for label in ('c4c_root_primary_01','c4c_final_fast_01'):
 assert load(C/(label+'_exit.json'))['exitCode']==0
with (G/'superseded_runs.json').open('x',encoding='utf-8') as out:
 json.dump(dict(gateRuns={'01':'stopped: encoding regression and old expectations','02':'stopped: isolate legacy imports',
                         '03':'stopped: final AOI signature naming'},
                preparation={'14':'superseded encoding, failed legacy identity','15':'superseded pre-signature AOI names',
                             '16':'superseded: genealogy generation overlapped final Unit-name edit','17':'qualified final frozen source'},
                controllerAccess=False),out,indent=2)
capacity=load(W/'capacity_auto_17.json');assert capacity['VerifiedFit']
roles={}
for name in ('generate_17','generate_press_17'):
 data=load(W/(name+'.log'))
 roles[name]=dict(Counter(role for members in data['ModuleStorage'].values() for role in members.values()))
with (G/'storage_counts_17.json').open('x',encoding='utf-8') as out:json.dump(roles,out,indent=2)
used,available,total=[capacity[k] for k in ('UsedStandardBlocks','AvailableBlocks','TotalBlocks')]
assert used+available==total
pins=load(W/'prepare_candidate_17.json')
report=P.with_suffix('.md');s=report.read_text(encoding='utf-8');assert 'RESULTS_PENDING' in s
s=s.replace('RESULTS_PENDING',f"""- **2,584 AB tests pass** by full discovery on 421 frozen tool sources;
  the primary tree matches every hash. All 18 focused storage/image tests pass.
- **85 root tests pass**, including a fresh primary-tree run; AB spec/contracts
  and strict consistency pass. The 44 passing Dart gateway tests/analyzer are
  rebound to the unchanged tracked C4b gateway bytes.
- Final source 17 builds and reads back on both v38 targets for genealogy and
  on Echo for press. SDK/access audits and all three initialization audits pass.
- Executable token proof passes over **71 genealogy and 63 press routines**.
  Primary-tree regeneration is byte-identical to both prepared source 17 images.
  The schema-identity gates pass; no undeclared public surface change occurs.
- Offline Studio Capacity: **{capacity['DisplayedUsagePercent']}%, {used:,} used /
  {available:,} available / {total:,} Blocks**, {1921584-used:,} below C4b.
- Source SHA-256: genealogy `{pins['sourceSha256']}`; press `{pins['pressSha256']}`.
  Prepared ACD `{pins['acdSha256']}`.
- Derived roles across each application's four module-type definitions:
  genealogy `{roles['generate_17']}`; press `{roles['generate_press_17']}`.
  Counts are per type definition, not per instance; existing `ExecState` is
  additional to these former-context roles.

No download, tag write, mode operation, native scan measurement or retention
acceptance was performed. Capacity is an offline Studio estimate.""")
s=s.replace('All earlier findings remain recorded.', 'The proof also learned both truncated and untruncated Unit-name forms. All earlier findings remain recorded.')
report.write_text(s,encoding='utf-8',newline='\n')
plan=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
s=plan.read_text(encoding='utf-8');old='C4c narrows the AOI\nparameters.'
new=f"""**C4c is done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C4C_OFFLINE_2026-11-06.md)):
a code-derived plan keeps external/fixture facts as parameters, moves private
module state to locals and removes unused fields. Defaults and instance
initialization survive compiled read-back; distinct signatures name distinct
AOI layouts. All 2,584 AB/85 root tests and both v38 preparations pass; Capacity
is {capacity['DisplayedUsagePercent']}% ({used:,}/{total:,} Blocks). The C4a?c press/offline scope is complete;
remaining HX/O11 migrations and integrated native S6-Q stay open."""
assert s.count(old)==1;s=s.replace(old,new);plan.write_text(s,encoding='utf-8',newline='\n')
review=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md'
s=review.read_text(encoding='utf-8');old='- **C4c.** Members only an AOI touches become locals, and unused ones go.'
new="""- **C4c, as built** ([evidence](Evidence/AB_S6_COLLAPSE_C4C_OFFLINE_2026-11-06.md)).
  One immutable plan derived from complete executable owners drives parameters,
  local defaults, instance initializers and V5 fields. External reads/writes
  and O10 facts remain addressable; instance-specific initial values cannot
  become type defaults. Unused fields go; unknown whole-instance consumers
  refuse generation. Different storage/leaf/body signatures get distinct module
  AOI names, and the Unit name binds its actual typed parameter signature.
  Final source 17, both v38 targets, initialization/token/schema proofs and
  all 2,584 AB tests pass. This closes the split's press/offline work; extra
  HX fact accounting/migration remains with C5/O11 before integrated S6-Q."""
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('| C4 | R6 + O10: fixture observation structure in acceptance declarations; the press harness and the 15 HX modules read it; frame removed |',
            '| C4 | R6 + O10: acceptance fixture, accounted press readers, frame removal and private AOI narrowing; remaining HX join with C5/O11 before S6-Q |')
review.write_text(s,encoding='utf-8',newline='\n')
files=[row['file'] for row in bindings['files']]+[p.relative_to(R).as_posix() for p in (plan,review)]
for name in files:
 source=R/name;target=P/'Source'/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as out:out.write(source.read_bytes())
secrets=[str(u['pin']).encode() for u in load('C:/work/fraktal_echo38_access_fixture.json')['users']]
hashes={}
for file in sorted(P.rglob('*')):
 if not file.is_file():continue
 assert file.suffix.lower() not in {'.acd','.l5x','.bak','.exe','.dll','.pdb','.pyc'}
 assert 'credential' not in file.name.lower()
 raw=file.read_bytes();data=gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw
 assert not any(value in data for value in secrets),'credential data refused'
 hashes[file.relative_to(P).as_posix()]=sha(file)
assert not any(value in report.read_bytes() for value in secrets)
with (P/'payload_hashes.json').open('x',encoding='utf-8') as out:json.dump(hashes,out,indent=2,sort_keys=True)
meta=dict(schema='fraktal.ab.s6-collapse-c4c-offline',schemaVersion=1,entryCommit='c1c55a6a5',
 sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=report.name,reportSha256=sha(report),
 payloadManifestSha256=sha(P/'payload_hashes.json'),files=len(hashes),ABTests=2584,focusedTests=18,rootTests=85,
 dartTestsBound=44,controllerAccess=False,nativeAcceptance=False,preparation=pins,capacity=capacity)
with (P/'manifest.json').open('x',encoding='utf-8') as out:json.dump(meta,out,indent=2)
# Only five C4c source files plus current documentation/evidence are staged.
authored=['FraktalCore/PLC/Allen-Bradley/tools/'+name for name in
 ('fraktal_ab_module_storage.py','test_fraktal_ab_module_storage.py','fraktal_ab_generate.py',
  'fraktal_ab_collapse.py','test_fraktal_ab_collapse.py')]
authored += [p.relative_to(R).as_posix() for p in (plan,review,report)]
subprocess.run(['git','add','--',*authored,P.relative_to(R).as_posix()],cwd=R,check=True)
subprocess.run(['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check','--',*authored],cwd=R,check=True)
staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=R,text=True).splitlines()
assert all(f in authored or f.startswith(P.relative_to(R).as_posix()+'/') for f in staged)
body=C/'commit_c4c.txt'
body.write_text(f"""S6 WP6.6 C4c: derive private module AOI storage from its owners

One immutable generated-owner plan keeps external and O10 facts as Input or
Output parameters, moves private state to locals and deletes unused fields.
Instance-specific defaults stay in instance data, V5 metadata follows the
same plan, and distinct signatures get distinct bounded AOI names.

Validation: 2,584 AB tests, 18 focused and 85 root tests; both v38 targets
plus press Echo; parameter/local/instance initialization, token and schema
proofs; exact primary regeneration; {capacity['DisplayedUsagePercent']}% offline Capacity. Gateway tests
bind to unchanged C4b source. No controller operations; native S6-Q remains
pending after C5-C7. Superseded investigations are retained append-only.
""",encoding='utf-8',newline='\n')
subprocess.run(['git','commit','--file',str(body)],cwd=R,check=True)
print(subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip())
