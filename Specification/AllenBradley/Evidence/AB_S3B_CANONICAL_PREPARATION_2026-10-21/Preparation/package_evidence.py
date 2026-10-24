"""Append-only S3b offline preparation seal; never archives ACDs or credentials."""
from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path("C:/Users/SoftIndVM/Fraktal")
W=Path(__file__).parent
BASE=ROOT/"Specification/AllenBradley/Evidence"
NAME="AB_S3B_CANONICAL_PREPARATION_2026-10-21"
DEST=BASE/NAME
REPORT=BASE/(NAME+".md")
def sha(data):return hashlib.sha256(data).hexdigest()
def put(relative,data):
    path=DEST/relative
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as stream:stream.write(data)
required=("ab_suite_02","root_tests_01","spec_gate_02","contracts_gate_02",
          "consistency_gate_02","whitespace_gate_02","prepared_readback_01",
          "echo_readback_04","physical_readback_04","preparation_verification_01",
          "access_source_01","access_echo_01","access_physical_01","access_prepared_01",
          "session_build_02","final_checks_01","prior_seals_01","inspect_final_01",
          "preflight_verify_01","capacity_reference_auto_01","capacity_candidate_auto_01")
for name in required:
    assert json.loads((W/(name+"_exit.json")).read_text())["exitCode"]==0,name
assert not any((W/p).exists() for p in ("authorization.json","deploy_attempt.json","backup.sha256","echo_before_s3b.ACD"))
candidate="634A3A86B88E666CFFCA9F530AC1D279709078BCF3E2C7EC2727B4B134394EEF"
source="72B9FAA0ECA228FEBAD8D19B5628A09DC06B87E739AAB3473C63E1E891CEF589"
assert sha((W/"s3b_canonical.ACD").read_bytes()).upper()==candidate
assert sha((W/"capacity_review.ACD").read_bytes()).upper()==candidate
assert sha((W/"genealogy_s3b_final.L5X").read_bytes()).upper()==source
original=Path("C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD")
assert sha(original.read_bytes()).upper()=="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084"
assert json.loads((W/"final_checks_01.json").read_text())["passed"]
capacity=json.loads((W/"capacity_review.json").read_text())
assert capacity["VerifiedFit"] and capacity["Measured"] and capacity["CanonicalSha256"]==candidate
qualification=json.loads((W/"capacity_qualification_01.json").read_text())
assert qualification["passed"]
bindings=json.loads((W/"source_bindings_01.json").read_text())
for path,expected in bindings["sha256"].items():assert sha((ROOT/path).read_bytes())==expected,path
for path in W.rglob("*.py"):
    if not any(p in ("bin","obj","__pycache__") for p in path.parts):compile(path.read_bytes(),str(path),"exec")
DEST.mkdir()
suffixes={".py",".ps1",".cs",".csproj",".json",".sha256",".md",".log",".gz",".l5x"}
for path in sorted(W.rglob("*")):
    if not path.is_file() or any(part in ("bin","obj","__pycache__") for part in path.parts):continue
    if ".acd" in path.name.lower() or "credential" in path.name.lower():continue
    if path.suffix.lower() not in suffixes:continue
    relative="Preparation/"+path.relative_to(W).as_posix()
    data=path.read_bytes()
    if path.suffix.lower()==".l5x":relative+=".gz";data=gzip.compress(data,mtime=0)
    put(relative,data)
for path in bindings["sha256"]:put("Source/"+path,(ROOT/path).read_bytes())
documents=("AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md",
    "AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md",
    "AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md",
    "AB_CANONICAL_PUBLICATION_S3B_NOTES_2026-10-21.md",
    "AB_CANONICAL_PUBLICATION_S3B_INVENTORY_2026-10-21.json",
    "AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md",
    "AB_FROZEN_CONTRACTS_V2.json","AB_CAPACITY_FORECAST_METHOD_2026-10-21.md",
    "AB_CAPACITY_OBSERVATIONS_2026-10-21.json")
for name in documents:put("Target/"+name,(BASE.parent/name).read_bytes())
put("Reference/echo38_5580_seed.L5X.gz",gzip.compress(Path("C:/work/echo38_5580_seed.L5X").read_bytes(),mtime=0))
artifacts=[]
for file in sorted(DEST.rglob("*")):
    if not file.is_file():continue
    data=file.read_bytes()
    row=dict(path=file.relative_to(DEST).as_posix(),bytes=len(data),sha256=sha(data))
    if file.name.lower().endswith(".l5x.gz"):row["expandedSha256"]=sha(gzip.decompress(data))
    artifacts.append(row)
manifest=dict(schema="fraktal.ab.s3b-canonical-preparation-evidence",schemaVersion=1,
    date="2026-10-21",timeZone="America/Mexico_City",
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),sourceCommit=bindings["sourceCommit"],
    publicationStage="S3b",runtimeAccepted=False,controllerChanges=0,currentAuthorizationPending=True,
    preparedAcdSha256=candidate,generatedSourceSha256=source,expectedPaths=304,fixtureEquipmentModules=0,
    capacityMeasured=True,capacityProvider=capacity["Provider"],
    usedStandardBlocks=capacity["UsedStandardBlocks"],availableBlocks=capacity["AvailableBlocks"],
    totalBlocks=capacity["TotalBlocks"],nativeAcdFilesArchived=False,credentialFilesArchived=False,
    artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a["bytes"] for a in artifacts),
    priorSeals=json.loads((W/"prior_seals_verification_01.json").read_text())["rows"])
put("manifest.json",json.dumps(manifest,indent=2).encode())
print(json.dumps(dict(sealed=True,artifacts=len(artifacts),bytes=manifest["totalBytes"],reportSha256=manifest["reportSha256"])))
