"""Offline audit after the authorized S3b candidate fixture; never writes tags."""
from pathlib import Path
import argparse,gzip,hashlib,json
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("fixture",type=Path)
parser.add_argument("--output",type=Path,required=True)
args=parser.parse_args()
if args.output.exists():parser.error("new output required")
try:
    fixture=json.loads(args.fixture.read_text(encoding="utf-8"))
    assert not fixture.get("error"),"candidate fixture recorded an error"
    assert len(fixture["rows"])==31 and all(r["passed"] for r in fixture["rows"]),"31 successful rows required"
    assert fixture["restored"] and fixture["policyRestored"],"fixture restoration incomplete"
    decisions=fixture["s3bDecisionPairs"]
    conditions=fixture["s3bConditionPairs"]
    assert len(decisions)==4,"four active decision pairs required"
    coverage={(r["kind"],r["languageOrdinal"]) for r in conditions if r["passed"]}
    assert {("held",n) for n in range(3)}|{("fault",n) for n in range(3)} <= coverage,"held/fault coverage incomplete"
    captures=[]
    for item in [*decisions,*conditions]:
        path=Path(item["output"])
        raw=path.read_bytes()
        evidence=json.loads(gzip.decompress(raw))
        result=evidence["comparison"]
        state=evidence["pair"]
        assert item["passed"] and evidence["passed"] and result["equal"] and result["typeAcceptance"]
        assert result["comparedPaths"]==result["typedPaths"]==304
        proof=state["stateEvidence"]
        assert state["sameStateVerified"] and proof["kind"]=="PLC entire-scan generation"
        assert proof["generation"]>0 and proof["generation"]%2==0
        values=state["canonical"]["values"]
        if item in decisions:assert values["Press/Decision/Prompt"]
        else:
            base="Press/"+item["module"]+"/Status/Diagnostic/"
            assert values[base+"ReasonCode"]!=0 and values[base+"Since"]!=0
        captures.append(dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),paths=304))
    report=dict(passed=True,readOnly=True,rows=31,decisionPairs=len(decisions),
                conditionPairs=len(conditions),coverage=sorted(coverage),captures=captures)
except (AssertionError,ValueError,KeyError,TypeError,OSError) as error:
    report=dict(passed=False,readOnly=True,error=str(error))
with args.output.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
raise SystemExit(0 if report["passed"] else 1)
