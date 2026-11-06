from pathlib import Path
import datetime,gzip,hashlib,json,re,shutil,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');P=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C4B_OFFLINE_2026-11-06';G=P/'Gates'
load=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
assert load(G/'gate_summary_01.json')['passed']
assert load(G/'full_ab_source_bindings_result_01.json')['sourcesUnchangedDuringSuite']
counts={}
for label in ('full_ab_01','focused_python_01','root_01'):
 matches=re.findall(r'Ran (\d+) tests? in', (G/(label+'.log')).read_bytes().decode('ascii','replace'))
 counts[label]=int(matches[-1])
assert counts==dict(full_ab_01=2574,focused_python_01=74,root_01=85),counts
bindings=load(G/'source_bindings_01.json');assert not bindings['defects']
for row in bindings['files']:assert sha(R/row['file'])==row['sha256'],row['file']
report=P.with_suffix('.md');s=report.read_text(encoding='utf-8');assert 'RESULTS_PENDING' in s
s=s.replace('RESULTS_PENDING', """- **2,574 AB tests pass** by full discovery, with 74 focused tests under
  ResourceWarnings-as-errors. Source hashes are unchanged throughout the suite.
- **44 Dart gateway tests pass**, analyzer clean; **85 root tests** and AB
  spec/contracts plus strict consistency pass.
- Fresh v38 build/read-back: genealogy on EchoController and PhysicalController,
  press on EchoController; SDK and access audits pass.
- Source 13 regenerates C4a source 12 **byte for byte**: genealogy
  `E25317EC6B713FB08285109F198004C5552BE49C0CE09A5AD48E72480AB5368F`, press
  `216E09BB96BB195596F60D639287C67469FC420C334D06E6290E55461084CBA4`.
  Legacy regeneration is also byte-identical to source 07.
- Exact prepared ACD `EB43312E237B2BF5FCB155F90F6C93DAEBA2B5E8A3726D566DE072830A97B215`;
  Capacity **61%, 1,921,584 used / 1,224,144 available / 3,145,728 Blocks**.
  This is offline Studio Capacity, not a runtime scan measurement.""")
report.write_text(s,encoding='utf-8',newline='\n')
plan=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
s=plan.read_text(encoding='utf-8');old="""frame. C4b migrates the press harnesses onto it, and C4c narrows the AOI"""
new="""frame. **C4b is done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C4B_OFFLINE_2026-11-06.md)):
the press readers use O10 plus exact canonical aliases under the same scan
proof; 86 accepted native-state replays preserve all accounted facts and the
unchanged row predicates. All 2,574 AB tests pass, both v38 targets build/read
back, and fresh Capacity remains 61%. Other HX profiles must account their
extra facts before activation; their command/launcher migration remains with
C5/O11 and S6-Q. C4c narrows the AOI"""
assert s.count(old)==1;s=s.replace(old,new);plan.write_text(s,encoding='utf-8',newline='\n')
review=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md'
s=review.read_text(encoding='utf-8');old="""- **C4b.** The press harnesses read the structure and the canonical rows,
  with the offline gate that each row's predicate gives the same result over
  the new sources as over the legacy contexts."""
new="""- **C4b, as built** ([evidence](Evidence/AB_S6_COLLAPSE_C4B_OFFLINE_2026-11-06.md)).
  The basic press walk and inherited canonical-press state readers use the
  structure and exact canonical aliases under one progressing scan proof.
  All 86 accepted native-state replays preserve the accounted facts, 85
  before/after records and unchanged row/wait predicates. Other HX profiles
  need their own fact accounting; their Frame/launcher migration stays open
  with C5/O11. A collapsed profile never falls back to old context reads."""
assert s.count(old)==1;s=s.replace(old,new);review.write_text(s,encoding='utf-8',newline='\n')
files=[row['file'] for row in bindings['files']]
files += [str(p.relative_to(R)).replace('\\','/') for p in (plan,review)]
for relative in files:
 source=R/relative;target=P/'Source'/relative;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as out:out.write(source.read_bytes())
pins=[str(u['pin']).encode() for u in load('C:/work/fraktal_echo38_access_fixture.json')['users']]
hashes={}
for f in sorted(P.rglob('*')):
 if not f.is_file():continue
 assert f.suffix.lower() not in {'.acd','.l5x','.bak','.exe','.dll','.pdb','.pyc'}
 assert 'credential' not in f.name.lower()
 raw=f.read_bytes();data=gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw
 assert not any(pin in data for pin in pins),'credential data refused'
 hashes[f.relative_to(P).as_posix()]=sha(f)
assert not any(pin in report.read_bytes() for pin in pins)
with (P/'payload_hashes.json').open('x',encoding='utf-8') as out:json.dump(hashes,out,indent=2,sort_keys=True)
meta=dict(schema='fraktal.ab.s6-collapse-c4b-offline',schemaVersion=1,entryCommit='0406f72c6',
 sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=report.name,reportSha256=sha(report),
 payloadManifestSha256=sha(P/'payload_hashes.json'),files=len(hashes),ABTests=2574,focusedTests=74,
 dartTests=44,rootTests=85,controllerAccess=False,nativeAcceptance=False,preparation=load(G/'Prepare/prepare_candidate_13.json'))
with (P/'manifest.json').open('x',encoding='utf-8') as out:json.dump(meta,out,indent=2)
authored=files+[str(report.relative_to(R)).replace('\\','/')]
paths=authored+[str(P.relative_to(R)).replace('\\','/')]
subprocess.run(['git','add','--',*paths],cwd=R,check=True)
subprocess.run(['git','diff','--cached','--check','--',*authored],cwd=R,check=True)
staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=R,text=True).splitlines()
assert all(f in authored or f.startswith(str(P.relative_to(R)).replace('\\','/')+'/') for f in staged),staged
body=Path('C:/work/fraktal-ab-c4-control-20261106/commit_c4b.txt')
body.write_text("""S6 WP6.6 C4b: read press acceptance facts under canonical scan proofs

Co-read the O10 V1 fixture and canonical aliases using the published scan
counter, retaining strict proof/freshness limits and fail-closed guards.
The press case predicates remain unchanged; 86 accepted-state replays and
85 before/after records preserve their results. Other HX migrations remain
accounted separately with C5/O11.

Validation: 2,574 AB tests; 74 focused, 44 Dart and 85 root tests; both v38
targets and press Echo build/readback; byte-identical PLC output; 61% Capacity.
No controller operations. Append-only evidence retains the failed replay.
""",encoding='utf-8',newline='\n')
subprocess.run(['git','commit','--file',str(body)],cwd=R,check=True)
print(subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip())
