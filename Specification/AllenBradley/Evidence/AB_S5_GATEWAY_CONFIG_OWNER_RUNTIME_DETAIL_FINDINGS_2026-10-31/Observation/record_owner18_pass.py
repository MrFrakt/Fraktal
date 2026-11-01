import sys
sys.path.pop(0)
from pathlib import Path
import datetime,json
D=Path(__file__).parent/'session_18'
sys.path.insert(0,str(D))
from browser_witness import state
boundary=state()
assert boundary['serial']=='601FC87B' and boundary['mode']==1 and boundary['currentLevel']==0 and not boundary['loginBusy'] and boundary['idle'], boundary
ready=json.loads((D/'browser_ready.json').read_bytes())
report=json.loads((D/'owner_detail_issue_report.json').read_bytes())
record=dict(token=ready['token'],ownerRecorded=True,passed=True,
    ownerWords='Performed now; all passed without flicker',
    logoutConfirmationWords='MANUAL, logged out; both tabs closed',
    checks={key:True for key in ready['checklist']},
    twoBrowserTabs=True,initialConnectionWithoutErrorFlash=True,
    partSlideMovementAndReturnWithoutDisconnect=True,
    reportedIssues=['Command timing PartSlide card is too tall and disappears after a few seconds','Event history clears and repopulates repeatedly over about 10 to 15 seconds'],
    issueEvidence='owner_detail_issue_report.json',stageExitImplied=False,
    serial='601FC87B',
    canonicalSha256='95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012',
    recordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    provenance='Fresh owner connection/command checklist and subsequent explicit logout confirmation; native boundaries independently required')
with (D/'browser_owner_checklist.json').open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2)
print(json.dumps(dict(ownerRecorded=True,connectionCommandChecklistPassed=True,reportedIssueCount=2,nativeBoundary=boundary,stageExitImplied=False)))
