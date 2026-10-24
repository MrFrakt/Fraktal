// Guarded local Echo session for the regenerated current-source image (2026-10-19).
// prepare: offline import/build/save; backup: upload the running image first;
// deploy-authorized: guarded Program -> Download -> Run. Same shape as the
// AB_PART_GENEALOGY_2026-10-19 session; only paths and the source hash differ.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string root="C:/work/fraktal-ab-echo-20261019";
const string route="EmulateEthernet\\127.0.0.1";
var source=Path.Combine(root,"genealogy_current.L5X");
var candidate=Path.Combine(root,"genealogy_current.ACD");
var backupPath=Path.Combine(root,"echo_before_redownload.ACD");
static string Hash(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Python(string path, params string[] args) {
    var info=new ProcessStartInfo("python") { UseShellExecute=false };
    info.ArgumentList.Add(path);
    foreach (var arg in args) info.ArgumentList.Add(arg);
    using var process=Process.Start(info)??throw new Exception("Guard failed to start");
    await process.WaitForExitAsync();
    if (process.ExitCode!=0) throw new Exception("Exact target/configuration guard refused");
}
static Task Guard()=>Python("C:/work/fraktal-ab-echo-20261019/scripts/guard_echo.py");
if (args.Length!=1 || args[0] is not ("prepare" or "backup" or "deploy-authorized")) throw new ArgumentException("prepare, backup or deploy-authorized required");
if (args[0]=="prepare") {
    if (File.Exists(candidate)||Hash(source)!="91BF67C9101EAE863CF29C1A9DF6413D7256AB056D985394587F0183AA525714") throw new Exception("Source guard refused");
    using var imported=await LogixProject.OpenLogixProjectAsync(source,new StdOutEventLogger());
    await imported.BuildAsync(LogixProject.RequestedBuildTarget.EchoController,CancellationToken.None);
    await imported.SaveAsAsync(candidate,true);
    using var prepared=await LogixProject.OpenLogixProjectAsync(candidate,new StdOutEventLogger());
    await prepared.BuildAsync(LogixProject.RequestedBuildTarget.EchoController,CancellationToken.None);
    await prepared.SaveAsync();
    await prepared.SaveAsAsync(Path.Combine(root,"prepared_readback.L5X"),true);
    File.WriteAllText(Path.Combine(root,"prepared.sha256"),Hash(candidate));
    Console.WriteLine(JsonSerializer.Serialize(new {Prepared=candidate,Sha256=Hash(candidate)}));
    return 0;
}
if (args[0]=="backup") {
    if (File.Exists(backupPath)) throw new Exception("Backup exists");
    await Guard();
    await Python(Path.Combine(root,"scripts/preflight.py"),"--verify-only");
    using var uploaded=await LogixProject.UploadToNewProjectAsync(backupPath,route,new StdOutEventLogger());
    await uploaded.SaveAsync();
    await uploaded.SaveAsAsync(Path.Combine(root,"echo_before_redownload.L5X"),true);
    File.WriteAllText(Path.Combine(root,"backup.sha256"),Hash(backupPath));
    Console.WriteLine(JsonSerializer.Serialize(new {Backup=backupPath,Sha256=Hash(backupPath)}));
    return 0;
}
if (!File.Exists(backupPath)||Hash(backupPath)!=File.ReadAllText(Path.Combine(root,"backup.sha256")).Trim()) throw new Exception("Current backup missing or changed");
if (Hash(candidate)!=File.ReadAllText(Path.Combine(root,"prepared.sha256")).Trim()) throw new Exception("Prepared ACD changed");
using (var check=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"prepared_compare.json"))))
    if (!check.RootElement.GetProperty("Equivalent").GetBoolean()) throw new Exception("Actual prepared readback differs");
using var project=await LogixProject.OpenLogixProjectAsync(candidate,new StdOutEventLogger());
await project.SetCommunicationsPathAsync(route);
await Python(Path.Combine(root,"scripts/preflight.py"),"--verify-only");
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
await project.SaveAsAsync(Path.Combine(root,"downloaded_current.L5X"),true);
var final=await project.ReadControllerModeAsync();
Console.WriteLine(JsonSerializer.Serialize(new {Downloaded=true,FinalMode=final.ToString(),AcdSha256=Hash(candidate)}));
return final==LogixProject.ControllerMode.Run?0:1;
