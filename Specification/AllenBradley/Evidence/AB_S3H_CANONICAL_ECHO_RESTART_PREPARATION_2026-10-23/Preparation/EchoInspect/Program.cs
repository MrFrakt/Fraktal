// Read-only service metadata. No update, enable, mode, fault or clock operation.
using System.Text.Json;
using RockwellAutomation.FactoryTalkLogixEcho.Api.Client;
var client=ClientFactory.GetServiceApiClientV2("Fraktal read-only Echo readiness");
if(args.Length==1 && args[0]=="methods") {
    Console.WriteLine(JsonSerializer.Serialize(client.GetType().GetMethods()
        .Where(m=>m.Name.Contains("Controller") || m.Name.Contains("Start") || m.Name.Contains("Restart"))
        .Select(m=>m.ToString()).ToArray()));
    return;
}
var c=await client.ReadController(0x601FC87Bu);
if(c.SerialNumber!=0x601FC87Bu || c.IPConfigurationData.Address.ToString()!="127.0.0.1")
    throw new Exception("Exact local Echo metadata identity refused");
Console.WriteLine(JsonSerializer.Serialize(new {c.ControllerGuid,c.SerialNumber,c.ControllerName,c.Slot,
    Address=c.IPConfigurationData.Address.ToString(),c.FirmwarePackageName,c.FirmwarePackageVersion,
    c.IsEnabled,ErrorCode=c.ErrorCode.ToString(),Mode=c.ControllerMode.ToString(),
    KeySwitch=c.KeySwitchPosition.ToString(),c.IsFaulted,c.IsInRunMode,c.LoadedProjectName,c.ProjectPath}));
