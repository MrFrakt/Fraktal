import sys
sys.path.pop(0)
from pathlib import Path
import datetime,json
D=Path('C:/work/fraktal-ab-s5-20261029/session_19')
sys.path.insert(0,str(D))
from browser_witness import state
boundary=state()
assert boundary['serial']=='601FC87B' and boundary['mode']==1 and boundary['currentLevel']==0 and not boundary['loginBusy'] and boundary['idle'],boundary
ready=json.loads((D/'browser_ready.json').read_bytes())
delta=(boundary['typedAck']-ready['before']['typedAck'])&0xffffffff
assert 4<=delta<0x80000000,delta
record=dict(token=ready['token'],ownerRecorded=True,passed=True,
    ownerWords='Performed now; all checks passed, logged out and tabs closed',
    checks={key:True for key in ready['checklist']},
    twoBrowserTabs=True,initialConnectionWithoutErrorFlash=True,
    partSlideMovementAndReturnWithoutDisconnect=True,
    timingCardCompactAndHorizontallyScrollable=True,
    historyAndTimingStayedVisibleForAtLeast20Seconds=True,
    loggedOutAndBothTabsClosed=True,reportedIssues=[],
    serial='601FC87B',
    canonicalSha256='95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012',
    recordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    provenance='Exact owner reply to fresh session19 corrected-build checklist; native boundary independently read, and runner rechecks it before accepting C12')
with (D/'browser_owner_checklist.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
print(json.dumps(dict(ownerRecorded=True,nativeBoundary=boundary,acknowledgementDelta=delta,finalGatesAndRollbackPending=True)))
