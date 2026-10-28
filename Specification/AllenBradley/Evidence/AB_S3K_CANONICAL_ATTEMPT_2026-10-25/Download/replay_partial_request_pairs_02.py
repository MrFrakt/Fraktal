"""Re-decode native frame bytes and independently replay S3j reference contexts."""
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
import collections,gzip,hashlib,json,os,sys
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s3k_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_equivalence as comparison
import fraktal_ab_genealogy_s3k_demo as demo
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_s3k_equivalence as gate
import fraktal_ab_manifest as manifest
import fraktal_ab_models as models
import fraktal_ab_press_execute as execute
import fraktal_ab_mailbox as mb
import fraktal_ab_sets as sets
import fraktal_ab_paired_fragments as fragments
import fraktal_ab_paired_observation as observed
import fraktal_ab_canonical_observation as frame_contract
R=Path(__file__).parent;output=R/'partial_pair_replay_02.json';app=demo.application()
fixture=json.loads((R/'request_cases_02.json').read_bytes());items=[item for key,value in fixture.items() if key.endswith('Pairs') for item in value if item['passed']]
assert len(items)==5
rows=[];attempts=[]
for item in items:
 path=Path(item['output']);raw=path.read_bytes();e=json.loads(gzip.decompress(raw));pair=e['pair']
 assert item['passed'] and e['passed']
 canonical=reader.snapshot(pair['capture']);assert canonical==pair['canonical']
 responses={r['tag']:SimpleNamespace(Status=r['status'],Value=bytes.fromhex(r['rawHex']) if r['rawHex'] is not None else r['value']) for r in pair['rawReads']}
 class Held:
  def Read(self,name):return responses[name]
 held=Held();u=execute.read_unit(held);ctx={m.name:execute.read_module(held,m.name) for m in app.modules}
 codes=models.read(held,app);additional=gate.additional_inputs(held,app)
 assert json.loads(json.dumps(dict(unit=u,contexts=ctx,codes=codes,additional=additional)))==pair['legacyInputs']
 context=dict(page=0,model=0,provider_state={})
 expected=shared.oracle(app,manifest.content(app),u,ctx,codes,
  expected=gate.subset_paths(app,codes,canonical=False,count=additional['host']['metadata']['Count'],shift_count=additional['line_shift']['Count'],page=context['page'],model=context['model']),
  extra=lambda a,unit:gate.extra_values(a,unit,additional,**context),logical_types=gate.logical_types)
 assert expected['values']==pair['projection']['values'] and expected['types']==pair['projection']['types'],path.name+' independent reference differs'
 result=comparison.compare_documents(expected,canonical)
 assert result['equal'] and result['typeAcceptance']
 frames=pair['fragmentPacketEvidence']
 plan=[f['plan'] for f in frames];replies=[(f['status'],bytes.fromhex(f['rawHex'])) for f in frames]
 tag=frame_contract.frame_tag(app);sizes={tag:plan[0]['total']}
 assert {p['tags'][0] for p in plan}=={tag}
 raw_frame=fragments.decode(plan,replies,sizes)[tag].Value
 cached={r['tag'] for r in pair['capture']['records'] if r['tag'] in pair['metadataEvidence']['sources']}
 live=[t for t in responses if t not in cached]
 layout=observed.layout(pair['capture'],tag,live,{t:len(responses[t].Value) for t in live},frame_contract.HEADER)
 for name,(a,b) in layout['slices'].items():assert raw_frame[a:b]==responses[name].Value,name
 header={n:int.from_bytes(raw_frame[o:o+4],'little',signed=True) for n,o in layout['header'].items()}
 proof=pair['stateEvidence'];stamp=proof['frame']
 assert proof['kind']=='PLC observation frame generation' and header['SourceGeneration']==stamp['sourceGeneration']
 assert header['SourceGeneration']%2==0 and header['SourceGeneration']>=stamp['notBefore']
 assert header['FragmentRevision']==stamp['fragmentRevision']==pair['metadataEvidence']['coherenceToken'][2]
 assert pair['sameStateVerified'] and proof['generation']%2==0 and pair['readConnections']==4
 attempts.append(len(proof['attempts']))
 rows.append(dict(file=path.name,sha256=hashlib.sha256(raw).hexdigest(),paths=result['typedPaths'],attempts=len(proof['attempts']),fragmentPackets=len(frames),
  frameSourceGeneration=header['SourceGeneration'],notBefore=stamp['notBefore']))
report=dict(passed=True,readOnly=True,controllerAccess=False,captures=len(rows),rows=rows,
 independentProviderContextSource='empty provider context, page/model zero, Access-only captures; no named-set walk executed',
 attempts=dict(minimum=min(attempts),maximum=max(attempts),distribution=sorted(collections.Counter(attempts).items())))
with output.open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
