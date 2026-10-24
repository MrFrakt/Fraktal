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

const string root="C:/work/fraktal-ab-s0-20261020/readiness_20edac489b6c46e2b6229c76d400e9e7";
const string route="EmulateEthernet\\127.0.0.1";
const string genealogyAcd="C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD";
const string genealogySha="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084";
var source=Path.Combine(root,"corrected_combined/s0_combined.L5X");
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
static Task Guard()=>Python("C:/work/fraktal-ab-s0-20261020/readiness_20edac489b6c46e2b6229c76d400e9e7/scripts/guard_echo.py");
static async Task Download(string acd, string exportName) {
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
    if (File.Exists(probe)) throw new Exception("Probe ACD exists");
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
    if (!File.Exists(backupPath)||Hash(backupPath)!=File.ReadAllText(Path.Combine(root,"backup.sha256")).Trim()) throw new Exception("Current backup missing or changed");
    if (Hash(probe)!=File.ReadAllText(Path.Combine(root,"probe.sha256")).Trim()) throw new Exception("Probe ACD changed");
    using (var check=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"probe_prepared_compare.json"))))
        if (!check.RootElement.GetProperty("Equivalent").GetBoolean()) throw new Exception("Prepared probe readback differs");
    await Python(Path.Combine(root,"scripts/preflight.py"),"--verify-only");
    await Download(probe,"probe_downloaded.L5X");
    return 0;
}
// restore-genealogy: only from the probe image, only a copy of the hash-pinned
// genealogy ACD. Download saves into the project it opens, and the original is
// bound by hash in AB_ECHO_REDOWNLOAD_2026-10-19, so it is never opened here.
var restoreCopy=Path.Combine(root,"genealogy_restore.ACD");
if (!File.Exists(restoreCopy)) {
    if (Hash(genealogyAcd)!=genealogySha) throw new Exception("Genealogy ACD changed");
    File.Copy(genealogyAcd,restoreCopy);
}
if (Hash(genealogyAcd)!=genealogySha) throw new Exception("Genealogy ACD changed");
await Python(Path.Combine(root,"scripts/probe_loaded.py"));
await Download(restoreCopy,"genealogy_restored.L5X");
return 0;
