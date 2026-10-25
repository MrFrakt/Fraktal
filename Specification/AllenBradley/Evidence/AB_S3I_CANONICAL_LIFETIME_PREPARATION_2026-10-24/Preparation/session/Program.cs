// Guarded S3i lifetime session on local Echo 601FC87B. Controller operations require
// current owner authorization; this offline preparation grants none.
// Observation-frame S3i lifetime candidate; its ACD was prepared offline by the sealed S3i preparation.
// backup: upload the genealogy image;
// deploy-canonical: download the S3i lifetime candidate; restore-genealogy: download the
// hash-pinned genealogy ACD back. Every controller step re-runs the identity guard.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string root="C:/work/fraktal-ab-s3i-lifetime-20261024/prepare_9af0ac9f71534d89b5be9645bdc6575f";
const string route="EmulateEthernet\\127.0.0.1";
const string genealogyAcd="C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD";
const string genealogySha="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084";
var probe=Path.Combine(root,"s3i_canonical.ACD");
var backupPath=Path.Combine(root,"echo_before_s3i.ACD");
static string Hash(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Python(string path, params string[] args) {
    var info=new ProcessStartInfo("C:/Python314/python.exe") { UseShellExecute=false };
    info.ArgumentList.Add(path);
    foreach (var arg in args) info.ArgumentList.Add(arg);
    using var process=Process.Start(info)??throw new Exception("Guard failed to start");
    await process.WaitForExitAsync();
    if (process.ExitCode!=0) throw new Exception("Exact target/configuration guard refused");
}
static Task Guard()=>Python("C:/work/fraktal-ab-s3i-lifetime-20261024/prepare_9af0ac9f71534d89b5be9645bdc6575f/scripts/guard_echo.py");
static async Task Download(string acd, string exportName) {
    if (File.Exists(Path.Combine(root,exportName))) throw new Exception("Append-only download export already exists");
    using var project=await LogixProject.OpenLogixProjectAsync(acd,new StdOutEventLogger());
    await project.SetCommunicationsPathAsync(route);
    await Guard();
    // Opening an ACD takes time: recheck idle/logout/config after it opens,
    // immediately before entering the candidate's controller-changing path.
    // Rollback must remain available after an interrupted candidate session.
    if (exportName=="canonical_downloaded.L5X")
        await Python(Path.Combine(root,"scripts/preflight.py"),"--verify-only");
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
var modes=new[]{"backup","deploy-canonical","restore-genealogy","cycle-retained"};
if (args.Length!=1 || Array.IndexOf(modes,args[0])<0) throw new ArgumentException(string.Join(", ",modes)+" required");
// The owner approval is recorded for this new session and this exact ACD.
using (var authorization=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"authorization.json")))) {
    var approved=authorization.RootElement;
    if (!approved.GetProperty("CurrentOwnerApproved").GetBoolean() ||
        !approved.GetProperty("AccessVectorsAuthorized").GetBoolean() ||
        !approved.GetProperty("ConfigurationVectorsAuthorized").GetBoolean() ||
        !approved.GetProperty("NativeLineVectorsAuthorized").GetBoolean() ||
        !approved.GetProperty("CalendarLifetimeVectorsAuthorized").GetBoolean() ||
        !approved.GetProperty("RetainedCycleAuthorized").GetBoolean() ||
        approved.GetProperty("Serial").GetString()!="601FC87B" ||
        approved.GetProperty("CanonicalSha256").GetString()!=File.ReadAllText(Path.Combine(root,"canonical.sha256")).Trim())
        throw new Exception("Current target/artifact owner authorization missing");
}
if (args[0]=="cycle-retained") {
    var control=Path.Combine(root,"retention_control.ACD");
    var report=Path.Combine(root,"retained_cycle.json");
    var pin=File.ReadAllText(Path.Combine(root,"canonical.sha256")).Trim();
    if (File.Exists(report) || Hash(control)!=pin) throw new Exception("Retained control copy missing/changed or cycle already recorded");
    await Guard();
    await Python(Path.Combine(root,"scripts/retention_preflight.py"));
    LogixProject.ControllerMode before;
    LogixProject.ControllerMode after;
    using (var project=await LogixProject.OpenLogixProjectAsync(control,new StdOutEventLogger()))
    {
    await project.SetCommunicationsPathAsync(route);
    await Guard();
    await Python(Path.Combine(root,"scripts/retention_readiness.py"));
    before=await project.ReadControllerModeAsync();
    if (before!=LogixProject.ControllerMode.Run) throw new Exception("Retained cycle must start in Run");
    await Guard();
    await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Program);
    await Guard();
    await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Run);
    await Guard();
    after=await project.ReadControllerModeAsync();
    if (after!=LogixProject.ControllerMode.Run) throw new Exception("Retained cycle did not return to Run");
    }
    if (Hash(control)!=pin) throw new Exception("Retained cycle changed its control copy");
    using var output=new FileStream(report,FileMode.CreateNew,FileAccess.Write);
    JsonSerializer.Serialize(output,new {Passed=true,Before=before.ToString(),After=after.ToString(),DownloadPerformed=false,SourceAcdUnchanged=true,CanonicalSha256=pin});
    Console.WriteLine(JsonSerializer.Serialize(new {RetainedCycleCompleted=true,DownloadPerformed=false,FinalMode=after.ToString()}));
    return 0;
}
if (args[0]=="backup") {
    if (File.Exists(backupPath)) throw new Exception("Backup exists");
    await Guard();
    await Python(Path.Combine(root,"scripts/preflight.py"),"--verify-only");
    using var uploaded=await LogixProject.UploadToNewProjectAsync(backupPath,route,new StdOutEventLogger());
    await uploaded.SaveAsync();
    await uploaded.SaveAsAsync(Path.Combine(root,"echo_before_s3i.L5X"),true);
    File.WriteAllText(Path.Combine(root,"backup.sha256"),Hash(backupPath));
    Console.WriteLine(JsonSerializer.Serialize(new {Backup=backupPath,Sha256=Hash(backupPath)}));
    return 0;
}
if (args[0]=="deploy-canonical") {
    var baselineFile=Path.Combine(root,"baseline_capacity.json");
    using var baselineReference=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"baseline_reference.json")));
    if(Hash(baselineFile)!=baselineReference.RootElement.GetProperty("capacitySha256").GetString())
        throw new Exception("Prior-stage Capacity evidence changed");
    using var priorCapacity=JsonDocument.Parse(File.ReadAllText(baselineFile));
    var prior=priorCapacity.RootElement;
    using (var capacity=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"capacity_review.json")))) {
        var estimate=capacity.RootElement;
        if (!estimate.GetProperty("VerifiedFit").GetBoolean() ||
            !estimate.GetProperty("Measured").GetBoolean() ||
            estimate.GetProperty("Provider").GetString() is not ("OwnerStudio" or "StudioUIAutomation") ||
            estimate.GetProperty("CanonicalSha256").GetString()!=File.ReadAllText(Path.Combine(root,"canonical.sha256")).Trim() ||
            estimate.GetProperty("CapacityUnit").GetString()!="Blocks" ||
            estimate.GetProperty("UsedStandardBlocks").GetInt64()<0 ||
            estimate.GetProperty("AvailableBlocks").GetInt64()<0 ||
            estimate.GetProperty("TotalBlocks").GetInt64()<=0 ||
            estimate.GetProperty("UsedStandardBlocks").GetInt64()>estimate.GetProperty("TotalBlocks").GetInt64() ||
            estimate.GetProperty("AvailableBlocks").GetInt64()!=estimate.GetProperty("TotalBlocks").GetInt64()-estimate.GetProperty("UsedStandardBlocks").GetInt64() ||
            estimate.GetProperty("BaselineSha256").GetString()!=prior.GetProperty("CanonicalSha256").GetString() ||
            estimate.GetProperty("BaselineUsedStandardBlocks").GetInt64()!=prior.GetProperty("UsedStandardBlocks").GetInt64() ||
            estimate.GetProperty("BaselineAvailableBlocks").GetInt64()!=prior.GetProperty("AvailableBlocks").GetInt64() ||
            estimate.GetProperty("BaselineTotalBlocks").GetInt64()!=prior.GetProperty("TotalBlocks").GetInt64() ||
            estimate.GetProperty("BaselineUsedStandardBlocks").GetInt64()<0 ||
            estimate.GetProperty("BaselineAvailableBlocks").GetInt64()<0 ||
            estimate.GetProperty("BaselineTotalBlocks").GetInt64()!=estimate.GetProperty("TotalBlocks").GetInt64() ||
            estimate.GetProperty("BaselineAvailableBlocks").GetInt64()!=estimate.GetProperty("BaselineTotalBlocks").GetInt64()-estimate.GetProperty("BaselineUsedStandardBlocks").GetInt64())
            throw new Exception("Exact-artifact owner Capacity Estimate gate not satisfied");
    }
    if (!File.Exists(backupPath)||Hash(backupPath)!=File.ReadAllText(Path.Combine(root,"backup.sha256")).Trim()) throw new Exception("Current backup missing or changed");
    if (Hash(probe)!=File.ReadAllText(Path.Combine(root,"canonical.sha256")).Trim()) throw new Exception("Probe ACD changed");
    using (var check=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_prepared_compare.json"))))
        if (!check.RootElement.GetProperty("Equivalent").GetBoolean()) throw new Exception("Prepared probe readback differs");
    await Python(Path.Combine(root,"scripts/preflight.py"),"--verify-only");
    using (var attempt=new FileStream(Path.Combine(root,"deploy_attempt.json"),FileMode.CreateNew,FileAccess.Write))
        JsonSerializer.Serialize(attempt,new {Serial="601FC87B",CanonicalSha256=Hash(probe),Utc=DateTime.UtcNow});
    await Download(probe,"canonical_downloaded.L5X");
    return 0;
}
// restore-genealogy: only from the probe image, only a copy of the hash-pinned
// genealogy ACD. Download saves into the project it opens, and the original is
// bound by hash in AB_ECHO_REDOWNLOAD_2026-10-19, so it is never opened here.
var restoreCopy=Path.Combine(root,"genealogy_restore_"+Guid.NewGuid().ToString("N")+".ACD");
if (Hash(genealogyAcd)!=genealogySha) throw new Exception("Genealogy ACD changed");
File.Copy(genealogyAcd,restoreCopy,false);
if (Hash(restoreCopy)!=genealogySha) throw new Exception("Rollback copy does not match pinned original");
// Restoration remains available after an interrupted authorized download.
// Its source is a hash-checked copy; exact identity/fault/mode guards still run.
using (var attempt=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"deploy_attempt.json"))))
    if (attempt.RootElement.GetProperty("Serial").GetString()!="601FC87B" ||
        attempt.RootElement.GetProperty("CanonicalSha256").GetString()!=File.ReadAllText(Path.Combine(root,"canonical.sha256")).Trim())
        throw new Exception("No matching authorized probe download attempt to restore");
await Guard();
await Download(restoreCopy,"genealogy_restored.L5X");
return 0;
