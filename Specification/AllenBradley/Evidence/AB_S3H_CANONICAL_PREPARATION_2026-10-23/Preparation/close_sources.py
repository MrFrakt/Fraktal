"""Bind exact source closure, compiler logs, prepared image and Capacity delta."""
from pathlib import Path
import ast,datetime,hashlib,json,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(T))
from fraktal_ab_sdk_log_gate import audit_log
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
audits={}
for label in ('native_echo_03','native_physical_03','prepare_acd_01'):
    operations=('Open project','Build','Save As')+(('Save',) if label=='prepare_acd_01' else ())
    audit=audit_log((P/(label+'.log')).read_text(),operations,True);assert audit['Clean'],(label,audit);audits[label]=audit
with (P/'sdk_audits_01.json').open('x') as f:json.dump(dict(passed=True,logs=audits),f,indent=2)
cap=json.loads((P/'capacity_auto_01.json').read_text());prior=json.loads((P/'baseline_capacity.json').read_text())
assert cap['VerifiedFit'] and cap['CanonicalSha256']==(P/'canonical.sha256').read_text().strip()
for key in ('Sha256','UsedStandardBlocks','AvailableBlocks','TotalBlocks'):
    cap['Baseline'+key]=prior['CanonicalSha256' if key=='Sha256' else key]
cap['DeltaUsedStandardBlocks']=cap['UsedStandardBlocks']-prior['UsedStandardBlocks']
with (P/'capacity_review.json').open('x') as f:json.dump(cap,f,indent=2)
prepared=json.loads((P/'prepared_readback_01.log').read_text());assert prepared['Equivalent']
with (P/'canonical_prepared_compare.json').open('x') as f:json.dump(prepared,f,indent=2)
before=json.loads((ROOT/'Specification/AllenBradley/Evidence/AB_S3G_CANONICAL_RUNTIME_2026-10-23/Runtime/source_verification_01.json').read_text())['sha256']
added=('fraktal_ab_canonical_traceability','fraktal_ab_genealogy_s3h_demo','fraktal_ab_s3h_reference','fraktal_ab_s3h_equivalence','fraktal_ab_s3h_fixture_execute','test_fraktal_ab_s3h_traceability')
paths={ROOT/n for n in before}|{T/(n+'.py') for n in added};pending=list(paths);seen=set()
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
current={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}
changes={name:dict(before=pin,after=current[name]) for name,pin in before.items() if pin!=current[name]}
assert {Path(n).name for n in changes}=={'fraktal_ab_canonical_publication.py','fraktal_ab_generate.py','fraktal_ab_s2_equivalence.py','test_fraktal_ab_canonical_publication.py'}
for name in ('fraktal_ab_canonical_reader.py','fraktal_ab_canonical_manifest.py','fraktal_ab_canonical_acquire.py'):
    relative=(T/name).relative_to(ROOT).as_posix();assert current[relative]==before[relative]
report=dict(capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),localPythonImportsClosed=True,
    sha256=current,changedExistingSources=changes,addedSources=sorted(set(current)-set(before)))
with (P/'source_bindings_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(dict(passed=True,sourceBindings=len(current),changedExistingSources=list(changes),addedSources=report['addedSources'],
    capacityBlocks=cap['UsedStandardBlocks'],deltaBlocks=cap['DeltaUsedStandardBlocks'],preparedAcdSha256=cap['CanonicalSha256'])))
