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
    var info=new ProcessStartInfo("C:/Python314/python.exe") { UseShellExecute=false };
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
var copy=Path.Combine(runtime,"genealogy_recovery_bba0675c4a7945959f5bac7cd36bd1fc.ACD");
if(Hash(original)!=baselineSha)throw new Exception("Pinned original changed");
var previous=File.ReadAllText(Path.Combine(runtime,"recovery_01.log"));
if(!previous.Contains("] Download succeeded") || !previous.Contains("] Save succeeded"))throw new Exception("No successful recovery download");
var export=Path.Combine(runtime,"genealogy_recovered_run.L5X");
if(File.Exists(export))throw new Exception("Append-only export exists");
using var project=await LogixProject.OpenLogixProjectAsync(copy,new StdOutEventLogger());
await project.SetCommunicationsPathAsync("EmulateEthernet\\127.0.0.1");
await Python(Path.Combine(runtime,"recovered_image_guard.py"));
var mode=await project.ReadControllerModeAsync();
if(mode is not (LogixProject.ControllerMode.Program or LogixProject.ControllerMode.Run))throw new Exception("Unexpected mode");
if(mode!=LogixProject.ControllerMode.Run) {
    await Python(Path.Combine(runtime,"recovered_image_guard.py"));
    await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Run);
}
await project.SaveAsync();
await project.SaveAsAsync(export,true);
if(await project.ReadControllerModeAsync()!=LogixProject.ControllerMode.Run || Hash(original)!=baselineSha)throw new Exception("Run recovery final state failed");
Console.WriteLine(JsonSerializer.Serialize(new {FinalMode="Run",Export=export,OriginalSha256=baselineSha}));
