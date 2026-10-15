<# Test-only power cycle of the exact owner Fraktal virtual controller. #>
$ErrorActionPreference='Stop'
$asm=[Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\5.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$manager=$asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
$infos=@($manager.GetProperty('RegisteredInstanceInfo').GetValue($null))
if ($infos.Count -ne 1 -or $infos[0].Name -ne 'Fraktal') { throw 'Expected only owner Fraktal' }
$instance=$manager.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@('Fraktal'))
function Guard([bool]$CheckAddresses) {
  if ($instance.Name -ne 'Fraktal' -or "$($instance.CPUType)" -ne 'CPU1516' -or "$($instance.CommunicationInterface)" -ne 'TCPIP') { throw 'Virtual identity differs' }
  foreach ($index in 0,1,2) { if ($instance.GetNetInterfaceMapping($index) -ne 0) { throw 'Physical mapping present' } }
  if ($CheckAddresses -and '169.254.212.49' -notin @($instance.ControllerIP)) { throw 'Virtual target differs' }
  [ordered]@{utc=[datetime]::UtcNow.ToString('o');name=$instance.Name;cpu="$($instance.CPUType)";state="$($instance.OperatingState)";comm="$($instance.CommunicationInterface)";addresses=@($instance.ControllerIP);ie1=$instance.GetNetInterfaceMapping(0);ie2=$instance.GetNetInterfaceMapping(1);ie3=$instance.GetNetInterfaceMapping(2)} | ConvertTo-Json -Compress
}
Guard $true
$instance.PowerOff(30000) | Out-Null
Guard $false
$instance.PowerOn(60000) | Out-Null
Guard $true
$instance.Run(30000)
Guard $true
