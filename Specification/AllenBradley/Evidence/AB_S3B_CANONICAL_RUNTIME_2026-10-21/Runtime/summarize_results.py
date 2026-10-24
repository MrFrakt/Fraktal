"""Audit saved runtime artifacts without controller access."""
from pathlib import Path
import datetime,gzip,hashlib,json,statistics
R=Path(__file__).parent
W=Path("C:/work/fraktal-ab-s3b-20261021/prepare_17bd9babe817422b977d82139bae95cb")
def load(path):
    raw=path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix==".gz" else raw)
def timing(path):
    data=load(path);samples=data["samples"]
    names=("TaskLastScanUs","TaskMaxScanUs","TaskOverlapCount")
    result=dict(source=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    for name in names:
        values=[s["values"]["FRK_Press_HealthProbe."+name] for s in samples]
        result[name]=dict(minimum=min(values),median=statistics.median(values),maximum=max(values))
    return result
candidate=load(R/"candidate_regressions_03.json")
baseline=load(R/"baseline_regressions_01.json")
for record in (candidate,baseline):
    assert len(record["rows"])==31 and all(row["passed"] for row in record["rows"])
    assert not record.get("error") and record["restored"] and record["policyRestored"]
assert load(R/"candidate_acceptance_02.json")["passed"]
assert load(R/"final_checks_01.json")["passed"]
assert load(R/"idle_equivalence_02.json.gz")["comparison"]["comparedPaths"]==304
attempts=[];kinds={}
for pair in candidate["s3bDecisionPairs"]+candidate["s3bConditionPairs"]:
    capture=load(Path(pair["output"]))
    assert capture["passed"] and capture["comparison"]["typeAcceptance"]
    assert capture["comparison"]["comparedPaths"]==304
    assert capture["fixtureObserver"]==dict(independent=True,writerConnectionBytes=500,readConnectionBytes=4000)
    attempts.append(len(capture["pair"]["stateEvidence"]["attempts"]))
    kinds[pair.get("kind","decision")]=kinds.get(pair.get("kind","decision"),0)+1
counts=[len(load(R/(label+".json"))["rows"]) for label in
        ("candidate_regressions_01","candidate_regressions_02","candidate_regressions_03","baseline_regressions_01")]
original=Path("C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD")
assert hashlib.sha256(original.read_bytes()).hexdigest().upper()=="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084"
report=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    expectedPaths=304,acceptedRegressionRows=62,totalRegressionRows=sum(counts),
    retainedExtraCandidateRows=counts[0]+counts[1],rowsByRun=counts,
    acceptedPairs=kinds,acceptedAttemptCounts=attempts,
    capacity=load(W/"capacity_review.json"),
    timings=dict(beforeGenealogy=timing(R/"timing_baseline_01.json"),
        candidate=timing(R/"candidate_timing_02.json"),restoredGenealogy=timing(R/"baseline_timing_01.json"),
        priorS3a=timing(Path("C:/work/fraktal-ab-s3a-20261021/runtime_efed1b59b4d14c0dabdc5c66c143dffc/candidate_timing_02.json"))),
    originalGenealogyUnchanged=True,recordedDownloads=2,recordedModeChanges=4,controllerFaultClears=0)
with (R/"runtime_summary_01.json").open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2)
print(json.dumps(dict(passed=True,rowsByRun=counts,totalRows=sum(counts),pairs=kinds,attempts=attempts)))
