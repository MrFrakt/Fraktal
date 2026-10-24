"""Read-only audit of completed authorized SDK operations."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path("C:/Users/SoftIndVM/Fraktal")
R=Path(__file__).parent
W=Path("C:/work/fraktal-ab-s3b-20261021/prepare_17bd9babe817422b977d82139bae95cb")
sys.path.insert(0,str(ROOT/"FraktalCore/PLC/Allen-Bradley/tools"))
from fraktal_ab_sdk_log_gate import audit_log
label=sys.argv[1]
operations=("Save","Save As") if label.startswith("backup") else ("Download","Change Controller Mode","Save","Save As")
result=audit_log((R/(label+".log")).read_text(encoding="utf-8",errors="replace"),operations)
exit_record=json.loads((R/(label+"_exit.json")).read_text())
assert exit_record["exitCode"]==0,exit_record
assert result["Clean"],result
hashes={}
for name in (("echo_before_s3b.ACD",) if label.startswith("backup") else ("s3b_canonical.ACD",)):
    hashes[name]=hashlib.sha256((W/name).read_bytes()).hexdigest().upper()
if label.startswith("backup"):
    assert hashes["echo_before_s3b.ACD"]==(W/"backup.sha256").read_text().strip()
result.update(passed=True,hashes=hashes)
with (R/(label+"_audit.json")).open("x",encoding="utf-8") as output:json.dump(result,output,indent=2)
print(json.dumps(result))
