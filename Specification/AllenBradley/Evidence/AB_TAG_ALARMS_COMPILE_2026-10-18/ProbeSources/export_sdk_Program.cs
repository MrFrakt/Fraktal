using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;
if(args.Length!=2 || !File.Exists(args[0]) || File.Exists(args[1])) return 2;
using var project=await LogixProject.OpenLogixProjectAsync(args[0],new StdOutEventLogger());
await project.SaveAsAsync(args[1],true);
return 0;
