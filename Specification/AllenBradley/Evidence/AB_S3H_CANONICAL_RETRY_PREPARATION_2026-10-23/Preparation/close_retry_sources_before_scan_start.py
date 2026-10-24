from pathlib import Path
import ast,datetime,hashlib,json,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
W=P.parent/'transport_2eff7b66442a4322a987fb2f7812268b';R=P.parent/'runtime_6cf76ecb8785463ab372c202e79f03f2'
sys.path.insert(0,str(T));import fraktal_ab_generate as gen;import fraktal_ab_genealogy_s3h_demo as demo
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert (W/'socket_reads.py').read_text()==(T/'fraktal_ab_paired_socket_reads.py').read_text()
assert json.loads((W/'multiplex_transport_01.json').read_text())['passed']
before=json.loads((R/'source_verification_failed_01.json').read_text())['sha256']
paths={ROOT/n for n in before}|{T/'fraktal_ab_paired_socket_reads.py',T/'test_fraktal_ab_paired_socket_reads.py'}
pending=list(paths);seen=set()
while pending:
    p=pending.pop()
    if p in seen:continue
    seen.add(p)
    if p.suffix!='.py':continue
    tree=ast.parse(p.read_text(encoding='utf-8-sig'))
    names={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    names.update(a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names)
    for name in names:
        if not name:continue
        dependency=T/(name+'.py')
        if dependency.exists() and dependency not in paths:paths.add(dependency);pending.append(dependency)
current={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)};assert len(current)==159
changes={n:dict(previous=pin,current=current[n]) for n,pin in before.items() if pin!=current[n]}
assert {Path(n).name for n in changes}=={'fraktal_ab_s2_equivalence.py','test_fraktal_ab_paired_fragments.py','test_fraktal_ab_s3h_traceability.py'}
generated=P/'s3h_regenerated_retry_01.L5X';assert not generated.exists();gen.generate(demo.application(),Path('C:/work/echo38_5580_seed.L5X'),generated)
assert sha(generated)==sha(P/'s3h_candidate_03.L5X')=='e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315'
for p in ('s3h_canonical.ACD','capacity_review.ACD'):
    assert sha(P/p).upper()=='C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC'
report=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=current,
    changedFromFailedSession=changes,addedSources=sorted(set(current)-set(before)),sourceBindings=159,
    generatedSourceUnchanged=True,preparedAcdUnchanged=True,readOnlyObserverOnly=True,
    transportQualificationSource=(W/'multiplex_transport_01.json').as_posix(),
    transportModuleSha256=sha(T/'fraktal_ab_paired_socket_reads.py'))
with (P/'source_bindings_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('sha256','changedFromFailedSession')}))
