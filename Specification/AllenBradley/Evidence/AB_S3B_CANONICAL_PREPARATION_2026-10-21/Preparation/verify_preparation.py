from pathlib import Path
import gzip,hashlib,json,os,sys
from types import SimpleNamespace
ROOT=Path("C:/Users/SoftIndVM/Fraktal")
W=Path(__file__).parent
sys.path.insert(0,str(ROOT/"FraktalCore/PLC/Allen-Bradley/tools"))
os.environ["FRAKTAL_AB_DECLARATION"]="fraktal_ab_genealogy_demo"
import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_equivalence as equiv
import fraktal_ab_sdk_log_gate as sdk
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_s3a_equivalence as s3a
import fraktal_ab_genealogy_canonical_demo as s2app
import fraktal_ab_genealogy_s3a_demo as s3aapp
import fraktal_ab_manifest as manifest
import fraktal_ab_press_execute as execute
import fraktal_ab_models as models
def sha(raw):return hashlib.sha256(raw).hexdigest()
checks=[]
for name,expected in (("compatibility_s2.L5X","9398A04EE4ABECF74C006CF0BD2AB516D8EA3AE5607D37041AB8AE0CD0FE725E"),
                      ("compatibility_s3a.L5X","83443758841A5B5F8D334106079EB8B041F2FF3E3419DB99564108532E361095")):
    actual=sha((W/name).read_bytes()).upper()
    assert actual==expected,(name,actual)
    checks.append(dict(kind="unchangedStageOutput",name=name,sha256=actual))
for label,operations,clean in (("native_echo_03",("Build","Save As"),True),
                             ("native_physical_03",("Build","Save As"),True),
                             ("prepare_acd_01",("Build","Save","Save As"),True)):
    audit=sdk.audit_log((W/(label+".log")).read_text(encoding="utf-8",errors="replace"),operations,clean)
    assert audit["Clean"],audit
    checks.append(dict(kind="sdkLogAudit",name=label,audit=audit))
for stage,filename,factory in (("S2","equivalence_01",s2app.application),
                               ("S3A","idle_equivalence_02",s3aapp.application)):
    sealed=ROOT/("Specification/AllenBradley/Evidence/AB_"+stage+"_CANONICAL_RUNTIME_2026-10-21/Runtime")/(filename+".json.gz")
    evidence=json.loads(gzip.decompress(sealed.read_bytes()))
    pair=evidence["pair"]
    canonical=reader.snapshot(pair["capture"])
    assert canonical==pair["canonical"],stage+" canonical changed"
    app=factory()
    # The manifest's static localization rows come from the same declaration;
    # raw legacy values are decoded again through their owning readers.
    rows=manifest.content(app)
    responses={r["tag"]:SimpleNamespace(Status=r["status"],Value=bytes.fromhex(r["rawHex"]) if r["rawHex"] is not None else r["value"]) for r in pair["rawReads"]}
    class Held:
        def Read(self,name):return responses[name]
    comm=Held()
    unit=execute.read_unit(comm)
    contexts={m.name:execute.read_module(comm,m.name) for m in app.modules}
    codes=models.read(comm,app)
    held=pair["legacyInputs"]
    assert json.loads(json.dumps(dict(unit=unit,contexts=contexts,codes=codes)))==held
    projection=shared.oracle(app,rows,unit,contexts,codes,
        expected=s3a.subset_paths(app,codes,canonical=False) if stage=="S3A" else None,
        extra=s3a.extra_values if stage=="S3A" else None)
    assert projection["values"]==pair["projection"]["values"],stage+" projection changed"
    assert projection["types"]==pair["projection"]["types"],stage+" types changed"
    result=equiv.compare_documents(projection,canonical)
    assert result["equal"] and result["typeAcceptance"],result
    checks.append(dict(kind="sealedPairReplay",stage=stage,paths=result["comparedPaths"],sourceSha256=sha(sealed.read_bytes())))
forecast=json.loads((W/"capacity_forecast_01.json").read_text())
measured=json.loads((W/"capacity_candidate_auto_01.json").read_text())
error=forecast["estimatedUsedBlocks"]-measured["UsedStandardBlocks"]
checks.append(dict(kind="capacityHoldout",forecastBlocks=forecast["estimatedUsedBlocks"],
    measuredBlocks=measured["UsedStandardBlocks"],errorBlocks=error,
    errorPercent=100*error/measured["UsedStandardBlocks"],
    planningBudgetBlocks=forecast["planningBudgetBlocks"],
    withinPlanningBudget=measured["UsedStandardBlocks"]<=forecast["planningBudgetBlocks"],
    measurementNotUsedForCalibration=True))
with (W/"preparation_verification_01.json").open("x",encoding="utf-8") as out:
    json.dump(dict(passed=True,controllerChanges=0,checks=checks),out,indent=2)
print(json.dumps(dict(passed=True,checks=len(checks))))
