"""Prepare a new one-shot helper; no prior controller authorization transfers."""
from pathlib import Path
import hashlib,json,shutil
W=Path(__file__).parent
E=Path('C:/work/fraktal-ab-s3f-20261022/prepare_3816927132f14d4998876bc62e22f342')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
rows=[]
for label in ('echo','physical'):
    t=(W/f'native_{label}_01.log').read_text();r=json.loads(t[t.rindex('\n{')+1:])
    assert r['BuildAccepted'] and r['InputUnchanged'] and r['InputSha256']==sha(W/'genealogy_s3f_revision_01.L5X')
    assert json.loads((W/f'{label}_readback_01.log').read_text())['Equivalent']
    rows.append(dict(r,case='canonical',sourceSha256=r['InputSha256']))
with (W/'native_summary_final.json').open('x') as f:json.dump(dict(passed=True,rows=rows),f,indent=2)
assert not (W/'session').exists();(W/'session').mkdir();(W/'scripts').mkdir()
t=(E/'session/Program.cs').read_text().replace(E.as_posix(),W.as_posix()).replace('genealogy_s3f_05.L5X','genealogy_s3f_revision_01.L5X')
anchor='"restore-genealogy"};';assert t.count(anchor)==1;t=t.replace(anchor,'"restore-genealogy","restart-canonical"};')
anchor='!approved.GetProperty("ConfigurationVectorsAuthorized").GetBoolean() ||';assert t.count(anchor)==1
t=t.replace(anchor,anchor+'\n        !approved.GetProperty("RevisionVectorsAuthorized").GetBoolean() ||\n        !approved.GetProperty("RetainedRestartAuthorized").GetBoolean() ||')
anchor='if (final!=LogixProject.ControllerMode.Run) throw new Exception("Controller did not return to Run");';assert t.count(anchor)==1
t=t.replace(anchor,anchor+'\n    if(exportName=="canonical_downloaded.L5X") File.WriteAllText(Path.Combine(root,"deployed.sha256"),Hash(acd));')
anchor='if (args[0]=="backup") {';assert t.count(anchor)==1
t=t.replace(anchor,'''if (args[0]=="restart-canonical") {
    if (!File.Exists(Path.Combine(root,"canonical_downloaded.L5X")) ||
        Hash(probe)!=File.ReadAllText(Path.Combine(root,"deployed.sha256")).Trim())
        throw new Exception("Exact completed candidate deployment required");
    if (File.Exists(Path.Combine(root,"restart_before.json")) || File.Exists(Path.Combine(root,"restart_after.json")))
        throw new Exception("One-shot retained restart evidence exists");
    using var project=await LogixProject.OpenLogixProjectAsync(probe,new StdOutEventLogger());
    await project.SetCommunicationsPathAsync(route);
    if (await project.ReadControllerModeAsync()!=LogixProject.ControllerMode.Run)
        throw new Exception("Retained restart requires Run");
    await Python(Path.Combine(root,"restart_checks.py"),"before");
    await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Program);
    await Guard();
    await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Run);
    if (await project.ReadControllerModeAsync()!=LogixProject.ControllerMode.Run)
        throw new Exception("Retained restart did not return to Run");
    await Python(Path.Combine(root,"restart_checks.py"),"after");
    Console.WriteLine(JsonSerializer.Serialize(new {RetainedRestart=true,FinalMode="Run",NoDownload=true}));
    return 0;
}
'''+anchor)
with (W/'session/Program.cs').open('x') as f:f.write(t)
for name in ('S3fSession.csproj','NuGet.Config'):shutil.copyfile(E/'session'/name,W/'session'/name)
for name in ('guard_echo.py','preflight.py'):
    with (W/'scripts'/name).open('x') as f:f.write((E/'scripts'/name).read_text().replace(E.as_posix(),W.as_posix()))
for name in ('ensure_manual.py','final_checks.py','measure_timing.py','audit_access.py','audit_baseline_access.py'):
    with (W/name).open('x') as f:f.write((E/name).read_text().replace(E.as_posix(),W.as_posix()))
shutil.copyfile(E/'capacity_review.json',W/'baseline_capacity.json')
with (W/'baseline_reference.json').open('x') as f:json.dump(dict(source=(E/'capacity_review.json').as_posix(),capacitySha256=sha(W/'baseline_capacity.json')),f,indent=2)
print(json.dumps(dict(passed=True,controllerChangesAuthorized=False,sourceSha256=sha(W/'genealogy_s3f_revision_01.L5X'))))
