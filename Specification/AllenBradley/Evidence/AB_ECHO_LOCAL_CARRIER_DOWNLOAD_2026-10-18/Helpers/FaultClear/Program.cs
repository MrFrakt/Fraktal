// Authorized fault clear, using the installed public Echo SDK to operate the
// virtual keyswitch. The v38 help's Program/Remote route did not clear this
// Echo instance. This attempt uses Rockwell PM001's Program/Run/Program route.
using System.Diagnostics;
using System.Text.Json;
using RockwellAutomation.FactoryTalkLogixEcho.Api.Client;
using RockwellAutomation.FactoryTalkLogixEcho.Api.Interfaces;

if (args.Length != 1 || args[0] is not ("inspect" or "clear-authorized"))
    throw new ArgumentException("Expected inspect or clear-authorized");
var client = ClientFactory.GetServiceApiClientV2("Fraktal authorized local Echo commissioning");
var controller = await client.ReadController(0x601FC87Bu);

static object Summary(ControllerData c) => new { c.ControllerGuid, c.SerialNumber,
    c.ControllerName, c.ChassisName, c.Slot, c.ControllerMode, c.IsFaulted,
    c.KeySwitchPosition, Address=c.IPConfigurationData.Address.ToString() };
static async Task Guard()
{
    var start = new ProcessStartInfo("python") { UseShellExecute=false };
    start.ArgumentList.Add("C:/work/fraktal-echo-deploy-20261018/guard_echo.py");
    using var process = Process.Start(start) ?? throw new Exception("Cannot start guard");
    await process.WaitForExitAsync();
    if (process.ExitCode != 0) throw new Exception("Exact Echo identity guard refused");
}
void Verify(ControllerData c)
{
    if (c.SerialNumber != 0x601FC87Bu || c.IPConfigurationData.Address.ToString() != "127.0.0.1")
        throw new Exception("Wrong Echo controller");
}
Verify(controller);
Console.WriteLine(JsonSerializer.Serialize(Summary(controller)));
if (args[0] == "inspect") return 0;
var states = new List<object> { Summary(controller) };
foreach (var position in new[] { KeySwitchPosition.Program, KeySwitchPosition.Run,
                                KeySwitchPosition.Program, KeySwitchPosition.Remote })
{
    await Guard();
    controller = await client.ReadController(0x601FC87Bu);
    Verify(controller);
    var update = controller.ToControllerUpdate();
    update.KeySwitchPosition = position;
    await client.UpdateController(update);
    await Task.Delay(200);
    controller = await client.ReadController(0x601FC87Bu);
    Verify(controller);
    states.Add(Summary(controller));
    Console.WriteLine(JsonSerializer.Serialize(Summary(controller)));
}
File.WriteAllText("C:/work/fraktal-echo-deploy-20261018/fault_clear_states_02.json",
    JsonSerializer.Serialize(states,new JsonSerializerOptions { WriteIndented=true }));
return controller.IsFaulted ? 1 : 0;
