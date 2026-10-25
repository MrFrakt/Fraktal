"""Prepare copies and guarded helpers offline; no controller operations."""
from pathlib import Path
import hashlib,json,shutil
W=Path(__file__).parent
OLD=Path('C:/work/fraktal-ab-s3i-20261024/prepare_d6df75f72d02435aab2ef3fbd7ea986d')
ROOT=Path('C:/Users/SoftIndVM/Fraktal');EV=ROOT/'Specification/AllenBradley/Evidence'
BASE='AB_S3I_CANONICAL_RUNTIME_2026-10-24';S=EV/BASE/'Session'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pin='A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
assert sha(OLD/'capacity_review.ACD').upper()==pin
for name in ('s3i_canonical.ACD','retention_control.ACD','capacity_review.ACD'):
    assert not (W/name).exists();shutil.copyfile(OLD/'capacity_review.ACD',W/name)
with (W/'canonical.sha256').open('x') as f:f.write(pin)
for name in ('baseline_capacity.json','baseline_reference.json','capacity_review.json','canonical_prepared_compare.json'):
    shutil.copyfile(S/name,W/name)
for folder in ('scripts','session'):(W/folder).mkdir(exist_ok=False)
for name in ('scripts/guard_echo.py','scripts/preflight.py','ensure_manual.py','final_checks.py','measure_timing.py','audit_access.py'):
    text=(S/name).read_text(encoding='utf-8').replace(str(OLD).replace('\\','/'),str(W).replace('\\','/'))
    with (W/name).open('x',encoding='utf-8',newline='\n') as f:f.write(text)
for source,target in (('session/S3iSession.csproj','session/S3iLifetimeSession.csproj'),('session/NuGet.Config','session/NuGet.Config')):
    shutil.copyfile(S/source,W/target)
text=(S/'session/Program.cs').read_text(encoding='utf-8').replace(str(OLD).replace('\\','/'),str(W).replace('\\','/'))
text=text.replace('S3h','S3i lifetime').replace('FramePrepare','the sealed S3i preparation')
old='var modes=new[]{"backup","deploy-canonical","restore-genealogy"};'
new='var modes=new[]{"backup","deploy-canonical","restore-genealogy","cycle-retained"};'
assert text.count(old)==1;text=text.replace(old,new)
old='!approved.GetProperty("NativeLineVectorsAuthorized").GetBoolean() ||'
assert text.count(old)==1
text=text.replace(old,old+'\n        !approved.GetProperty("CalendarLifetimeVectorsAuthorized").GetBoolean() ||\n        !approved.GetProperty("RetainedCycleAuthorized").GetBoolean() ||')
marker='if (args[0]=="backup") {'
assert text.count(marker)==1
cycle='''if (args[0]=="cycle-retained") {
    var control=Path.Combine(root,"retention_control.ACD");
    var report=Path.Combine(root,"retained_cycle.json");
    var pin=File.ReadAllText(Path.Combine(root,"canonical.sha256")).Trim();
    if (File.Exists(report) || Hash(control)!=pin) throw new Exception("Retained control copy missing/changed or cycle already recorded");
    await Guard();
    await Python(Path.Combine(root,"scripts/retention_preflight.py"));
    using var project=await LogixProject.OpenLogixProjectAsync(control,new StdOutEventLogger());
    await project.SetCommunicationsPathAsync(route);
    await Guard();
    await Python(Path.Combine(root,"scripts/retention_readiness.py"));
    var before=await project.ReadControllerModeAsync();
    if (before!=LogixProject.ControllerMode.Run) throw new Exception("Retained cycle must start in Run");
    await Guard();
    await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Program);
    await Guard();
    await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Run);
    await Guard();
    var after=await project.ReadControllerModeAsync();
    if (after!=LogixProject.ControllerMode.Run || Hash(control)!=pin) throw new Exception("Retained cycle did not return to Run or changed its control copy");
    using var output=new FileStream(report,FileMode.CreateNew,FileAccess.Write);
    JsonSerializer.Serialize(output,new {Passed=true,Before=before.ToString(),After=after.ToString(),DownloadPerformed=false,SourceAcdUnchanged=true,CanonicalSha256=pin});
    Console.WriteLine(JsonSerializer.Serialize(new {RetainedCycleCompleted=true,DownloadPerformed=false,FinalMode=after.ToString()}));
    return 0;
}
'''
text=text.replace(marker,cycle+marker)
with (W/'session/Program.cs').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
shutil.copyfile(OLD/'s3i_bench_05.L5X',W/'s3i_bench_05.L5X')
shutil.copyfile(Path('C:/work/fraktal-ab-s3i-20261024/runtime_a7e7c2452c7e44568750b2776abec564/audit_baseline_access.py'),W/'audit_baseline_access.py')
with (W/'authorization.json').open('x') as f:
    json.dump(dict(CurrentOwnerApproved=False,ManualNormalizationAuthorized=False,AccessVectorsAuthorized=False,
        ConfigurationVectorsAuthorized=False,NativeLineVectorsAuthorized=False,CalendarLifetimeVectorsAuthorized=False,
        RetainedCycleAuthorized=False,FaultClearAuthorized=False,ClockSetAuthorized=False,Serial='601FC87B',CanonicalSha256=pin,
        RuntimeDirectory=None,Scope='Prepared only; current owner approval required'),f,indent=2)
with (W/'unchanged_image_01.json').open('x') as f:
    json.dump(dict(passed=True,canonicalSha256=pin,sourceSha256=sha(W/'s3i_bench_05.L5X'),
        capacityEvidence=str(S/'capacity_review.json'),capacitySha256=sha(S/'capacity_review.json'),
        measuredCapacityPercent=87,plcChanged=False,buildReadbackTransferredByExactHash=True,
        originalUnopened=True),f,indent=2)
print(json.dumps(dict(passed=True,canonicalSha256=pin,controllerOperations=0,authorization=False)))
