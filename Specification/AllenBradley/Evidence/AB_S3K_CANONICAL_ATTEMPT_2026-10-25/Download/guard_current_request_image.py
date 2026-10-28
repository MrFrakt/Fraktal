"""Read-only check immediately before the currently authorized request walk."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,sys
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
R=Path('C:/Users/SoftIndVM/Fraktal');D=Path(__file__).parent
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
from pylogix import PLC
import fraktal_ab_canonical_reader as reader
import fraktal_ab_projection as projection
import fraktal_ab_press_execute as execute
auth=json.loads((D/'request_authorization.json').read_bytes())
assert auth['CurrentOwnerApproved'] and auth['MailboxOrTagWritesAuthorized'] and auth['Serial']=='601FC87B'
reference=json.loads(gzip.decompress((D/'generic_capture_02.json.gz').read_bytes()))
suite=json.loads((D/'ab_suite_request_cases_01_exit.json').read_bytes());assert suite['exitCode']==0
end=datetime.datetime.fromisoformat(suite['endUtc']).timestamp()
sources=list((R/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py'))
assert not [p.name for p in sources if p.stat().st_mtime>end],'AB code changed after its final suite'
with PLC('127.0.0.1') as plc:
    plc.ProcessorSlot,plc.ConnectionSize,plc.SocketTimeout=0,4000,5
    snapshot,capture=reader.read_document(plc,expect_serial='601FC87B')
    assert capture['manifest']['contentHash']==reference['manifest']['contentHash']
    assert capture['manifest']['publicationStage']==13 and len(snapshot['commandArguments'])==9
    state=projection.read_access(plc);unit=execute.read_unit(plc)
    assert state is not None and state['CurrentLevel']==0 and not state['LoginBusy'],'active HMI/session guard'
    assert unit is not None and not any(unit[k] for k in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')),'Unit must be idle and unlatched'
    row=capture['manifest']['commandBindings'][0]
    symbol=next(s for s in capture['symbols'] if s['name']==row['PayloadSymbol'])
    template=next(t for t in capture['templates'] if t['handle']==symbol['handle'])
    assert template['byteSize']==784 and template['structureHandle']==41413
    result=dict(passed=True,readOnly=True,serial='601FC87B',canonicalSha256=auth['CanonicalSha256'],
        contentHash=capture['manifest']['contentHash'],currentLevel=state['CurrentLevel'],mode=unit['Mode'],idle=True,
        payloadBytes=784,structureHandle=41413,sourceFiles=len(sources),sourceBindings={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D/'current_request_image_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='sourceBindings'}))
