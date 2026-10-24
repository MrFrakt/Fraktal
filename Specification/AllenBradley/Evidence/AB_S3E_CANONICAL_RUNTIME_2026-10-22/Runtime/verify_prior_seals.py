"""Read-only hash verification of the sixteen predecessor canonical evidence seals."""
from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path("C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence")
W=Path(__file__).parent
rows=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
for path in sorted(ROOT.glob("AB_*/manifest.json")):
    if not any(n in path.parent.name for n in ("AB_S0_CANONICAL","AB_S0_SUPPLEMENTARY","AB_S1_CANONICAL","AB_S2_CANONICAL","AB_S3A_CANONICAL","AB_S3B_CANONICAL","AB_S3C_CANONICAL","AB_S3D_CANONICAL","AB_S3E_CANONICAL")):continue
    manifest=json.loads(path.read_text(encoding="utf-8"))
    artifacts=manifest["artifacts"]
    for entry in artifacts:
        file=path.parent/entry["path"]
        raw=file.read_bytes()
        assert sha(raw)==entry["sha256"].lower(),str(file)
        assert len(raw)==entry["bytes"],str(file)
        if entry.get("expandedSha256"):assert sha(gzip.decompress(raw))==entry["expandedSha256"].lower(),str(file)
    if manifest.get("report"):
        assert sha((ROOT/manifest["report"]).read_bytes())==manifest["reportSha256"].lower(),str(path)
    rows.append(dict(name=path.parent.name,artifacts=len(artifacts),manifestSha256=sha(path.read_bytes()),passed=True))
assert len(rows)==16,len(rows)
report=dict(passed=True,readOnly=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            records=len(rows),artifacts=sum(r["artifacts"] for r in rows),rows=rows)
with (W/"prior_seals_verification_01.json").open("x",encoding="utf-8") as output:json.dump(report,output,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!="rows"}))
