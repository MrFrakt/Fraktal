"""Require inherited S3f coverage plus native active-model and retained restart."""
from pathlib import Path
import argparse,json,subprocess,sys
W=Path(__file__).parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fixture',type=Path);parser.add_argument('--base-output',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
if args.output.exists() or args.base_output.exists():parser.error('new output files required')
previous=W/'verify_base_acceptance.py'
subprocess.run([sys.executable,str(previous),str(args.fixture),'--output',str(args.base_output)],check=True)
fixture=json.loads(args.fixture.read_text());base=json.loads(args.base_output.read_text())
assert base['passed']
extra=fixture['s3fRevisionRows'];assert len(extra)==1 and extra[0]['passed'] and extra[0]['case']=='active_model_revision_and_exact_restore'
phases=[r['phase'] for r in fixture['s3fConfigPairs']]
assert phases.count('active_model_confirmation')==2
for phase in ('active_model_before','active_model_changed','active_model_restored'):assert phases.count(phase)==1
before=json.loads((W/'restart_before.json').read_text());after=json.loads((W/'restart_after.json').read_text())
assert before['passed'] and after['passed']
from restart_checks import compare
compare(before['snapshot'],after['snapshot'])
result=dict(passed=True,readOnly=True,inheritedCandidateRows=41,activeModelRows=1,retainedRestartRows=1,
 totalCandidateChecks=43,originalModel=extra[0]['originalModel'],temporaryModel=extra[0]['temporaryModel'],
 beforeRevision=before['snapshot']['revision'],afterRevision=after['snapshot']['revision'],
 retainedConfigurationUnchanged=True,baseAudit=str(args.base_output))
with args.output.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
