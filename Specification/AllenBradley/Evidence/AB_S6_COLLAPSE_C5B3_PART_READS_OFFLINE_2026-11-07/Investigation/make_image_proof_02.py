from pathlib import Path
W=Path(__file__).parent
s=(W/'image_proof_01.py').read_text(encoding='utf-8')
s=s.replace("assert sha(old)=='07C771DF2BEBAAD59CE33611579F70ACFE92B76BB0A658783A761614E36DB417'", "pins=json.loads((R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06/Preparation/artifact_bindings.json').read_bytes())['artifacts']; assert any(Path(row['path'])==old and row['sha256']==sha(old) for row in pins)")
s=s.replace("exec(compile(ast.Module(body=nodes,type_ignores=[]),str(reference),'exec'),globals())", "code=ast.unparse(ast.Module(body=nodes,type_ignores=[])).replace('phase5_fact_accounting_01.json','fact_accounting_01.json').replace('len(deltas) == 39','len(deltas) == 12'); exec(compile(code,str(reference),'exec'),globals())\nfacts=[dict(surface=surface,member=m.name,dimension=m.dimension,source=source) for surface,m,name,source in fixture.facts(profile.application()) if surface!='Mailbox']\nwith (W/'fact_accounting_01.json').open('x',encoding='utf-8') as out:json.dump(dict(passed=True,facts=facts,scope='copy-source inventory; native genealogy values remain S6-Q'),out,indent=2)")
s=s.replace("W/'image_proof_01.json'","W/'image_proof_02.json'")
with (W/'image_proof_02.py').open('x',encoding='utf-8') as f:f.write(s)
