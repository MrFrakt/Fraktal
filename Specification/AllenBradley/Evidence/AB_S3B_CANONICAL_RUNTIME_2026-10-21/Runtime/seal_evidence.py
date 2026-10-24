"""Seal the approved S3b runtime without ACDs or credential files."""
from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path("C:/Users/SoftIndVM/Fraktal")
R=Path(__file__).parent
W=Path("C:/work/fraktal-ab-s3b-20261021/prepare_17bd9babe817422b977d82139bae95cb")
BASE=ROOT/"Specification/AllenBradley/Evidence"
NAME="AB_S3B_CANONICAL_RUNTIME_2026-10-21"
DEST=BASE/NAME
REPORT=BASE/(NAME+".md")
def sha(data):return hashlib.sha256(data).hexdigest()
def put(relative,data):
    path=DEST/relative
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as stream:stream.write(data)
required=("backup_01","backup_audit_01","backup_inventory_01","deploy_01","deploy_audit_01",
    "deploy_readback_01","deploy_access_01","initial_capture_01","candidate_regressions_03",
    "candidate_acceptance_02","idle_equivalence_02","candidate_timing_02",
    "pre_rollback_preflight_02","final_candidate_capture_01","restore_01","restore_audit_02",
    "restore_readback_01","baseline_regressions_01","final_checks_02","preflight_final_02",
    "inspect_final_02","ab_suite_01","root_tests_01","spec_gate_02","contracts_gate_02",
    "consistency_gate_02","whitespace_gate_01","capacity_calibration_01","runtime_summary_01")
for name in required:assert json.loads((R/(name+"_exit.json")).read_text())["exitCode"]==0,name
assert json.loads((R/"candidate_acceptance_02.json").read_text())["passed"]
assert json.loads((R/"final_checks_02.json").read_text())["passed"]
assert json.loads((R/"candidate_regressions_01.json").read_text())["error"]
assert not json.loads((R/"candidate_acceptance_01.json").read_text())["passed"]
summary=json.loads((R/"runtime_summary_01.json").read_text())
assert summary["passed"] and summary["totalRegressionRows"]==101
assert summary["acceptedPairs"]==dict(decision=4,held=10,fault=4)
bindings=json.loads((R/"runtime_source_bindings_final.json").read_text())
for path,expected in bindings["sha256"].items():assert sha((ROOT/path).read_bytes())==expected,path
source=W/"genealogy_s3b_final.L5X"
assert sha(source.read_bytes()).upper()=="72B9FAA0ECA228FEBAD8D19B5628A09DC06B87E739AAB3473C63E1E891CEF589"
original=Path("C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD")
assert sha(original.read_bytes()).upper()=="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084"
assert sha((W/"s3b_canonical.ACD").read_bytes()).upper()=="B308A9E4DE98B5E7557CDA84F55A6C57281DA161100B22D3A5F3AC7EA2079835"
assert sha((W/"echo_before_s3b.ACD").read_bytes()).upper()==(W/"backup.sha256").read_text().strip()
DEST.mkdir()
for file in sorted(R.iterdir()):
    if not file.is_file():continue
    assert ".acd" not in file.name.lower() and "credential" not in file.name.lower()
    put("Runtime/"+file.name,file.read_bytes())
for name in ("canonical.sha256","backup.sha256","authorization.json","preflight.json","deploy_attempt.json",
    "baseline_capacity.json","baseline_reference.json","capacity_review.json","RUNBOOK.md",
    "audit_access.py","final_checks.py","measure_timing.py","scripts/guard_echo.py","scripts/preflight.py",
    "session/Program.cs","session/S3bSession.csproj"):
    put("Session/"+name,(W/name).read_bytes())
for name in ("genealogy_s3b_final.L5X","canonical_downloaded.L5X","echo_before_s3b.L5X","genealogy_restored.L5X"):
    put("Session/"+name+".gz",gzip.compress((W/name).read_bytes(),mtime=0))
reference=Path("C:/work/fraktal-ab-s3a-20261021/runtime_efed1b59b4d14c0dabdc5c66c143dffc/candidate_timing_02.json")
put("Reference/prior_s3a_candidate_timing.json",reference.read_bytes())
for path in bindings["sha256"]:put("Source/"+path,(ROOT/path).read_bytes())
for name in ("AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md",
    "AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md",
    "AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md",
    "AB_CANONICAL_PUBLICATION_S3B_NOTES_2026-10-21.md",
    "AB_CAPACITY_FORECAST_METHOD_2026-10-21.md","AB_CAPACITY_OBSERVATIONS_2026-10-21.json",
    "AB_FROZEN_CONTRACTS_V2.json"):
    put("Target/"+name,(BASE.parent/name).read_bytes())
artifacts=[]
for path in sorted(DEST.rglob("*")):
    if not path.is_file():continue
    data=path.read_bytes()
    item=dict(path=path.relative_to(DEST).as_posix(),bytes=len(data),sha256=sha(data))
    if path.name.lower().endswith(".l5x.gz"):item["expandedSha256"]=sha(gzip.decompress(data))
    artifacts.append(item)
record=dict(schema="fraktal.ab.s3b-canonical-runtime-evidence",schemaVersion=1,
    date="2026-10-21",timeZone="America/Mexico_City",
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),publicationStage="S3b",runtimeAccepted=True,
    acceptedPaths=304,acceptedRegressionRows=62,extraCandidateRegressionRows=39,totalRegressionRows=101,
    acceptedDecisionPairs=4,acceptedHeldPairs=10,acceptedFaultPairs=4,
    recordedDownloads=2,recordedModeChanges=4,controllerFaultClears=0,clockSets=0,
    nativeAcdFilesArchived=False,credentialFilesArchived=False,originalGenealogyUnchanged=True,
    artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a["bytes"] for a in artifacts),
    priorSeals=json.loads((R/"prior_seals_verification_01.json").read_text())["rows"])
put("manifest.json",json.dumps(record,indent=2).encode())
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),bytes=record["totalBytes"],reportSha256=record["reportSha256"])))
