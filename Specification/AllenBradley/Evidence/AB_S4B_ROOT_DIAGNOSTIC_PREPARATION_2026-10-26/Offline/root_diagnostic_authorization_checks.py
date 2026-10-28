from pathlib import Path
import ast,copy,importlib.util,json,py_compile,subprocess,sys
W=Path(__file__).parent;D=W.parent/'retry_root_diagnostic_01';R=Path('C:/Users/SoftIndVM/Fraktal')
spec=importlib.util.spec_from_file_location('prepared_s4b_session',D/'qualification_session_v2.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
template=json.loads((D/'authorization.template.json').read_bytes())
assert not template['CurrentOwnerApproved'] and not (D/'authorization.json').exists()
valid=copy.deepcopy(template);valid.update(CurrentOwnerApproved=True,OwnerInstruction='offline in-memory test only')
for flag in module.FLAGS:valid[flag]=True
module.authorize(valid);cases=[]
for key in ['CurrentOwnerApproved','Serial','CanonicalSha256','SourceSha256','OwnerInstruction',*module.FLAGS,
    'FaultClearAuthorized','ClockSetAuthorized','PowerOperationsAuthorized','VendorStateEditsAuthorized']:
    value=copy.deepcopy(valid)
    value[key]=False if key in module.FLAGS or key=='CurrentOwnerApproved' else True if key.endswith('Authorized') else ''
    try:module.authorize(value)
    except ValueError:cases.append(key)
    else:raise AssertionError('unrefused '+key)
for path in D.rglob('*.py'):py_compile.compile(str(path),doraise=True)
def refused(name,command,needle):
    process=subprocess.run(command,cwd=R,capture_output=True,text=True)
    with (W/(name+'.log')).open('x',encoding='utf-8') as stream:stream.write(process.stdout+process.stderr)
    assert process.returncode!=0 and needle in process.stdout+process.stderr
refused('missing_approval_cli_root_diagnostic_01',[sys.executable,str(D/'qualification_session_v2.py')],'authorization.json')
refused('missing_approval_sdk_root_diagnostic_01',[str(D/'session/bin/Debug/net8.0/win-x86/S4bSession.exe'),'backup'],'authorization.json')
assert not (D/'echo_before_s4b.ACD').exists() and not (D/'session_started.json').exists()
# The observer tool's argument refusal is an expected negative gate, before I/O.
assert json.loads((W/'cli_refusal_01_exit.json').read_bytes())['exitCode']!=0
assert 'Endpoint and new output required' in (W/'cli_refusal_01.log').read_text()
report=dict(passed=True,controllerAccess=False,currentAuthorization=False,refusalCases=cases,
    missingApprovalCliRefused=True,missingApprovalSdkRefused=True,readOnlyToolArgumentRefused=True,helpersCompile=True)
with (W/'root_diagnostic_authorization_checks_01.json').open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(dict(passed=True,authorizationRefusalCases=len(cases),controllerAccess=False)))
