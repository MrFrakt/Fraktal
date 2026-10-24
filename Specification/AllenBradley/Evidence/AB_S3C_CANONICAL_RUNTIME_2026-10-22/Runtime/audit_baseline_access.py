"""Read-only baseline access audit using the sealed prior allow-list."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_access_audit as access
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if args.output.exists():parser.error('new output required')
prior=json.loads(Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21/Runtime/candidate_access_01.json').read_text())['topLevel']
report=access.audit(access.controller_tags(args.project),set(prior['Mailbox']),set(prior['Public']),set(prior['Plant']))
with args.output.open('x') as out:json.dump(report,out,indent=2)
print(json.dumps(dict(passed=report['Conforms'],tags=report['TagsAudited'])))
raise SystemExit(0 if report['Conforms'] else 1)
