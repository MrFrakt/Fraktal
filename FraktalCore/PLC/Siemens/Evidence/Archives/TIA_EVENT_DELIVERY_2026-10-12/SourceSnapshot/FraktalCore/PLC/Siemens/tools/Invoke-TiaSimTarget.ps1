<# Adopt the owner's empty Fraktal instance for the isolated 1500 Web API bench. #>
param([ValidateSet('adopt','status')] [string] $Action='status')
$ErrorActionPreference='Stop'
$simAsm=[Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\5.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$simManager=$simAsm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
$simInfos=@($simManager.GetProperty('RegisteredInstanceInfo').GetValue($null))
if ($simInfos.Count -ne 1 -or $simInfos[0].Name -ne 'Fraktal') { throw 'Expected only the owner-created Fraktal instance' }
$simInstance=$simManager.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@('Fraktal'))
function Snapshot {
  [ordered]@{utc=[datetime]::UtcNow.ToString('o');name=$simInstance.Name;cpu="$($simInstance.CPUType)";
    comm="$($simInstance.CommunicationInterface)";state="$($simInstance.OperatingState)";
    addresses=@($simInstance.ControllerIP);ie1=$simInstance.GetNetInterfaceMapping(0);
    ie2=$simInstance.GetNetInterfaceMapping(1);ie3=$simInstance.GetNetInterfaceMapping(2);
    networkMode=[int]$simManager.GetProperty('NetworkMode').GetValue($null)}
}
$simBefore=Snapshot
$simBefore | ConvertTo-Json -Compress
if ($Action -eq 'status') { exit }
if ($simBefore.cpu -ne 'CPU1500_Unspecified' -or $simBefore.comm -ne 'Softbus' -or $simBefore.state -ne 'Stop' -or $simBefore.addresses.Count -ne 1 -or $simBefore.addresses[0] -ne '192.168.0.1' -or $simBefore.ie1 -ne 0 -or $simBefore.ie2 -ne 0 -or $simBefore.ie3 -ne 0) { throw 'Owner instance no longer matches the empty stopped target' }
$simAdapter=@(Get-NetAdapter | Where-Object InterfaceDescription -eq 'Siemens PLCSIM Virtual Ethernet Adapter')
if ($simAdapter.Count -ne 1 -or $simAdapter[0].Status -ne 'Up') { throw 'Expected the isolated virtual Ethernet adapter' }
$simIps=@(Get-NetIPAddress -InterfaceIndex $simAdapter[0].ifIndex -AddressFamily IPv4)
if ($simIps.Count -ne 1 -or $simIps[0].PrefixLength -ne 16 -or $simIps[0].IPAddress -notlike '169.254.*') { throw 'Virtual subnet differs' }
$simInstance.PowerOff(30000) | Out-Null
$simInstance.CPUType=[enum]::Parse($simAsm.GetType('Siemens.Simatic.Simulation.Runtime.ECPUType'),'CPU1516')
$simInstance.CommunicationInterface=[enum]::Parse($simAsm.GetType('Siemens.Simatic.Simulation.Runtime.ECommunicationInterface'),'TCPIP')
$simInstance.PowerOn(60000) | Out-Null
$simSuite=[Activator]::CreateInstance($simAsm.GetType('Siemens.Simatic.Simulation.Runtime.SIPSuite4'))
foreach ($simPair in @(@('IPAddress','169.254.212.49'),@('SubnetMask','255.255.0.0'),@('DefaultGateway','0.0.0.0'))) {
  $simComponent=[Activator]::CreateInstance($simAsm.GetType('Siemens.Simatic.Simulation.Runtime.SIP'))
  $simComponent.IPString=$simPair[1]
  $simSuite.($simPair[0])=$simComponent
}
$simInstance.SetIPSuite(0,$simSuite,$true)
Snapshot | ConvertTo-Json -Compress
