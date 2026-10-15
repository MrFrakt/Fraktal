from pathlib import Path
import os,subprocess,json,sys
w=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Structure_Examples_20261011'
checks=[('21_tools_clean.log',['-m','unittest','discover','-s','FraktalCore/PLC/Siemens/tools','-t','FraktalCore/PLC/Siemens/tools']),
        ('22_consistency.log',['tools/check_consistency.py']),
        ('23_consistency_tests.log',['-m','unittest','tools.test_check_consistency'])]
results=[]
for name,args in checks:
    with (w/name).open('xb') as stream:r=subprocess.run([sys.executable,*args],stdout=stream,stderr=subprocess.STDOUT)
    results.append({'log':name,'exit':r.returncode})
    assert r.returncode==0,(name,r.returncode)
(w/'24_checks.json').write_bytes((json.dumps(results,indent=2)+'\n').encode('ascii'))
print(json.dumps(results))
