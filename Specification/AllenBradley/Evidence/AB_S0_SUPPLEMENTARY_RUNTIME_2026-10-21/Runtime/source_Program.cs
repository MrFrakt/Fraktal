// Guarded S0 session on local Echo 601FC87B. Controller operations require
// current owner authorization; this offline preparation grants none.
// prepare-probe: offline import/build/save; backup: upload the genealogy image;
// deploy-probe: download the S0 probe; restore-genealogy: download the
// hash-pinned genealogy ACD back. Every controller step re-runs the identity guard.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string root="C:/work/fraktal-ab-s0-supplementary-20261020/prepare_da41a9b11aad4d10938044fdcdcb4005";
const string route="EmulateEthernet\\127.0.0.1";
const string genealogyAcd="C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD";
const string genealogySha="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084";
var source=Path.Combine(root,"generated_final/s0s_combined.L5X");
var probe=Path.Combine(root,"s0_probe.ACD");
var backupPath=Path.Combine(root,"echo_before_s0.ACD");
static string Hash(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Python(string path, params string[] args) {
    var info=new ProcessStartInfo("python") { UseShellExecute=false };
    info.ArgumentList.Add(path);
    foreach (var arg in args) info.ArgumentList.Add(arg);
    using var process=Process.Start(info)??throw new Exception("Guard failed to start");
    await process.WaitForExitAsync();
    if (process.ExitCode!=0) throw new Exception("Exact target/configuration guard refused");
}
static Task Guard()=>Python("C:/work/fraktal-ab-s0-supplementary-20261020/prepare_da41a9b11aad4d10938044fdcdcb4005/scripts/guard_echo.py");
static async Task Download(string acd, string exportName) {
    if (File.Exists(Path.Combine(root,exportName))) throw new Exception("Append-only download export already exists");
    using var project=await LogixProject.OpenLogixProjectAsync(acd,new StdOutEventLogger());
    await project.SetCommunicationsPathAsync(route);
    await Guard();
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
var modes=new[]{"prepare-probe","backup","deploy-probe","restore-genealogy"};
if (args.Length!=1 || Array.IndexOf(modes,args[0])<0) throw new ArgumentException(string.Join(", ",modes)+" required");
if (args[0]=="prepare-probe") {
    if (new[]{probe,Path.Combine(root,"probe.sha256"),Path.Combine(root,"probe_prepared_readback.L5X")}.Any(File.Exists)) throw new Exception("Append-only prepared artifact exists");
    using (var gates=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"native_summary.json"))))
        {
            if (!gates.RootElement.GetProperty("passed").GetBoolean()) throw new Exception("Native compiler gates are not green");
            var combined=gates.RootElement.GetProperty("rows").EnumerateArray().Where(r=>r.GetProperty("case").GetString()=="combined").ToArray();
            if (combined.Length!=2 || combined.Any(r=>!string.Equals(r.GetProperty("sourceSha256").GetString(),Hash(source),StringComparison.OrdinalIgnoreCase)))
                throw new Exception("Compiler results do not bind this exact source");
        }
    using var imported=await LogixProject.OpenLogixProjectAsync(source,new StdOutEventLogger());
    await imported.BuildAsync(LogixProject.RequestedBuildTarget.EchoController,CancellationToken.None);
    await imported.SaveAsAsync(probe,true);
    using var prepared=await LogixProject.OpenLogixProjectAsync(probe,new StdOutEventLogger());
    await prepared.BuildAsync(LogixProject.RequestedBuildTarget.EchoController,CancellationToken.None);
    await prepared.SaveAsync();
    await prepared.SaveAsAsync(Path.Combine(root,"probe_prepared_readback.L5X"),true);
    File.WriteAllText(Path.Combine(root,"probe.sha256"),Hash(probe));
    Console.WriteLine(JsonSerializer.Serialize(new {Prepared=probe,Sha256=Hash(probe)}));
    return 0;
}
// The owner approval is recorded for this new session and this exact ACD.
using (var authorization=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"authorization.json")))) {
    var approved=authorization.RootElement;
    if (!approved.GetProperty("CurrentOwnerApproved").GetBoolean() ||
        approved.GetProperty("Serial").GetString()!="601FC87B" ||
        approved.GetProperty("ProbeSha256").GetString()!=File.ReadAllText(Path.Combine(root,"probe.sha256")).Trim())
        throw new Exception("Current target/artifact owner authorization missing");
}
if (args[0]=="backup") {
    if (File.Exists(backupPath)) throw new Exception("Backup exists");
    await Guard();
    await Python(Path.Combine(root,"scripts/preflight.py"),"--verify-only");
    using var uploaded=await LogixProject.UploadToNewProjectAsync(backupPath,route,new StdOutEventLogger());
    await uploaded.SaveAsync();
    await uploaded.SaveAsAsync(Path.Combine(root,"echo_before_s0.L5X"),true);
    File.WriteAllText(Path.Combine(root,"backup.sha256"),Hash(backupPath));
    Console.WriteLine(JsonSerializer.Serialize(new {Backup=backupPath,Sha256=Hash(backupPath)}));
    return 0;
}
if (args[0]=="deploy-probe") {
    using (var capacity=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"capacity_review.json")))) {
        var estimate=capacity.RootElement;
        if (!estimate.GetProperty("OwnerConfirmedFit").GetBoolean() ||
            estimate.GetProperty("ProbeSha256").GetString()!=File.ReadAllText(Path.Combine(root,"probe.sha256")).Trim() ||
            estimate.GetProperty("CapacityUnit").GetString()!="Blocks" ||
            estimate.GetProperty("UsedStandardBlocks").GetInt64()<0 ||
            estimate.GetProperty("AvailableBlocks").GetInt64()<0 ||
            estimate.GetProperty("TotalBlocks").GetInt64()<=0 ||
            estimate.GetProperty("UsedStandardBlocks").GetInt64()>estimate.GetProperty("TotalBlocks").GetInt64() ||
            estimate.GetProperty("AvailableBlocks").GetInt64()!=estimate.GetProperty("TotalBlocks").GetInt64()-estimate.GetProperty("UsedStandardBlocks").GetInt64())
            throw new Exception("Exact-artifact owner Capacity Estimate gate not satisfied");
    }
    if (!File.Exists(backupPath)||Hash(backupPath)!=File.ReadAllText(Path.Combine(root,"backup.sha256")).Trim()) throw new Exception("Current backup missing or changed");
    if (Hash(probe)!=File.ReadAllText(Path.Combine(root,"probe.sha256")).Trim()) throw new Exception("Probe ACD changed");
    using (var check=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"probe_prepared_compare.json"))))
        if (!check.RootElement.GetProperty("Equivalent").GetBoolean()) throw new Exception("Prepared probe readback differs");
    await Python(Path.Combine(root,"scripts/preflight.py"),"--verify-only");
    using (var attempt=new FileStream(Path.Combine(root,"deploy_attempt.json"),FileMode.CreateNew,FileAccess.Write))
        JsonSerializer.Serialize(attempt,new {Serial="601FC87B",ProbeSha256=Hash(probe),Utc=DateTime.UtcNow});
    await Download(probe,"probe_downloaded.L5X");
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
        attempt.RootElement.GetProperty("ProbeSha256").GetString()!=File.ReadAllText(Path.Combine(root,"probe.sha256")).Trim())
        throw new Exception("No matching authorized probe download attempt to restore");
await Guard();
await Download(restoreCopy,"genealogy_restored.L5X");
return 0;
