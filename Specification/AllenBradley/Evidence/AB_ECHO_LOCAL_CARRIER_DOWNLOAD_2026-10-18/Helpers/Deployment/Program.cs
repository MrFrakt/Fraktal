// One authorized session, loopback Echo only. Does not extend OfflineProbe.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string root = "C:/work/fraktal-echo-deploy-20261018";
const string route = @"EmulateEthernet\127.0.0.1";
var candidate = Path.Combine(root, "part_traceability.ACD");
if (args.Length != 1 || args[0] is not ("inspect" or "backup" or "prepare" or "deploy-authorized"))
    throw new ArgumentException("Expected inspect, backup, prepare or deploy-authorized");

static async Task Guard()
{
    var start = new ProcessStartInfo("python") { UseShellExecute=false };
    start.ArgumentList.Add("C:/work/fraktal-echo-deploy-20261018/guard_echo.py");
    using var process = Process.Start(start) ?? throw new Exception("Guard failed to start");
    await process.WaitForExitAsync();
    if (process.ExitCode != 0) throw new Exception("Exact Echo identity guard rejected operation");
}
static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));

if (args[0] == "backup")
{
    var backup = Path.Combine(root, "echo_before.ACD");
    if (File.Exists(backup)) throw new Exception("Refusing existing backup");
    await Guard();
    using var uploaded = await LogixProject.UploadToNewProjectAsync(backup, route, new StdOutEventLogger());
    await uploaded.SaveAsync();
    await uploaded.SaveAsAsync(Path.Combine(root, "echo_before.L5X"), true);
    Console.WriteLine(JsonSerializer.Serialize(new { Backup=backup, Sha256=Hash(backup) }));
    return 0;
}

using var project = await LogixProject.OpenLogixProjectAsync(candidate, new StdOutEventLogger());
if (args[0] == "prepare")
{
    await project.BuildAsync(LogixProject.RequestedBuildTarget.EchoController, CancellationToken.None);
    await project.SaveAsync();
    await project.SaveAsAsync(Path.Combine(root, "prepared_readback.L5X"), true);
    File.WriteAllText(Path.Combine(root,"prepared.sha256"), Hash(candidate));
    Console.WriteLine(JsonSerializer.Serialize(new { Prepared=candidate, Sha256=Hash(candidate) }));
    return 0;
}

await project.SetCommunicationsPathAsync(route);
await Guard();
var mode = await project.ReadControllerModeAsync();
Console.WriteLine($"ECHO MODE {mode}");
if (args[0] == "inspect") return 0;

var expected = File.ReadAllText(Path.Combine(root,"prepared.sha256")).Trim();
if (Hash(candidate) != expected) throw new Exception("Prepared ACD changed");
if (!File.Exists(Path.Combine(root,"echo_before.ACD"))) throw new Exception("Backup missing");
if (!File.Exists(Path.Combine(root,"preflight.json"))) throw new Exception("Readback preflight missing");
using (var gate = JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"preflight.json"))))
    if (!gate.RootElement.GetProperty("Equivalent").GetBoolean()) throw new Exception("Readback gate failed");

if (mode != LogixProject.ControllerMode.Program)
{
    if (mode != LogixProject.ControllerMode.Run && mode != LogixProject.ControllerMode.Faulted)
        throw new Exception("Unexpected starting mode");
    await Guard();
    await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Program);
}
await Guard();
await project.DownloadAsync();
await project.SaveAsync();
await Guard();
await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Run);
var finalMode = await project.ReadControllerModeAsync();
await project.SaveAsync();
await project.SaveAsAsync(Path.Combine(root,"downloaded.L5X"), true);
Console.WriteLine(JsonSerializer.Serialize(new { Target=route, ExpectedSerial="601FC87B",
    PreparedSha256=expected, DownloadCompleted=true, FinalMode=finalMode.ToString(),
    AcdSha256=Hash(candidate) }));
return finalMode == LogixProject.ControllerMode.Run ? 0 : 1;
