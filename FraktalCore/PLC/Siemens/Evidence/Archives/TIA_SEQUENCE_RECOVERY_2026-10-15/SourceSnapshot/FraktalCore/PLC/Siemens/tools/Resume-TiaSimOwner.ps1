<# Restore the existing persisted Fraktal bench after a workstation restart.
   This keeper has no expiry and never powers off/unregisters on exit. #>
param()
$ErrorActionPreference = 'Stop'
$restoreAsm = [Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\5.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$restoreManager = $restoreAsm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
$restoreName = 'Fraktal'
function Emit-Restore($kind, $fields) {
  ([ordered]@{t=[datetime]::UtcNow.ToString('o');event=$kind}+$fields) | ConvertTo-Json -Compress
}
$restoreInfos = @($restoreManager.GetProperty('RegisteredInstanceInfo').GetValue($null))
if ($restoreInfos.Count -gt 1 -or ($restoreInfos.Count -eq 1 -and $restoreInfos[0].Name -ne $restoreName)) {
  throw 'Unexpected simulator owner; no registration changed'
}
$restoreFolder = Join-Path $restoreManager.GetProperty('DefaultStoragePath').GetValue($null) $restoreName
if (-not (Test-Path -LiteralPath $restoreFolder -PathType Container)) { throw 'Persisted Fraktal storage is required' }
$restoreAdapter = @(Get-NetAdapter | Where-Object InterfaceDescription -eq 'Siemens PLCSIM Virtual Ethernet Adapter')
if ($restoreAdapter.Count -ne 1 -or $restoreAdapter[0].Status -ne 'Up') { throw 'Isolated virtual adapter unavailable' }
$restoreAddresses = @(Get-NetIPAddress -InterfaceIndex $restoreAdapter[0].ifIndex -AddressFamily IPv4)
if ($restoreAddresses.Count -ne 1 -or $restoreAddresses[0].PrefixLength -ne 16 -or $restoreAddresses[0].IPAddress -notlike '169.254.*') {
  throw 'Virtual subnet differs; no adapter configuration changed'
}
if ($restoreInfos.Count -eq 0) {
  $restoreMode = [enum]::Parse($restoreAsm.GetType('Siemens.Simatic.Simulation.Runtime.ECommunicationMode'),'Non_Promiscuous')
  $restoreManager.GetProperty('NetworkMode').SetValue($null,$restoreMode)
  $restoreInstance = $restoreManager.GetMethod('RegisterInstance',[type[]]@([string])).Invoke($null,@($restoreName))
  Emit-Restore 'persisted-owner-registered' @{name=$restoreName;storage=$restoreFolder}
  $restoreInstance.CommunicationInterface = [enum]::Parse($restoreAsm.GetType('Siemens.Simatic.Simulation.Runtime.ECommunicationInterface'),'TCPIP')
} else {
  $restoreInstance = $restoreManager.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@($restoreName))
}
foreach ($restoreInterface in 0,1,2) {
  if ($restoreInstance.GetNetInterfaceMapping($restoreInterface) -ne 0) { throw 'Physical mapping present; refusing bench operations' }
}
if ("$($restoreInstance.OperatingState)" -eq 'Off') {
  for ($restoreAttempt = 1; $restoreAttempt -le 3; $restoreAttempt++) {
    try {
      $restoreResult = $restoreInstance.PowerOn(60000)
      Emit-Restore 'power-on' @{result="$restoreResult";attempt=$restoreAttempt}
      break
    } catch {
      Emit-Restore 'power-on-retry' @{attempt=$restoreAttempt;message=$_.Exception.InnerException.Message}
      if ($restoreAttempt -eq 3) { throw }
      Start-Sleep -Seconds 5
    }
  }
}
$restoreStatus = @{name=$restoreName;cpu="$($restoreInstance.CPUType)";comm="$($restoreInstance.CommunicationInterface)";
  state="$($restoreInstance.OperatingState)";addresses=@($restoreInstance.ControllerIP)}
Emit-Restore 'restored-owner' $restoreStatus
if ($restoreStatus.cpu -ne 'CPU1516' -or $restoreStatus.comm -ne 'TCPIP' -or $restoreStatus.addresses -notcontains '169.254.212.49') {
  throw 'Persisted target identity differs; no address, image or certificate replaced'
}
while ($true) { Start-Sleep -Seconds 5 }
