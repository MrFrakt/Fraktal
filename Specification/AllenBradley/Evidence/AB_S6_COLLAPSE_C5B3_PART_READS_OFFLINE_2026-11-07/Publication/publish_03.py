from pathlib import Path
import base64,datetime,hashlib,json,re,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B3_PART_READS_OFFLINE_2026-11-07';P=R/'Specification/AllenBradley/Evidence'/NAME

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
def save(p,value):
 with Path(p).open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,indent=2)
def verify():
 freeze=read(W/'tools_freeze_03.json')
 for row in freeze['files']:assert sha(R/row['path'])==row['sha256'],row['path']
 for row in read(W/'unrelated_before.json'):assert sha(R/row['path'])==row['sha256'],row['path']
 for row in read(P/'artifact_manifest.json')['files']:assert sha(P/row['path'])==row['sha256'],row['path']
 references=read(W/'reference_bindings_01.json')
 assert sha(R/references['evidenceManifest'])==references['evidenceManifestSha256']
 for row in references['files']:assert sha(R/row['path'])==row['sha256'],row['path']
 runtime=read(W/'runtime_bindings_01.json')
 for name,digest in runtime['sources'].items():assert sha(R/name)==digest,name
 for name in ('gateway','hostAdapter'):assert sha(runtime[name]['path'])==runtime[name]['sha256']
 return freeze
assert git('branch','--show-current')=='main'
freeze=verify();assert git('rev-parse','HEAD')==freeze['head']
assert not git('diff','--cached','--name-only'),'existing staged work'
assert read(W/'seal_03_exit.json')['exitCode']==0 and read(P/'Gates/summary.json')['passed']
assert git('config','core.hooksPath')=='.githooks'
prefix='FraktalCore/PLC/Allen-Bradley/tools/'
sources=[prefix+name for name in ('fixtures/schema_identity/fraktal_ab_genealogy_s6_collapse_demo.declared.json','fraktal_ab_canonical_live.py','fraktal_ab_fixture_reads.py','fraktal_ab_genealogy_s6_collapse_demo.py','fraktal_ab_part_execute.py','test_fraktal_ab_part_canonical.py','test_fraktal_ab_fixture_observation.py','test_fraktal_ab_s3i_lifetime.py')]
actual=git('diff','--name-only','--',prefix).splitlines()+git('ls-files','--others','--exclude-standard','--',prefix).splitlines();assert set(actual)==set(sources),actual
docs=['Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md','Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','Specification/AllenBradley/Evidence/'+NAME+'.md']
basepaths=sorted(set(sources+docs+[p.relative_to(R).as_posix() for p in P.rglob('*') if p.is_file()]))
subprocess.run(['git','fetch','origin','main'],cwd=R,check=True)
assert git('rev-parse','origin/main')==freeze['head'],'origin/main advanced'
basefile=W/'commit_base_paths_01.nul'
with basefile.open('xb') as out:out.write(b'\0'.join(p.encode() for p in basepaths)+b'\0')
subprocess.run(['git','add','-f','--pathspec-from-file='+str(basefile),'--pathspec-file-nul'],cwd=R,check=True)
assert set(git('diff','--cached','--name-only').splitlines())==set(basepaths)
command=['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check']
check=subprocess.run(command,cwd=R,capture_output=True)
assert check.returncode in (0,2),check.returncode
text=check.stdout.decode('utf-8','strict');warnings=[]
bound={str((P/row['path']).relative_to(R).as_posix()):row for row in read(P/'artifact_manifest.json')['files']}
for line in text.splitlines():
 hit=re.fullmatch(r'(.+):([0-9]+): (trailing whitespace\.|new blank line at EOF\.|space before tab in indent\.)',line)
 if not hit:continue
 path,lineno,kind=hit.groups();assert path in bound and path.endswith('.log'),line
 row=bound[path];assert sha(R/path)==row['sha256']
 warnings.append(dict(path=path,line=int(lineno),kind=kind,sha256=row['sha256'],reason='Immutable raw test output; preserve exact bytes and exclude only this hash-bound evidence path from whitespace lint'))
