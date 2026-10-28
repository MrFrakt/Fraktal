// Guarded S4b option A download on local Echo 601FC87B, derived from the S3j session.
// backup: upload the current genealogy image (reads the controller only);
// deploy-canonical: download the pinned S4b ACD copy; restore-genealogy: download a
// hash-checked copy of the pinned genealogy ACD. Each command needs its own flag in
// authorization.json, and every controller step re-runs the exact identity guard.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string root="C:/work/fraktal-ab-s4b-busy-witness-20261027/session_01";
const string route="EmulateEthernet\\127.0.0.1";
const string genealogyAcd="C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD";
const string genealogySha="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084";
const string scripts="C:/work/fraktal-ab-s4b-busy-witness-20261027/session_01/scripts";
var probe=Path.Combine(root,"s4b_read_view.ACD");
var backupPath=Path.Combine(root,"echo_before_s4b.ACD");
static string Hash(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Python(string path, params string[] args) {
    var info=new ProcessStartInfo("C:/Python314/python.exe") { UseShellExecute=false };
    info.ArgumentList.Add(path);
    foreach (var arg in args) info.ArgumentList.Add(arg);
    using var process=Process.Start(info)??throw new Exception("Guard failed to start");
    await process.WaitForExitAsync();
    if (process.ExitCode!=0) throw new Exception("Exact target/configuration guard refused");
}
static Task Guard()=>Python(scripts+"/guard_echo.py");
static async Task Download(string acd, string exportName, bool fromBaseline) {
    if (File.Exists(Path.Combine(root,exportName))) throw new Exception("Append-only download export already exists");
    using var project=await LogixProject.OpenLogixProjectAsync(acd,new StdOutEventLogger());
    await project.SetCommunicationsPathAsync(route);
    await Guard();
    // Opening an ACD takes time: recheck idle/logout/config immediately before
    // leaving the genealogy baseline.
    if (fromBaseline) await Python(scripts+"/preflight.py","--verify-only");
    else await Python(root+"/pre_restore_guard.py");
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
var modes=new[]{"backup","deploy-canonical","restore-genealogy"};
if (args.Length!=1 || Array.IndexOf(modes,args[0])<0) throw new ArgumentException(string.Join(", ",modes)+" required");
var canonical=File.ReadAllText(Path.Combine(root,"canonical.sha256")).Trim();
if (canonical!="30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5")
    throw new Exception("Pinned S4b artifact differs");
using (var authorization=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"authorization.json")))) {
    var approved=authorization.RootElement;
    var flag=args[0] switch { "backup"=>"BackupUploadAuthorized", "deploy-canonical"=>"DownloadAuthorized", _=>"RestoreGenealogyAuthorized" };
    if (!approved.GetProperty("CurrentOwnerApproved").GetBoolean() || !approved.GetProperty(flag).GetBoolean() ||
        approved.GetProperty("FaultClearAuthorized").GetBoolean() || approved.GetProperty("ClockSetAuthorized").GetBoolean() ||
        approved.GetProperty("PowerOperationsAuthorized").GetBoolean() || approved.GetProperty("VendorStateEditsAuthorized").GetBoolean() ||
        approved.GetProperty("SourceSha256").GetString()!="60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E" ||
        approved.GetProperty("Serial").GetString()!="601FC87B" || approved.GetProperty("CanonicalSha256").GetString()!=canonical)
        throw new Exception("Current target/artifact owner authorization missing for "+args[0]);
}
if (args[0]=="backup") {
    if (File.Exists(backupPath)) throw new Exception("Backup exists");
    await Guard();
    await Python(scripts+"/preflight.py","--verify-only");
    using var uploaded=await LogixProject.UploadToNewProjectAsync(backupPath,route,new StdOutEventLogger());
    await uploaded.SaveAsync();
    await uploaded.SaveAsAsync(Path.Combine(root,"echo_before_s4b.L5X"),true);
    File.WriteAllText(Path.Combine(root,"backup.sha256"),Hash(backupPath));
    Console.WriteLine(JsonSerializer.Serialize(new {Backup=backupPath,Sha256=Hash(backupPath)}));
    return 0;
}
if (args[0]=="deploy-canonical") {
    using (var capacity=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"capacity_review.json"))))
    using (var authorization=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"authorization.json")))) {
        var estimate=capacity.RootElement;
        var owner=authorization.RootElement.GetProperty("OwnerCapacityConfirmed");
        var used=estimate.GetProperty("UsedStandardBlocks").GetInt64();
        var available=estimate.GetProperty("AvailableBlocks").GetInt64();
        var total=estimate.GetProperty("TotalBlocks").GetInt64();
        if (!estimate.GetProperty("VerifiedFit").GetBoolean() || !estimate.GetProperty("Measured").GetBoolean() ||
            !estimate.GetProperty("Offline").GetBoolean() || !estimate.GetProperty("SourceUnchanged").GetBoolean() ||
            estimate.GetProperty("Provider").GetString()!="StudioUIAutomation" ||
            estimate.GetProperty("CanonicalSha256").GetString()!=canonical ||
            estimate.GetProperty("CapacityUnit").GetString()!="Blocks" ||
            used<0 || available<0 || total<=0 || available!=total-used ||
            owner.GetProperty("UsedStandardBlocks").GetInt64()!=used ||
            owner.GetProperty("AvailableBlocks").GetInt64()!=available ||
            owner.GetProperty("TotalBlocks").GetInt64()!=total)
            throw new Exception("Exact-artifact Capacity Estimate gate not satisfied");
    }
    if (!File.Exists(backupPath)||Hash(backupPath)!=File.ReadAllText(Path.Combine(root,"backup.sha256")).Trim()) throw new Exception("Current backup missing or changed");
    if (Hash(probe)!=canonical) throw new Exception("Probe ACD changed");
    using (var check=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_prepared_compare.json"))))
        if (!check.RootElement.GetProperty("Equivalent").GetBoolean()) throw new Exception("Prepared probe readback differs");
    await Python(scripts+"/preflight.py","--verify-only");
    using (var attempt=new FileStream(Path.Combine(root,"deploy_attempt.json"),FileMode.CreateNew,FileAccess.Write))
        JsonSerializer.Serialize(attempt,new {Serial="601FC87B",CanonicalSha256=Hash(probe),Utc=DateTime.UtcNow});
    await Download(probe,"canonical_downloaded.L5X",true);
    return 0;
}
// restore-genealogy: only after this session's download attempt, only from a copy of
// the hash-pinned genealogy ACD (Download saves into the project it opens).
var restoreCopy=Path.Combine(root,"genealogy_restore_"+Guid.NewGuid().ToString("N")+".ACD");
if (Hash(genealogyAcd)!=genealogySha) throw new Exception("Genealogy ACD changed");
File.Copy(genealogyAcd,restoreCopy,false);
if (Hash(restoreCopy)!=genealogySha) throw new Exception("Rollback copy does not match pinned original");
using (var attempt=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"deploy_attempt.json"))))
    if (attempt.RootElement.GetProperty("Serial").GetString()!="601FC87B" ||
        attempt.RootElement.GetProperty("CanonicalSha256").GetString()!=canonical)
        throw new Exception("No matching authorized download attempt to restore");
await Guard();
await Download(restoreCopy,"genealogy_restored.L5X",false);
return 0;
