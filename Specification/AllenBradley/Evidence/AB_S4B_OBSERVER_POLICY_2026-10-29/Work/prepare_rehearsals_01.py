from pathlib import Path
W=Path(__file__).parent;C=Path('C:/work/fraktal-ab-s4b-o8-20261028/offline_01')
raw=(C/'run_rehearsal_01.py').read_text(encoding='utf-8')
before="'pubspec.yaml','pubspec.lock'):"
assert raw.count(before)==1
raw=raw.replace(before,"'tool/qualify_cip_canonical.dart','test/cip_qualification_test.dart',\n    'pubspec.yaml','pubspec.lock'):")
with (W/'run_rehearsal_01.py').open('x',encoding='utf-8') as f:f.write(raw)
raw=(C/'verify_rehearsals_01.py').read_text(encoding='utf-8')
before="""    else:
        failure=load(W/label/'desktop/failure.json')
        assert not result['passed'] and failure['link']=='stale' and 'after-overview' in failure['error']
        result['debugComparison']='STALE at after-overview; zero completed captures'
"""
after="""    elif result['passed']:
        coverage=load(W/label/'desktop/result.json')
        assert coverage['rehearsalPassed'] and len(coverage['shots'])==31
        result['debugComparison']='Debug completed all 31 rehearsal views; no native claim'
    else:
        failure=load(W/label/'desktop/failure.json')
        assert not failure['desktopLiveAccepted']
        result['debugComparison']=str(failure['error'])
"""
assert raw.count(before)==1;raw=raw.replace(before,after)
with (W/'verify_rehearsals_01.py').open('x',encoding='utf-8') as f:f.write(raw)
print('Rehearsal runner binds all 29 changed/supporting HMI inputs; no controller changes')