assert check.returncode==0 or warnings,'unparsed whitespace refusal'
excluded=sorted({row['path'] for row in warnings})
clean=command+['--','.']+[':(exclude)'+path for path in excluded]
subprocess.run(clean,cwd=R,check=True)
Q=P/'Publication';Q.mkdir(exist_ok=False)
with (Q/'publish_03.py').open('xb') as out:out.write(Path(__file__).read_bytes())
save(Q/'whitespace_01.json',dict(schema='fraktal.evidence.immutable-log-whitespace',schemaVersion=1,recordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),baseArtifactManifestSha256=sha(P/'artifact_manifest.json'),command=command,exitCode=check.returncode,stdoutBase64=base64.b64encode(check.stdout).decode(),stderrBase64=base64.b64encode(check.stderr).decode(),exceptions=warnings,allOtherStagedPathsClean=True,cleanCommand=clean,hookBypassed=False))
save(Q/'scope_01.json',dict(parent=freeze['head'],branch='main',authorization='User: commit an push on main when finished; persists for this continued work',sources=sources,documents=docs,basePaths=basepaths,sourceFreezeSha256=sha(W/'tools_freeze_03.json'),controllerAccess=False,credentialsArchived=False))
message='S6 C5b3: migrate Part and host-event acquisition to canonical rows\n\nKeep the Part recovery matrix predicates while reading PLC-published Part\nidentity/results and occupied HostEvents ring rows. Pin each primitive write\nwith a fresh native Template-based manifest identity read. Account for the\ngenealogy matrix with 12 copy-only O10 facts (13 total).\n\nValidation: 2,707 AB tests, 85 root tests, 74 focused checks, accepted Part\nand host-batch replays, unchanged 25 checks/11 waits, both v38 build/read-back\nand SDK/access/default audits. Capacity 60%, +1,272 Blocks. Public data and\nmanifest hashes unchanged; press profiles byte-identical. No Echo operations.\nInherited bootstrap/configuration/disconnect lifecycle remains a later slice.\n'
messagefile=W/'commit_message_01.txt'
with messagefile.open('x',encoding='utf-8',newline='\n') as out:out.write(message)
with (Q/'commit_message_01.txt').open('xb') as out:out.write(messagefile.read_bytes())
manifest=[dict(path=p.relative_to(Q).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(Q.rglob('*')) if p.is_file()]
save(Q/'artifact_manifest.json',dict(schema='fraktal.evidence.artifacts',schemaVersion=1,baseArtifactManifestSha256=sha(P/'artifact_manifest.json'),files=manifest))
paths=sorted(set(sources+docs+[p.relative_to(R).as_posix() for p in P.rglob('*') if p.is_file()]))
save(W/'commit_paths_01.json',paths)
pathfile=W/'commit_paths_01.nul'
with pathfile.open('xb') as out:out.write(b'\0'.join(p.encode() for p in paths)+b'\0')
subprocess.run(['git','add','-f','--pathspec-from-file='+str(pathfile),'--pathspec-file-nul'],cwd=R,check=True)
assert set(git('diff','--cached','--name-only').splitlines())==set(paths)
subprocess.run(clean,cwd=R,check=True)
verify()
subprocess.run(['git','commit','-F',str(messagefile)],cwd=R,check=True)
commit=git('rev-parse','HEAD');assert git('rev-parse','HEAD^')==freeze['head']
subprocess.run(['git','push','origin','main'],cwd=R,check=True)
remote=git('ls-remote','--heads','origin','refs/heads/main').split()[0];assert remote==commit
verify()
result=dict(committed=True,pushed=True,branch='main',commit=commit,remote=remote,files=len(paths),immutableLogWhitespaceExceptions=len(warnings),unrelatedEditsPreserved=True,hookBypassed=False)
save(W/'publish_result_01.json',result)
print(json.dumps(result,indent=1))
