from pathlib import Path
import gzip,json,sys,hashlib
R=Path('C:/Users/SoftIndVM/Fraktal')
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_command_binding import write_plan
fixture=R/'FraktalCore/HMI/test/fixtures/cip_publication_goldens.json.gz'
capture=json.loads(gzip.decompress(fixture.read_bytes()))['vectors'][-1]['capture']
row=capture['manifest']['commandBindings'][0]
vectors=[]
for kind in range(39):
    args=dict(Kind=kind,TargetPath=row['RootSymbol']+'.Fixture',NameValue='fixture.key',
              TextValue='é測試',User='fixture_user',Secret='FAKE_TEST_ONLY',
              IntValue=-2147483648+kind,BoolValue=bool(kind%2),DurationMs=0xffffffff-kind)
    sequence=(0xfffffff0+kind)&0xffffffff
    plan=write_plan(capture,row,args,sequence,connection_bytes=4000)
    vectors.append(dict(kind=kind,arguments=args,sequence=sequence,
                        payloadRequestHex=plan.payload_request.hex(),commitRequestHex=plan.commit_request.hex()))
out=R/'FraktalCore/HMI/test/fixtures/cip_command_goldens.json.gz'
out.write_bytes(gzip.compress(json.dumps(dict(source='Python fraktal_ab_command_binding.write_plan',
    captureSha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),root=row['RootSymbol'],vectors=vectors),
    ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
print(json.dumps(dict(vectors=len(vectors),sha256=hashlib.sha256(out.read_bytes()).hexdigest())))
