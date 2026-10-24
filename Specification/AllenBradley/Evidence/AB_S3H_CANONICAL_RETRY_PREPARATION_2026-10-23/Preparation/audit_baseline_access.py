"""Read-only backup policy comparison against the sealed genealogy artifact."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys,xml.etree.ElementTree as ET
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_access_audit as access
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('project',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if args.output.exists():parser.error('new output required')
source=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21/Reference/genealogy_current.L5X.gz')
raw=gzip.decompress(source.read_bytes())
assert hashlib.sha256(raw).hexdigest()=='91bf67c9101eae863cf29c1a9df6413d7256ab056d985394587f0183aa525714'
expected={n.get('Name'):n.get('ExternalAccess') for n in ET.fromstring(raw).findall('./Controller/Tags/Tag')}
prior=json.loads(Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21/Runtime/candidate_access_01.json').read_text())['topLevel']
mailbox=set(prior['Mailbox']);plant=set(prior['Plant']);public={name for name,value in expected.items() if value=='Read Only'}
observed=access.controller_tags(args.project)
report=access.audit(observed,mailbox,public,plant)
report.update(SealedReferenceSha256=hashlib.sha256(raw).hexdigest(),ExactReferenceTagAccessEqual=observed==expected)
report['Conforms']=report['Conforms'] and report['ExactReferenceTagAccessEqual']
with args.output.open('x') as out:json.dump(report,out,indent=2)
print(json.dumps(dict(passed=report['Conforms'],tags=report['TagsAudited'],exactReferenceEqual=report['ExactReferenceTagAccessEqual'])))
raise SystemExit(0 if report['Conforms'] else 1)
