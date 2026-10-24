"""Offline re-decode of every accepted native S3c capture and legacy oracle."""
from pathlib import Path
from types import SimpleNamespace
import collections,gzip,hashlib,json,os,sys
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_equivalence as equivalence
import fraktal_ab_genealogy_s3c_demo as demo
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_s3c_equivalence as gate
import fraktal_ab_s3b_equivalence as previous
import fraktal_ab_manifest as manifest
import fraktal_ab_models as models
import fraktal_ab_press_execute as execute
R=Path(__file__).parent;app=demo.application();rows=[];attempts=[];revisions=set()
paths=sorted(R.glob('candidate_regressions_01_*.json.gz'))+[R/'idle_equivalence_01.json.gz']
for path in paths:
 raw=path.read_bytes();evidence=json.loads(gzip.decompress(raw));pair=evidence['pair']
 assert evidence['passed']
 canonical=reader.snapshot(pair['capture']);assert canonical==pair['canonical'],path.name+' native replay changed'
 responses={r['tag']:SimpleNamespace(Status=r['status'],Value=bytes.fromhex(r['rawHex']) if r['rawHex'] is not None else r['value']) for r in pair['rawReads']}
 class Held:
  def Read(self,name):return responses[name]
 comm=Held();unit=execute.read_unit(comm);contexts={m.name:execute.read_module(comm,m.name) for m in app.modules};codes=models.read(comm,app);additional=gate.additional_inputs(comm)
 inputs=dict(unit=unit,contexts=contexts,codes=codes,additional=additional)
 assert json.loads(json.dumps(inputs))==pair['legacyInputs'],path.name+' legacy re-decode changed'
 projection=shared.oracle(app,manifest.content(app),unit,contexts,codes,
  expected=gate.subset_paths(app,codes,canonical=False),extra=lambda a,u:gate.extra_values(a,u,additional),logical_types=previous.logical_types)
 assert projection['values']==pair['projection']['values'] and projection['types']==pair['projection']['types'],path.name+' oracle replay changed'
 comparison=equivalence.compare_documents(projection,canonical)
 assert comparison['equal'] and comparison['typeAcceptance'] and comparison['comparedPaths']==647
 proof=pair['stateEvidence'];attempts.append(len(proof['attempts']));revisions.add(pair['capture']['manifest']['fragmentRevision'])
 rows.append(dict(file=path.name,sha256=hashlib.sha256(raw).hexdigest(),paths=647,attempts=len(proof['attempts']),generation=proof['generation']))
generic=reader.snapshot(json.loads(gzip.decompress((R/'generic_capture_01.json.gz').read_bytes())))
assert generic==json.loads(gzip.decompress((R/'generic_snapshot_01.json.gz').read_bytes()))
assert generic['nodeCount']==647 and generic['moduleCount']==7
report=dict(passed=True,readOnly=True,controllerAccess=False,pairedCaptures=len(rows),rows=rows,genericPaths=647,genericModules=7,
 attempts=dict(minimum=min(attempts),maximum=max(attempts),distribution=sorted(collections.Counter(attempts).items())),observedFragmentRevisions=sorted(revisions))
with (R/'capture_replay_01.json').open('x') as out:json.dump(report,out,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
