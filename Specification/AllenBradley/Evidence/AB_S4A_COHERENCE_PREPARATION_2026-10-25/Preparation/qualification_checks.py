"""Offline S4a scope/refusal checks and accepted-profile regeneration."""
from copy import deepcopy
from pathlib import Path
import gzip,hashlib,importlib,json,subprocess,sys

R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools'
W=Path(__file__).parent;D=W.parent/'session_01'
sys.path[:0]=[str(D),str(T)]
import qualification_session as session
import fraktal_ab_genealogy_s4_demo as candidate
import fraktal_ab_read_coherence as coherence
import fraktal_ab_read_group_probe as probe
import fraktal_ab_canonical_publication as publication
import fraktal_ab_generate as gen
from fraktal_ab_sdk_log_gate import audit_log

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
template=json.loads((D/'authorization.template.json').read_bytes())
approved=dict(template,CurrentOwnerApproved=True,OwnerInstruction='synthetic offline authorization only')
approved.update({flag:True for flag in session.FLAGS})
session.authorize(approved)
cases=[]
for field,bad in [('CurrentOwnerApproved',False),('Serial','601FC87C'),('CanonicalSha256','0'*64),
                  ('SourceSha256','0'*64),('OwnerInstruction',''),
                  *((flag,False) for flag in session.FLAGS),
                  *((flag,True) for flag in ('FaultClearAuthorized','ClockSetAuthorized','PowerOperationsAuthorized','VendorStateEditsAuthorized'))]:
    value=dict(approved,**{field:bad})
    try:session.authorize(value)
    except ValueError:cases.append(field)
    else:raise AssertionError('bad grant accepted: '+field)
assert not (D/'authorization.json').exists()
result=subprocess.run([sys.executable,str(D/'qualification_session.py')],cwd=R,capture_output=True,text=True)
assert result.returncode and 'authorization.json' in result.stderr and 'FileNotFoundError' in result.stderr
assert not (D/'session_started.json').exists()
with (W/'missing_approval_cli_01.log').open('x') as stream:stream.write(result.stdout+result.stderr)
sdk=D/'session/bin/Debug/net8.0/win-x86/S4Session.exe'
result=subprocess.run([str(sdk),'backup'],cwd=R,capture_output=True,text=True)
assert result.returncode and 'authorization.json' in result.stderr and 'FileNotFoundException' in result.stderr
assert not (D/'echo_before_s4a.ACD').exists()
with (W/'missing_approval_sdk_01.log').open('x') as stream:stream.write(result.stdout+result.stderr)

E=R/'Specification/AllenBradley/Evidence/AB_S3K_CANONICAL_RUNTIME_2026-10-25'
seal=json.loads((E/'manifest.json').read_bytes())
item=next(a for a in seal['artifacts'] if a['path'].endswith('generic_capture.json.gz'))
path=E/item['path'];assert sha(path).lower()==item['sha256'].lower()
capture=json.loads(gzip.decompress(path.read_bytes()))
# Schema-only preview: the accepted physical root layouts are unchanged by V6.7.
# These injected descriptors are NOT represented as native V6.7 evidence.
capture['manifest']['schemaMinor']=7
capture['manifest']['readCoherenceBindings']=coherence.rows(candidate.application())
capture['symbols'].append(dict(name=publication.generation_tag(candidate.application()),atomic=0xc4,arrayRank=0))
groups=probe.plan_groups(capture)
assert all('Observation' not in g['symbol'] and 'Command' not in g['symbol'] for g in groups)
assert len(groups)==8

rows=[]
for name,module,pin in [
    ('s3k','fraktal_ab_genealogy_s3k_demo','B543336202821F95BC41A5A51441E86021F1BA9EFF28D42FABCD1AA83D7C782A'),
    ('press_s3_exit','fraktal_ab_press_canonical_echo38','6FD00A4825A2ADFA0BE9E662446905B53461C17CE40A50C1DE02733F530FBB02')]:
    profile=importlib.import_module(module);output=W/('compat_current_'+name+'.L5X')
    if name=='press_s3_exit':profile.generate(Path('C:/work/echo38_5580_seed.L5X'),output)
    else:gen.generate(profile.application(),Path('C:/work/echo38_5580_seed.L5X'),output)
    rows.append(dict(name=name,pin=pin,actual=sha(output)))
assert all(row['actual']==row['pin'] for row in rows)
audits={}
for name in ('native_EchoController_02','native_PhysicalController_02','prepare_acd_02'):
    audits[name]=audit_log((W/(name+'.log')).read_text(),required_operations=('Build','Save As') if name.startswith('native_') else ('Save As',))
    assert audits[name]['Clean'],audits[name]
report=dict(passed=True,authorizationRefusalCases=len(cases),refusedFields=cases,
    missingApprovalCliRefused=True,missingApprovalSdkRefused=True,controllerAccess=False,
    currentProfilesByteIdentical=rows,schemaOnlyPlanPreview=groups,
    previewIsNotNativeV67Evidence=True,sdkAudits=audits)
with (W/'qualification_checks_01.json').open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(dict(passed=True,refusalCases=len(cases),previewGroups=len(groups),
    currentProfiles=len(rows),maxGroupBytes=max(g['bytes'] for g in groups),controllerAccess=False)))
