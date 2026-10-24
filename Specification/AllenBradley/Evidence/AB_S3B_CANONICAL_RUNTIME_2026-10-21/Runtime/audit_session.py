"""Read-only audit of completed authorized SDK operations."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path("C:/Users/SoftIndVM/Fraktal")
R=Path(__file__).parent
W=Path("C:/work/fraktal-ab-s3b-20261021/prepare_17bd9babe817422b977d82139bae95cb")
sys.path.insert(0,str(ROOT/"FraktalCore/PLC/Allen-Bradley/tools"))
from fraktal_ab_sdk_log_gate import audit_log
label=sys.argv[1]
audit_name=sys.argv[2] if len(sys.argv)>2 else label+"_audit"
operations=("Save","Save As") if label.startswith("backup") else ("Download","Change Controller Mode","Save","Save As")
result=audit_log((R/(label+".log")).read_text(encoding="utf-8",errors="replace"),operations)
exit_record=json.loads((R/(label+"_exit.json")).read_text())
assert exit_record["exitCode"]==0,exit_record
assert result["Clean"],result
records=[json.loads(line) for line in (R/(label+".log")).read_text(encoding="utf-8",errors="replace").splitlines() if line.startswith("{")]
completed=[item for item in records if "Backup" in item or "Downloaded" in item]
assert len(completed)==1
completed=completed[0]
artifact=Path(completed.get("Backup",completed.get("Downloaded")))
actual=hashlib.sha256(artifact.read_bytes()).hexdigest().upper()
assert actual==completed.get("Sha256",completed.get("AcdSha256"))
hashes={str(artifact):actual}
if label.startswith("backup"):
    assert actual==(W/"backup.sha256").read_text().strip()
else:assert completed["FinalMode"]=="Run"
result.update(passed=True,hashes=hashes)
with (R/(audit_name+".json")).open("x",encoding="utf-8") as output:json.dump(result,output,indent=2)
print(json.dumps(result))
