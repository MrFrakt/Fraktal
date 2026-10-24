// Restore the already approved hash-pinned genealogy image only to verified empty Echo.
// Original S3h session guards and sentinels stay unchanged.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string root="C:/work/fraktal-ab-s3h-20261024/recovery_768ff2a0acb34093b2bbb90f95538b17";
const string preparation="C:/work/fraktal-ab-s3h-20261023/diagnostic_0b74f072e0d74c7c97531e07dec70898";
const string original="C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD";
const string baselineSha="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084";
const string candidateSha="C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC";
static string Hash(string p)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p)));
static bool Permit(bool current,string serial,string candidate,bool recovery,bool fault,bool clock)=>
    current && serial=="601FC87B" && candidate==candidateSha && recovery && !fault && !clock;
static async Task Python(string path) {
    var info=new ProcessStartInfo("C:/Python314/python.exe") {UseShellExecute=false};
    info.ArgumentList.Add(path);
    using var child=Process.Start(info)??throw new Exception("Guard failed to start");
    await child.WaitForExitAsync();
    if(child.ExitCode!=0)throw new Exception("Recovery target/source guard refused");
}
if(args.SequenceEqual(new[]{"selftest"})) {
    var cases=new[]{
        Permit(true,"601FC87B",candidateSha,true,false,false),
        !Permit(false,"601FC87B",candidateSha,true,false,false),
        !Permit(true,"00000000",candidateSha,true,false,false),
        !Permit(true,"601FC87B","changed",true,false,false),
        !Permit(true,"601FC87B",candidateSha,false,false,false),
        !Permit(true,"601FC87B",candidateSha,true,true,false),
        !Permit(true,"601FC87B",candidateSha,true,false,true)
    };
    if(cases.Any(p=>!p))throw new Exception("Authorization test failed");
    Console.WriteLine(JsonSerializer.Serialize(new {Passed=true,AuthorizationCases=cases.Length,ControllerChanges=0}));
    return 0;
}
if(!args.SequenceEqual(new[]{"restore-empty"}))throw new ArgumentException("selftest or restore-empty required");
using(var a=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"authorization.json")))) {
    var x=a.RootElement;
    if(!Permit(x.GetProperty("CurrentOwnerApproved").GetBoolean(),x.GetProperty("Serial").GetString()??"",
        x.GetProperty("CanonicalSha256").GetString()??"",x.GetProperty("EmptyGenealogyRecoveryAuthorized").GetBoolean(),
        x.GetProperty("FaultClearAuthorized").GetBoolean(),x.GetProperty("ClockSetAuthorized").GetBoolean()))
        throw new Exception("Current exact-target empty genealogy recovery authorization missing");
}
using(var a=JsonDocument.Parse(File.ReadAllText(Path.Combine(preparation,"authorization.json")))) {
    var x=a.RootElement;
    if(!x.GetProperty("CurrentOwnerApproved").GetBoolean() || x.GetProperty("Serial").GetString()!="601FC87B" ||
        x.GetProperty("CanonicalSha256").GetString()!=candidateSha ||
        x.GetProperty("ApprovalQuestion").GetString()!="call_b76d12f2f038411386f83c339fcd94e0:0" ||
        !(x.GetProperty("Scope").GetString()??"").Contains("hash-checked genealogy rollback"))
        throw new Exception("Existing genealogy recovery/fixture scope changed");
}
using(var c=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"baseline_capacity.json")))) {
    var x=c.RootElement;
    if(!x.GetProperty("OwnerConfirmedFit").GetBoolean() || x.GetProperty("BaselineSha256").GetString()!=baselineSha ||
        x.GetProperty("BaselineUsedStandardBlocks").GetInt64()!=720352 ||
        x.GetProperty("BaselineAvailableBlocks").GetInt64()!=2425376 ||
        x.GetProperty("BaselineTotalBlocks").GetInt64()!=3145728)
        throw new Exception("Hash-pinned genealogy Capacity evidence changed");
}
var export=Path.Combine(root,"genealogy_recovered.L5X");
if(File.Exists(export)||File.Exists(Path.Combine(root,"recovery_attempt.json")))throw new Exception("One-shot recovery already attempted");
if(Hash(original)!=baselineSha)throw new Exception("Pinned genealogy original changed");
await Python(Path.Combine(root,"empty_guard.py"));
var copy=Path.Combine(root,"genealogy_copy_"+Guid.NewGuid().ToString("N")+".ACD");
File.Copy(original,copy,false);
if(Hash(copy)!=baselineSha)throw new Exception("Recovery copy hash mismatch");
using var project=await LogixProject.OpenLogixProjectAsync(copy,new StdOutEventLogger());
await project.SetCommunicationsPathAsync("EmulateEthernet\\127.0.0.1");
await Python(Path.Combine(root,"empty_guard.py"));
if(await project.ReadControllerModeAsync()!=LogixProject.ControllerMode.Program)throw new Exception("Empty target left Program mode");
using(var marker=new FileStream(Path.Combine(root,"recovery_attempt.json"),FileMode.CreateNew,FileAccess.Write))
    JsonSerializer.Serialize(marker,new {Serial="601FC87B",GenealogySha256=baselineSha,Utc=DateTime.UtcNow});
await project.DownloadAsync();
await project.SaveAsync();
await Python(Path.Combine(preparation,"scripts/guard_echo.py"));
await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Run);
await project.SaveAsync();
await project.SaveAsAsync(export,true);
var mode=await project.ReadControllerModeAsync();
if(mode!=LogixProject.ControllerMode.Run||Hash(original)!=baselineSha)throw new Exception("Recovery final state or original hash check failed");
Console.WriteLine(JsonSerializer.Serialize(new {RecoveredFrom=copy,OriginalSha256=baselineSha,FinalMode=mode.ToString(),Export=export}));
return 0;
