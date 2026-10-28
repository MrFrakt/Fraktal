// Offline only: import/build/save an L5X as an ACD, reopen/build/save, export read-back.
// No communications path, upload, download, mode change or tag write.
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

static string Hash(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
if (args.Length!=3) throw new ArgumentException("source.L5X output.ACD readback.L5X");
var (source,acd,readback)=(Path.GetFullPath(args[0]),Path.GetFullPath(args[1]),Path.GetFullPath(args[2]));
if (new[]{acd,readback}.Any(File.Exists)) throw new Exception("Append-only output exists");
var sourceSha=Hash(source);
using (var imported=await LogixProject.OpenLogixProjectAsync(source,new StdOutEventLogger()))
{
    await imported.BuildAsync(LogixProject.RequestedBuildTarget.EchoController,CancellationToken.None);
    await imported.SaveAsAsync(acd,true);
}
using (var prepared=await LogixProject.OpenLogixProjectAsync(acd,new StdOutEventLogger()))
{
    await prepared.BuildAsync(LogixProject.RequestedBuildTarget.EchoController,CancellationToken.None);
    await prepared.SaveAsync();
    await prepared.SaveAsAsync(readback,true);
}
if (Hash(source)!=sourceSha) throw new Exception("Source changed during preparation");
Console.WriteLine(JsonSerializer.Serialize(new {Source=source,SourceSha256=sourceSha,Prepared=acd,Sha256=Hash(acd),Readback=readback}));
return 0;
