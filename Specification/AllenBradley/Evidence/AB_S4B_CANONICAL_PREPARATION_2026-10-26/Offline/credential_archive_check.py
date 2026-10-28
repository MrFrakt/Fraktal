from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
credential=json.loads(Path('C:/work/fraktal_echo38_access_fixture.json').read_bytes())
accounts=[]
def walk(value):
    if isinstance(value,dict):
        if isinstance(value.get('user'),str) and isinstance(value.get('pin'),str):accounts.append((value['user'],value['pin']))
        for item in value.values():walk(item)
    elif isinstance(value,list):
        for item in value:walk(item)
walk(credential)
assert accounts,'fixture accounts unavailable for exclusion check'
archive=R/'Specification/AllenBradley/Evidence/AB_S4B_OFFLINE_2026-10-26/retired_spike'
matched=[]
for p in archive.rglob('*.dart'):
    text=p.read_text(encoding='utf-8')
    if any(user in text and any(q+pin+q in text for q in ("'",'"')) for user,pin in accounts):matched.append(p.relative_to(R).as_posix())
report=dict(passed=not matched,credentialFileArchived=False,accountValuesRecorded=False,possibleEmbeddedCredentialPaths=matched)
with (W/'credential_archive_check_01.json').open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report));raise SystemExit(0 if report['passed'] else 1)
