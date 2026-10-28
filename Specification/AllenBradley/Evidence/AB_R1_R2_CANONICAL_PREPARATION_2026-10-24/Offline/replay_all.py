from pathlib import Path
from copy import deepcopy
from dataclasses import replace
import gzip,hashlib,importlib,json,os,sys,time
R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';W=Path(__file__).parent
sys.path.insert(0,str(T));os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_type_manifest as type_manifest
import fraktal_ab_canonical_publication as publisher
import fraktal_ab_canonical_manifest as wire
E=R/'Specification/AllenBradley/Evidence'
seen=set();rows=[];stages={};minors={};before=time.time()
for seal in sorted(E.glob('AB_*CANONICAL*/manifest.json')):
 doc=json.loads(seal.read_bytes())
 artifacts=doc.get('artifacts',doc.get('files',[]))
 if not isinstance(artifacts,list):continue
 for item in artifacts:
  rel=item.get('path','')
  if not (rel.endswith('.json') or rel.endswith('.json.gz')) or not rel.startswith(('Runtime/','Run/','Diagnostic/')):continue
  path=seal.parent/rel;raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
  assert sha==item['sha256'].lower(),str(path)+' seal mismatch'
  if sha in seen:continue
  seen.add(sha)
  content=json.loads(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw)
  pair=content.get('pair',{})
  c=pair.get('capture') if isinstance(pair,dict) else None
  if c is None and content.get('schema')==reader.SCHEMA:c=content
  if c is None:continue
  old=reader.snapshot(c)
  if pair and 'canonical' in pair:assert old==pair['canonical'],str(path)+' old replay changed'
  elif rel.startswith('Runtime/generic_capture'):
   document=path.with_name(path.name.replace('generic_capture','generic_document'))
   if document.exists():assert old==json.loads(gzip.decompress(document.read_bytes())),str(path)+' generic replay changed'
  stage=c['manifest'].get('publicationStage')
  count=dict(path=str(path.relative_to(E)),sha256=sha,minor=c['manifest'].get('schemaMinor',0),stage=stage,values=old['nodeCount'])
  minors[count['minor']]=minors.get(count['minor'],0)+1
  if stage is not None:
   if stage not in stages:
    suffix={2:'canonical',3:'s3a',4:'s3b',5:'s3c',6:'s3d',7:'s3e',8:'s3f',9:'s3g',10:'s3h',11:'s3i'}[stage]
    app=replace(importlib.import_module('fraktal_ab_genealogy_'+suffix+'_demo').application(),canonical_type_manifest=True)
    stages[stage]=type_manifest.tables(app,publisher.schema(app))
   annotations,exceptions=stages[stage]
   after=deepcopy(c);m=after['manifest'];m.pop('annotations');m.update(schemaMinor=4,typeAnnotations=annotations,pathExceptions=exceptions)
   m.setdefault('fragmentRevision',0);m.setdefault('bindings',[]);m.setdefault('services',[])
   # ContentHash is a configuration identity, not a value: keep the synthetic
   # token here so complete snapshot equality also checks every other field.
   after['coherenceBefore']=after['coherenceAfter']=reader.coherence_token(m)
   new=reader.snapshot(after)
   assert old==new,str(path)+' V6.4 snapshot differs'
   count['v64Equal']=True
  rows.append(count)
  if len(rows)%100==0:print(json.dumps(dict(captures=len(rows),seconds=time.time()-before)),flush=True)
report=dict(passed=True,captures=len(rows),stages=sorted(stages),minors=minors,seconds=time.time()-before,rows=rows)
with (W/'capture_replay_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
