"""Compare the same Dart contract verdicts before/after the first S6 migration."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time

W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
T=R/'FraktalCore/PLC/Allen-Bradley/tools';H=R/'FraktalCore/HMI'
SDK=Path('C:/work/fraktal-toolchains/flutter-3.47.5')
sys.path.insert(0,str(T))
source=subprocess.check_output(['git','show','8cd2060f1:FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s9_contract.py'],cwd=R)
old=dict(__name__='historical_s9_contract',__file__=str(T/'fraktal_ab_s9_contract.py'))
exec(compile(source,str(T/'fraktal_ab_s9_contract.py'),'exec'),old)
legacy=old['snapshot']()
import fraktal_ab_s9_contract as current
documents=dict(legacy=legacy,canonical=current.snapshot())
files=['test/repository_contract_test.dart','test/reconnecting_opcua_session_client_test.dart',
       'test/fraktal_gateway_server_test.dart','test/opcua_repository_test.dart','test/opcua_freshness_test.dart']
verdicts={};summaries={}
for label,document in documents.items():
    path=W/('s9_'+label+'_snapshot_01.json')
    with path.open('x',encoding='utf-8') as f:json.dump(document,f,allow_nan=False)
    command=[str(SDK/'bin/cache/dart-sdk/bin/dart.exe'),str(SDK/'bin/cache/flutter_tools.snapshot'),
             'test','--no-pub','--machine',*files]
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    log=W/('s9_'+label+'_machine_01.log')
    with log.open('xb') as output:
        run=subprocess.run(command,cwd=H,env=dict(os.environ,FRAKTAL_S9_SNAPSHOT=str(path),FLUTTER_ROOT=str(SDK)),
            stdout=output,stderr=subprocess.STDOUT,timeout=300)
    suites={};tests={};results={}
    for line in log.read_text(encoding='utf-8',errors='replace').splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if event.get('type')=='suite':suites[event['suite']['id']]=event['suite']['path']
        if event.get('type')=='testStart':
            test=event['test'];tests[test['id']]=(suites.get(test['suiteID']),test['name'])
        if event.get('type')=='testDone' and not event.get('hidden',False):
            key=tests[event['testID']]
            results.setdefault(key,[]).append((event['result'],event['skipped']))
    assert run.returncode==0,(label,run.returncode)
    assert results and all(r==('success',False) for rows in results.values() for r in rows)
    verdicts[label]={key:sorted(value) for key,value in results.items()}
    summaries[label]=dict(passed=True,tests=sum(map(len,results.values())),
        logSha256=hashlib.sha256(log.read_bytes()).hexdigest().upper(),startedUtc=started,
        finishedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllerAccess=False)
    with (W/('s9_'+label+'_machine_01_exit.json')).open('x',encoding='utf-8') as f:json.dump(summaries[label],f,indent=2)
    print(json.dumps(dict(label=label,**summaries[label])),flush=True)
assert verdicts['legacy']==verdicts['canonical'],'Dart contract case set/verdicts changed'
result=dict(passed=True,unchangedCaseSetAndVerdicts=True,controllerAccess=False,controllerWrites=0,
    historicalReferenceCommit='8cd2060f1591bd31bd8c0c4ba7857598fe7c5f38',
    sourceReferenceSha256=hashlib.sha256(source).hexdigest().upper(),runs=summaries,
    scope='Legacy synthetic adapter fixture versus canonical sealed S5 native capture; identical contract assertions/verdicts, not a same-state value-equivalence claim',
    cases=[dict(suite=key[0],name=key[1],results=value) for key,value in sorted(verdicts['canonical'].items())])
with (W/'s9_contract_verdict_equivalence_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
