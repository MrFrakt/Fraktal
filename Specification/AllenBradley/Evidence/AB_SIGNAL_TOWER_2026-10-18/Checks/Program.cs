using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string root = "C:/work/fraktal-ab-tower-20261018";
const string route = "EmulateEthernet\\127.0.0.1";
var source = Path.Combine(root,"tower_03.L5X");
var candidate = Path.Combine(root,"tower_03.ACD");
static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Guard() {
    var info = new ProcessStartInfo("python") { UseShellExecute=false };
    info.ArgumentList.Add("C:/work/fraktal-echo-deploy-20261018/guard_echo.py");
    using var process=Process.Start(info) ?? throw new Exception("Identity guard did not start");
    await process.WaitForExitAsync();
    if (process.ExitCode!=0) throw new Exception("Exact local Echo identity refused");
}
if (args.Length!=1 || args[0] is not ("prepare" or "backup" or "deploy-authorized")) throw new ArgumentException("prepare, backup or deploy-authorized required");
if (args[0]=="backup") {
    var path=Path.Combine(root,"echo_before_tower.ACD");
    if (File.Exists(path)) throw new Exception("Backup already exists");
    await Guard();
    using var uploaded=await LogixProject.UploadToNewProjectAsync(path,route,new StdOutEventLogger());
    await uploaded.SaveAsync();
    await uploaded.SaveAsAsync(Path.Combine(root,"echo_before_tower.L5X"),true);
    Console.WriteLine(JsonSerializer.Serialize(new {Backup=path,Sha256=Hash(path)}));
    return 0;
}
if (args[0]=="prepare") {
    if (File.Exists(candidate) || Hash(source)!="03BE7A3D4F16118E328673F096EA06C250D2D64FC14027BE043B824F535A99ED") throw new Exception("Candidate source guard failed");
    using var imported=await LogixProject.OpenLogixProjectAsync(source,new StdOutEventLogger());
    await imported.BuildAsync(LogixProject.RequestedBuildTarget.EchoController,CancellationToken.None);
    await imported.SaveAsAsync(candidate,true);
    using var prepared=await LogixProject.OpenLogixProjectAsync(candidate,new StdOutEventLogger());
    await prepared.BuildAsync(LogixProject.RequestedBuildTarget.EchoController,CancellationToken.None);
    await prepared.SaveAsync();
    await prepared.SaveAsAsync(Path.Combine(root,"prepared_03_readback.L5X"),true);
    File.WriteAllText(Path.Combine(root,"prepared_03.sha256"),Hash(candidate));
    Console.WriteLine(JsonSerializer.Serialize(new {Prepared=candidate,Sha256=Hash(candidate)}));
    return 0;
}
if (!File.Exists(Path.Combine(root,"echo_before_tower.ACD"))) throw new Exception("Current backup is missing");
var expected=File.ReadAllText(Path.Combine(root,"prepared_03.sha256")).Trim();
if (Hash(candidate)!=expected) throw new Exception("Prepared ACD changed");
using (var check=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"prepared_03_compare.json"))))
    if (!check.RootElement.GetProperty("Equivalent").GetBoolean()) throw new Exception("Readback preflight refused");
using var project=await LogixProject.OpenLogixProjectAsync(candidate,new StdOutEventLogger());
await project.SetCommunicationsPathAsync(route);
await Guard();
var mode=await project.ReadControllerModeAsync();
if (mode is not (LogixProject.ControllerMode.Run or LogixProject.ControllerMode.Program)) throw new Exception("Controller is not ready for a normal download");
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
await project.SaveAsAsync(Path.Combine(root,"downloaded_tower.L5X"),true);
var final=await project.ReadControllerModeAsync();
Console.WriteLine(JsonSerializer.Serialize(new {PreparedSha256=expected,DownloadCompleted=true,FinalMode=final.ToString(),AcdSha256=Hash(candidate)}));
return final==LogixProject.ControllerMode.Run ? 0 : 1;
