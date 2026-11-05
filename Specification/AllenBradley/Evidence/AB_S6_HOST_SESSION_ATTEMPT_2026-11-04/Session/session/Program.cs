// Guarded S6 V6.11 host-services capture session on local Echo 601FC87B, derived
// from the S5 session. backup: upload the current genealogy image (reads only);
// deploy-candidate: download a hash-checked copy of the pinned candidate ACD;
// restore-genealogy: download a hash-checked copy of the pinned genealogy ACD.
// Pinned originals are never opened (a download saves into the project it opens).
// Each command needs its own flag in authorization.json; every controller step
// re-runs the exact identity guard.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string root="C:/work/fraktal-ab-s6-host-20261104/session_01";
const string route="EmulateEthernet\\127.0.0.1";
const string genealogyAcd="C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD";
const string genealogySha="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084";
const string candidateSha="A4B4FC7811DCE769EFAE14B175C1A9E51373A40310588EC92B164F81753417D3";
const string sourceSha="847C428935E2BFBA3A131E90F0DAC7BC15072B4158B83D5C804206BFB0352059";
const string scripts=root+"/scripts";
var candidateAcd=Path.Combine(root,"s6_host_04.ACD");
var backupPath=Path.Combine(root,"echo_before_s6.ACD");
static string Hash(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Python(string path, params string[] args) {
    var info=new ProcessStartInfo("C:/Python314/python.exe") { UseShellExecute=false };
    info.ArgumentList.Add(path);
    foreach (var arg in args) info.ArgumentList.Add(arg);
    using var process=Process.Start(info)??throw new Exception("Guard failed to start");
    await process.WaitForExitAsync();
    if (process.ExitCode!=0) throw new Exception("Exact target/configuration guard refused: "+path);
}
static Task Guard()=>Python(scripts+"/guard_echo.py");
static string Copy(string pinned, string sha, string name) {
    if (Hash(pinned)!=sha) throw new Exception("Pinned ACD changed: "+pinned);
    var copy=Path.Combine(root,name+"_"+Guid.NewGuid().ToString("N")+".ACD");
    File.Copy(pinned,copy,false);
    if (Hash(copy)!=sha) throw new Exception("Download copy does not match its pin");
    return copy;
}
static async Task Download(string acd, string exportName, string preCheck, params string[] preArgs) {
    if (File.Exists(Path.Combine(root,exportName))) throw new Exception("Append-only download export already exists");
    using var project=await LogixProject.OpenLogixProjectAsync(acd,new StdOutEventLogger());
    await project.SetCommunicationsPathAsync(route);
    await Guard();
    // Opening an ACD takes time: recheck idle/logout/config immediately before Program mode.
    await Python(preCheck,preArgs);
    var mode=await project.ReadControllerModeAsync();
    if (mode is not (LogixProject.ControllerMode.Run or LogixProject.ControllerMode.Program)) throw new Exception("Controller mode is not ready for download");
    if (mode!=LogixProject.ControllerMode.Program) {
        await Guard();
        await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Program);
    }
    await Guard();
    await project.DownloadAsync();
    await project.SaveAsync();
    await Guard();
    await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Run);
    await project.SaveAsync();
    await project.SaveAsAsync(Path.Combine(root,exportName),true);
    var final=await project.ReadControllerModeAsync();
    Console.WriteLine(JsonSerializer.Serialize(new {Downloaded=acd,FinalMode=final.ToString(),AcdSha256=Hash(acd)}));
    if (final!=LogixProject.ControllerMode.Run) throw new Exception("Controller did not return to Run");
}
var modes=new[]{"backup","deploy-candidate","restore-genealogy"};
if (args.Length!=1 || Array.IndexOf(modes,args[0])<0) throw new ArgumentException(string.Join(", ",modes)+" required");
using (var authorization=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"authorization.json")))) {
    var approved=authorization.RootElement;
    var flag=args[0] switch { "backup"=>"BackupUploadAuthorized", "deploy-candidate"=>"DownloadAuthorized", _=>"RestoreGenealogyAuthorized" };
    if (!approved.GetProperty("CurrentOwnerApproved").GetBoolean() || approved.GetProperty("StandingDecision").GetString()!="O3" ||
        !approved.GetProperty(flag).GetBoolean() ||
        approved.GetProperty("FaultClearAuthorized").GetBoolean() || approved.GetProperty("ClockSetAuthorized").GetBoolean() ||
        approved.GetProperty("PowerOperationsAuthorized").GetBoolean() || approved.GetProperty("VendorStateEditsAuthorized").GetBoolean() ||
        approved.GetProperty("SourceSha256").GetString()!=sourceSha || approved.GetProperty("CanonicalSha256").GetString()!=candidateSha ||
        approved.GetProperty("Serial").GetString()!="601FC87B")
        throw new Exception("Standing O3 authorization for this exact candidate missing for "+args[0]);
}
if (args[0]=="backup") {
    if (File.Exists(backupPath)) throw new Exception("Backup exists");
    await Guard();
    await Python(root+"/preflight.py","--verify-only");
    using var uploaded=await LogixProject.UploadToNewProjectAsync(backupPath,route,new StdOutEventLogger());
    await uploaded.SaveAsync();
    await uploaded.SaveAsAsync(Path.Combine(root,"echo_before_s6.L5X"),true);
    File.WriteAllText(Path.Combine(root,"backup.sha256"),Hash(backupPath));
    Console.WriteLine(JsonSerializer.Serialize(new {Backup=backupPath,Sha256=Hash(backupPath)}));
    return 0;
}
if (args[0]=="deploy-candidate") {
    using (var capacity=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"capacity_review.json")))) {
        var estimate=capacity.RootElement;
        var used=estimate.GetProperty("UsedStandardBlocks").GetInt64();
        var available=estimate.GetProperty("AvailableBlocks").GetInt64();
        var total=estimate.GetProperty("TotalBlocks").GetInt64();
        if (!estimate.GetProperty("VerifiedFit").GetBoolean() || !estimate.GetProperty("Measured").GetBoolean() ||
            !estimate.GetProperty("Offline").GetBoolean() || !estimate.GetProperty("SourceUnchanged").GetBoolean() ||
            estimate.GetProperty("Provider").GetString()!="StudioUIAutomation" ||
            estimate.GetProperty("CanonicalSha256").GetString()!=candidateSha ||
            estimate.GetProperty("CapacityUnit").GetString()!="Blocks" ||
            used<0 || available<0 || total<=0 || available!=total-used)
            throw new Exception("Exact-artifact Capacity Estimate gate not satisfied");
    }
    if (!File.Exists(backupPath)||Hash(backupPath)!=File.ReadAllText(Path.Combine(root,"backup.sha256")).Trim()) throw new Exception("Current backup missing or changed");
    var copy=Copy(candidateAcd,candidateSha,"candidate");
    await Python(root+"/preflight.py","--verify-only");
    using (var attempt=new FileStream(Path.Combine(root,"deploy_attempt.json"),FileMode.CreateNew,FileAccess.Write))
        JsonSerializer.Serialize(attempt,new {Serial="601FC87B",CanonicalSha256=candidateSha,Utc=DateTime.UtcNow});
    await Download(copy,"candidate_downloaded.L5X",root+"/preflight.py","--verify-only");
    return 0;
}
// restore-genealogy: only after this session's download attempt.
using (var attempt=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"deploy_attempt.json"))))
    if (attempt.RootElement.GetProperty("Serial").GetString()!="601FC87B" ||
        attempt.RootElement.GetProperty("CanonicalSha256").GetString()!=candidateSha)
        throw new Exception("No matching authorized download attempt to restore");
var restoreCopy=Copy(genealogyAcd,genealogySha,"genealogy_restore");
await Guard();
await Download(restoreCopy,"genealogy_restored.L5X",root+"/pre_restore_guard.py");
return 0;
