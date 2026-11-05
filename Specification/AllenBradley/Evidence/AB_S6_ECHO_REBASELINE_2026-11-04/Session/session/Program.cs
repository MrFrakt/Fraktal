// Guarded re-baseline of local Echo 601FC87B after the owner's factory reset.
// Derived from the S5 session's restore-genealogy step: download a hash-checked
// copy of the pinned genealogy ACD, then Run. It refuses unless authorization.json
// carries the standing O3 record and its restore flag, the exact identity guard
// passes before every controller step, and the controller is still factory-empty
// (checked again immediately before leaving that state). Nothing else is offered.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string root="C:/work/fraktal-ab-s6-rebaseline-20261104/session_01";
const string route="EmulateEthernet\\127.0.0.1";
const string genealogyAcd="C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD";
const string genealogySha="D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084";
const string scripts=root+"/scripts";
static string Hash(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Python(string path, params string[] args) {
    var info=new ProcessStartInfo("C:/Python314/python.exe") { UseShellExecute=false };
    info.ArgumentList.Add(path);
    foreach (var arg in args) info.ArgumentList.Add(arg);
    using var process=Process.Start(info)??throw new Exception("Guard failed to start");
    await process.WaitForExitAsync();
    if (process.ExitCode!=0) throw new Exception("Exact target/precondition guard refused: "+path);
}
static Task Guard()=>Python(scripts+"/guard_echo.py");
if (args.Length!=1 || args[0]!="restore-genealogy") throw new ArgumentException("restore-genealogy required");
using (var authorization=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"authorization.json")))) {
    var approved=authorization.RootElement;
    if (!approved.GetProperty("CurrentOwnerApproved").GetBoolean() || approved.GetProperty("StandingDecision").GetString()!="O3" ||
        !approved.GetProperty("RestoreGenealogyAuthorized").GetBoolean() ||
        approved.GetProperty("FaultClearAuthorized").GetBoolean() || approved.GetProperty("ClockSetAuthorized").GetBoolean() ||
        approved.GetProperty("PowerOperationsAuthorized").GetBoolean() || approved.GetProperty("VendorStateEditsAuthorized").GetBoolean() ||
        approved.GetProperty("Serial").GetString()!="601FC87B" || approved.GetProperty("CanonicalSha256").GetString()!=genealogySha)
        throw new Exception("Standing O3 restore authorization for this exact pin missing");
}
var exportPath=Path.Combine(root,"genealogy_restored.L5X");
if (File.Exists(exportPath)) throw new Exception("Append-only download export already exists");
if (Hash(genealogyAcd)!=genealogySha) throw new Exception("Genealogy ACD changed");
// Download saves into the project it opens, so the pinned original is never opened.
var restoreCopy=Path.Combine(root,"genealogy_restore_"+Guid.NewGuid().ToString("N")+".ACD");
File.Copy(genealogyAcd,restoreCopy,false);
if (Hash(restoreCopy)!=genealogySha) throw new Exception("Rollback copy does not match pinned original");
await Guard();
using var project=await LogixProject.OpenLogixProjectAsync(restoreCopy,new StdOutEventLogger());
await project.SetCommunicationsPathAsync(route);
await Guard();
// Opening an ACD takes time: recheck the factory-empty precondition immediately before Program mode.
await Python(root+"/pre_download_guard.py","--verify-only");
var mode=await project.ReadControllerModeAsync();
if (mode is not (LogixProject.ControllerMode.Run or LogixProject.ControllerMode.Program)) throw new Exception("Controller mode is not ready for download");
if (mode!=LogixProject.ControllerMode.Program) {
    await Guard();
    await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Program);
}
await Guard();
using (var attempt=new FileStream(Path.Combine(root,"download_attempt.json"),FileMode.CreateNew,FileAccess.Write))
    JsonSerializer.Serialize(attempt,new {Serial="601FC87B",CanonicalSha256=genealogySha,Utc=DateTime.UtcNow});
await project.DownloadAsync();
await project.SaveAsync();
await Guard();
await project.ChangeControllerModeAsync(LogixProject.RequestedControllerMode.Run);
await project.SaveAsync();
await project.SaveAsAsync(exportPath,true);
var final=await project.ReadControllerModeAsync();
Console.WriteLine(JsonSerializer.Serialize(new {Downloaded=restoreCopy,FinalMode=final.ToString(),AcdSha256=genealogySha}));
if (final!=LogixProject.ControllerMode.Run) throw new Exception("Controller did not return to Run");
return 0;
