from pathlib import Path
import argparse,hashlib,json,sys
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from fraktal_ab_sdk_log_gate import audit_log
R=Path(__file__).parent;W=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009')
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('kind',choices=('backup','deploy','restart','restore'));args=p.parse_args()
text=(R/(args.label+'.log')).read_text();status=json.loads((R/(args.label+'_exit.json')).read_text());assert status['exitCode']==0,status
operations=('Save','Save As') if args.kind=='backup' else ('Change Controller Mode',) if args.kind=='restart' else ('Download','Save','Save As','Change Controller Mode')
report=audit_log(text,operations);assert report['Clean'],report
if args.kind=='restart':
 assert text.count('] Change Controller Mode succeeded')==2
 assert 'Download started' not in text and 'Download succeeded' not in text
 assert '"NoDownload":true' in text
 report['noDownload']=True
if args.kind in ('backup','deploy'):
 acd=W/('echo_before_s3f.ACD' if args.kind=='backup' else 's3f_canonical.ACD')
 pin=W/('backup.sha256' if args.kind=='backup' else 'deployed.sha256')
 actual=hashlib.sha256(acd.read_bytes()).hexdigest().upper();assert actual==pin.read_text().strip()
 report['acdSha256']=actual
with (R/(args.label+'_audit.json')).open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
