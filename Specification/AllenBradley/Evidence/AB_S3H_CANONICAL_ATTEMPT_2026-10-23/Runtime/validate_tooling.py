"""Close the oracle correction before any download; the approved image is exact."""
from pathlib import Path
import datetime,hashlib,json,re,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent;P=R.parent/'prepare_5822102a73e348ec95ff7082959ef940'
T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s3h_demo as demo
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for label in ('focused_tool_fix_01','ab_tool_fix_01','root_tool_fix_01','spec_tool_fix_01','contracts_tool_fix_01','consistency_tool_fix_01','whitespace_tool_fix_01'):
    assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
for label,count in (('focused_tool_fix_01',13),('ab_tool_fix_01',2140),('root_tool_fix_01',74)):
    matched=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',(R/(label+'.log')).read_text());assert matched and int(matched[1])==count
initial=json.loads((R/'initial_source_verification.json').read_text());current={n:sha(ROOT/n) for n in initial['sha256']}
changed={n:dict(prepared=pin,runtime=current[n]) for n,pin in initial['sha256'].items() if current[n]!=pin}
assert {Path(n).name for n in changed}=={'fraktal_ab_s3h_equivalence.py','test_fraktal_ab_s3h_traceability.py'}
output=R/'s3h_tooling_regenerated_01.L5X';assert not output.exists()
gen.generate(demo.application(),Path('C:/work/echo38_5580_seed.L5X'),output)
assert sha(output)==sha(P/'s3h_candidate_03.L5X')=='e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315'
assert sha(P/'s3h_canonical.ACD').upper()==initial['preparedAcdSha256']
approval=json.loads((P/'authorization.json').read_text())
assert approval['CurrentOwnerApproved'] and approval['ApprovalQuestion']=='call_ee9b48ca64a744a5a7221f84bf3615a1:0'
assert not (P/'deploy_attempt.json').exists()
report=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceBindings=len(current),sha256=current,changedFromPreparation=changed,
    generatedPlcSourceUnchanged=True,preparedSourceSha256=sha(output),preparedAcdSha256=initial['preparedAcdSha256'],
    sessionExecutableSha256=initial['sessionExecutableSha256'],abTests=2140,rootTests=74,focusedTests=13,
    reason='Path callback takes the independently bracketed legacy event Count, not its Boolean canonical selector',
    nativeBuildEvidenceReused='Both v38 build/read-back/access gates bind this byte-identical source and ACD',
    controllerChanges=0,authorizedSessionScopeUnchanged=True)
with (R/'tooling_validation_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('sha256','changedFromPreparation')}))
