"""Supersede generated package-map binding without changing any PLC/app code."""
from pathlib import Path
import json,subprocess,urllib.parse
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;D=W.parent/'session_01'
E=R/'Specification/AllenBradley/Evidence/AB_S4B_CANONICAL_PREPARATION_2026-10-26'
current=R/'FraktalCore/HMI/.dart_tool/package_config.json'
sealed=json.loads((E/'Sources/FraktalCore/HMI/.dart_tool/package_config.json').read_bytes())
live=json.loads(current.read_bytes())
def semantic(doc):
    return {row['name']:(urllib.parse.urljoin(current.as_uri(),row['rootUri']),row.get('packageUri'),row.get('languageVersion')) for row in doc['packages']}
assert semantic(sealed)==semantic(live),'package roots or language versions changed'
frozen=dict(sealed,packages=[dict(row,rootUri=urllib.parse.urljoin(current.as_uri(),row['rootUri'])) for row in sealed['packages']])
def save(p,text):
    with p.open('x',encoding='utf-8',newline='') as stream:stream.write(text)
save(D/'dart_package_config.json',json.dumps(frozen,indent=2)+'\n')
session=(D/'qualification_session.py').read_text().replace("D / 'source_bindings.json'","D / 'source_bindings_02.json'").replace("D / 'candidate_regressions.py'","D / 'candidate_regressions_v2.py'")
assert "D / 'source_bindings_02.json'" in session and "D / 'candidate_regressions_v2.py'" in session
save(D/'qualification_session_v2.py',session)
candidate=(D/'candidate_regressions.py').read_text().replace('from qualification_session import authorize','from qualification_session_v2 import authorize')
before="'--packages='+str(R/'FraktalCore/HMI/.dart_tool/package_config.json')"
assert candidate.count(before)==1
save(D/'candidate_regressions_v2.py',candidate.replace(before,"'--packages='+str(D/'dart_package_config.json')"))
check=(W/'qualification_checks.py').read_text().replace("D/'qualification_session.py'","D/'qualification_session_v2.py'")
for old,new in [('missing_approval_cli_01','missing_approval_cli_02'),('missing_approval_sdk_01','missing_approval_sdk_02'),
                ('qualification_checks_01.json','qualification_checks_02.json')]:check=check.replace(old,new)
save(W/'qualification_checks_v2.py',check)
result=dict(passed=True,onlyGeneratedMetadataChanged=True,packageSemanticsIdentical=True,packageRootsAbsolute=True,
    originalPreparationSuperseded=True,privateMap=str(D/'dart_package_config.json'),session=str(D/'qualification_session_v2.py'),controllerChanges=0)
save(W/'package_binding_fix_01.json',json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
