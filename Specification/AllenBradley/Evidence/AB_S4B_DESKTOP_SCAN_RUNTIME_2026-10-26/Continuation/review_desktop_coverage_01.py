from pathlib import Path
import json

W=Path(__file__).parent
D=W.parent/'desktop_scan_continue_01'
value=json.loads((D/'desktop_live/result.json').read_bytes())
expected=json.loads((W.parent/'desktop_fixture_06/result.json').read_bytes())
failures=[]
if not value.get('live') or not value.get('readOnly'):
    failures.append('live read-only context missing')
if value.get('modules')!=expected['modules']:
    failures.append('discovered module coverage differs: expected seven modules')
if value.get('fieldbusNodes')!=expected['fieldbusNodes']:
    failures.append('fieldbus coverage differs: expected three nodes')
if value.get('shots')!=expected['shots']:
    failures.append('rendered surface coverage differs: expected 31 distinct views')
result=dict(passed=not failures,helperReportedPassed=value.get('passed'),
    helperReportedDesktopLiveAccepted=value.get('desktopLiveAccepted'),
    desktopLiveAccepted=not failures,failures=failures,
    actualModules=len(value.get('modules',[])),expectedModules=len(expected['modules']),
    actualViews=len(value.get('shots',[])),expectedViews=len(expected['shots']),
    readOnly=True,controllerAccess=False,
    imageReview='Native overview screenshot shows STALE and an empty body; success flag is rejected.')
with (D/'desktop_acceptance_review_01.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps(result))
raise SystemExit(0 if result['passed'] else 1)
