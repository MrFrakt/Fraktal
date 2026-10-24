// Offline only: import/build/save the observation-frame S3h candidate as an ACD,
// reopen/build/save it, and export its read-back. This helper has no
// communications path, upload, download, mode change or tag write.
using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string root="C:/work/fraktal-ab-s3h-20261024/frame_b7a501a104b448438e1e3566840fa12f";
const string sourceSha="BF456BCA68745C39D0903D0DE96B9B8AD4EC9DC502E809F38DA82599D2EFB1F2";
var source=Path.Combine(root,"s3h_frame_candidate_01.L5X");
var acd=Path.Combine(root,"s3h_frame_canonical.ACD");
var readback=Path.Combine(root,"frame_prepared_readback.L5X");
var pin=Path.Combine(root,"frame_canonical.sha256");
static string Hash(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
if (args.Length!=0) throw new ArgumentException("no arguments");
if (new[]{acd,readback,pin}.Any(File.Exists)) throw new Exception("Append-only prepared artifact exists");
if (Hash(source)!=sourceSha) throw new Exception("Source differs from the compiled candidate");
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
File.WriteAllText(pin,Hash(acd));
Console.WriteLine(JsonSerializer.Serialize(new {Source=source,SourceSha256=sourceSha,Prepared=acd,Sha256=Hash(acd),Readback=readback,ReadbackSha256=Hash(readback)}));
return 0;
