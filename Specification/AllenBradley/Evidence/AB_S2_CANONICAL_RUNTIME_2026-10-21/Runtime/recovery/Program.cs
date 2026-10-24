// Recovery within the owner's approved S2 genealogy rollback, only on a zero-tag controller.
// The normal S2 preflight/deploy-attempt guards remain unchanged.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;
const string work="C:/work/fraktal-ab-s2-20261021/prepare_3701f795c13b4329891f4eca1346b3a5";
const string runtime="C:/work/fraktal-ab-s2-20261021/runtime_ff4a0406689d44478b85ee71f6f94799";
const string original="C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD";
const string baselineSha="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084";
static string Hash(string p)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p)));
static async Task Python(string path) {
    var info=new ProcessStartInfo("python") { UseShellExecute=false };
    info.ArgumentList.Add(path);
    using var process=Process.Start(info)??throw new Exception("Guard failed to start");
    await process.WaitForExitAsync();
    if(process.ExitCode!=0)throw new Exception("Recovery guard refused");
}
using(var a=JsonDocument.Parse(File.ReadAllText(Path.Combine(work,"authorization.json")))) {
    var x=a.RootElement;
    if(!x.GetProperty("CurrentOwnerApproved").GetBoolean() || x.GetProperty("Serial").GetString()!="601FC87B" ||
       x.GetProperty("CanonicalSha256").GetString()!=File.ReadAllText(Path.Combine(work,"canonical.sha256")).Trim() ||
       !x.GetProperty("Scope").EnumerateArray().Any(v=>v.GetString()=="genealogy rollback"))
        throw new Exception("Current S2 genealogy rollback authorization missing");
}
using(var c=JsonDocument.Parse(File.ReadAllText(Path.Combine(work,"capacity_review.json")))) {
    var x=c.RootElement;
    if(!x.GetProperty("OwnerConfirmedFit").GetBoolean() || x.GetProperty("BaselineSha256").GetString()!=baselineSha ||
       x.GetProperty("BaselineUsedStandardBlocks").GetInt64()>x.GetProperty("BaselineTotalBlocks").GetInt64())
        throw new Exception("Baseline Capacity gate missing");
}
var export=Path.Combine(runtime,"genealogy_recovered.L5X");
if(File.Exists(export))throw new Exception("Append-only recovery export exists");
if(Hash(original)!=baselineSha)throw new Exception("Pinned original changed");
await Python(Path.Combine(runtime,"recovery_empty_guard.py"));
var copy=Path.Combine(runtime,"genealogy_recovery_"+Guid.NewGuid().ToString("N")+".ACD");
File.Copy(original,copy,false);
if(Hash(copy)!=baselineSha)throw new Exception("Recovery copy mismatch");
using var project=await LogixProject.OpenLogixProjectAsync(copy,new StdOutEventLogger());
await project.SetCommunicationsPathAsync("EmulateEthernet\\127.0.0.1");
await Python(Path.Combine(runtime,"recovery_empty_guard.py"));
if(await project.ReadControllerModeAsync()!=LogixProject.ControllerMode.Program)throw new Exception("Empty controller mode changed");
await project.DownloadAsync();
await project.SaveAsync();
await Python(Path.Combine(work,"scripts/guard_echo.py"));
await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Run);
await project.SaveAsync();
await project.SaveAsAsync(export,true);
var mode=await project.ReadControllerModeAsync();
if(mode!=LogixProject.ControllerMode.Run || Hash(original)!=baselineSha)throw new Exception("Recovery final state or original hash failed");
Console.WriteLine(JsonSerializer.Serialize(new {RecoveredFrom=copy,OriginalSha256=baselineSha,FinalMode=mode.ToString(),Export=export}));
