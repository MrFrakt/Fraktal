<# Restore only the existing saved Fraktal image after the owner's VM reboot. #>
param([switch] $KeepAlive)
$ErrorActionPreference='Stop'
$asm=[Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\5.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$manager=$asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
function Emit($kind,$data) { ([ordered]@{utc=[datetime]::UtcNow.ToString('o');event=$kind}+$data) | ConvertTo-Json -Compress -Depth 5 }
$infos=@($manager.GetProperty('RegisteredInstanceInfo').GetValue($null))
if ($infos.Count -ne 0) { throw 'Restore requires zero registered instances after reboot' }
$savedPath=Join-Path $manager.GetProperty('DefaultStoragePath').GetValue($null) 'Fraktal'
$savedPath=[IO.Path]::GetFullPath($savedPath)
if ($savedPath -ne 'C:\Users\Siemens\Documents\Siemens\Simatic\Simulation\Runtime\Persistence\Fraktal') { throw 'Saved owner path differs' }
$hardware=Get-Content -LiteralPath (Join-Path $savedPath 'sim_hwdb.ini') -Raw | ConvertFrom-Json
if ($hardware.'CPU Ordering Number'.Trim() -ne '6ES7 516-3AP03-0AB0' -or $hardware.'CPU Family' -ne 'VPLC1500') { throw 'Saved CPU identity differs' }
if (-not (Test-Path -LiteralPath (Join-Path $savedPath 'SIMATIC_MC') -PathType Container)) { throw 'Saved memory card absent' }
$adapter=@(Get-NetAdapter | Where-Object InterfaceDescription -eq 'Siemens PLCSIM Virtual Ethernet Adapter')
if ($adapter.Count -ne 1 -or $adapter[0].Status -ne 'Up') { throw 'Virtual adapter differs' }
$ips=@(Get-NetIPAddress -InterfaceIndex $adapter[0].ifIndex -AddressFamily IPv4)
if ($ips.Count -ne 1 -or $ips[0].PrefixLength -ne 16 -or $ips[0].IPAddress -notlike '169.254.*') { throw 'Virtual subnet differs' }
$savedHashes=@(Get-ChildItem -LiteralPath $savedPath -File -Recurse | ForEach-Object {
  [ordered]@{path=$_.FullName.Substring($savedPath.Length+1);sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
})
if ($savedHashes.Count -lt 3) { throw 'Saved image incomplete' }
Emit 'saved-image' @{path=$savedPath;files=$savedHashes;bootUtc=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o');virtualAddress=$ips[0].IPAddress}
$manager.GetProperty('NetworkMode').SetValue($null,[enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ECommunicationMode'),'Non_Promiscuous'))
$cpu=[enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ECPUType'),'CPU1516')
$instance=$manager.GetMethod('RegisterInstance',[type[]]@($cpu.GetType(),[string])).Invoke($null,@($cpu,'Fraktal'))
if ($instance.Name -ne 'Fraktal' -or [IO.Path]::GetFullPath($instance.StoragePath).TrimEnd('\') -ne $savedPath) { throw 'Registered identity/storage differs' }
foreach ($index in 0,1,2) { if ($instance.GetNetInterfaceMapping($index) -ne 0) { throw 'Physical mapping present' } }
$instance.CommunicationInterface=[enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ECommunicationInterface'),'TCPIP')
for ($attempt=1; $attempt -le 3; $attempt++) {
  try { $result=$instance.PowerOn(60000); Emit 'power-on' @{result="$result";attempt=$attempt}; break }
  catch { Emit 'power-on-retry' @{attempt=$attempt;message=$_.Exception.Message}; if ($attempt -eq 3) { throw }; Start-Sleep -Seconds 5 }
}
if ("$($instance.CPUType)" -ne 'CPU1516') { throw 'Saved image did not restore CPU1516' }
$suite=[Activator]::CreateInstance($asm.GetType('Siemens.Simatic.Simulation.Runtime.SIPSuite4'))
foreach ($pair in @(@('IPAddress','169.254.212.49'),@('SubnetMask','255.255.0.0'),@('DefaultGateway','0.0.0.0'))) {
  $component=[Activator]::CreateInstance($asm.GetType('Siemens.Simatic.Simulation.Runtime.SIP'))
  $component.IPString=$pair[1]; $suite.($pair[0])=$component
}
$instance.SetIPSuite(0,$suite,$true)
foreach ($index in 0,1,2) { if ($instance.GetNetInterfaceMapping($index) -ne 0) { throw 'Physical mapping present after power-on' } }
if ('169.254.212.49' -notin @($instance.ControllerIP) -or "$($instance.CommunicationInterface)" -ne 'TCPIP') { throw 'Restored target differs' }
$instance.Run(30000)
Emit 'restored' @{name=$instance.Name;cpu="$($instance.CPUType)";state="$($instance.OperatingState)";comm="$($instance.CommunicationInterface)";addresses=@($instance.ControllerIP);ie1=$instance.GetNetInterfaceMapping(0);ie2=$instance.GetNetInterfaceMapping(1);ie3=$instance.GetNetInterfaceMapping(2);storage=$instance.StoragePath}
if ("$($instance.OperatingState)" -ne 'Run') { throw 'Saved CPU is not RUN' }
if ($KeepAlive) {
  # The registering API client owns the registration. Keep it alive without an
  # expiry or an unregister/power-off cleanup; the owner can attach the control panel.
  Emit 'keeper' @{pid=$PID;stopFile=(Join-Path $PSScriptRoot 'owner_keeper.stop')}
  while (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'owner_keeper.stop'))) {
    Start-Sleep -Seconds 5
  }
}
