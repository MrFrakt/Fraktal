<# Isolated S12 TCP/IP simulation. No host or physical-adapter configuration. #>
param([ValidateSet('host','status','read','run','halt')] [string] $Action = 'status',
      [string] $DataBlocks = 'S12Probe', [string] $Match = '.', [int] $MaxMinutes = 120)
$ErrorActionPreference = 'Stop'
$asm = [Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\5.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$manager = $asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
$instanceName = 'FrkS12'
if ($env:FRAKTAL_TIA_SIM_INSTANCE) {
  if ($env:FRAKTAL_TIA_SIM_INSTANCE -notin @('FrkS12','Fraktal')) { throw 'Unapproved simulator name' }
  $instanceName = $env:FRAKTAL_TIA_SIM_INSTANCE
}
$address = '169.254.212.49'
function Emit($kind,$data) { ([ordered]@{t=[datetime]::UtcNow.ToString('o');event=$kind}+$data) | ConvertTo-Json -Compress }
function Find-Instance {
  foreach ($info in $manager.GetProperty('RegisteredInstanceInfo').GetValue($null)) {
    if ($info.Name -eq $instanceName) { return $manager.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@($instanceName)) }
  }
  return $null
}
function Instance-Status($inst) {
  Emit 'instance' @{name=$instanceName;state="$($inst.OperatingState)";cpu="$($inst.CPUType)";
    comm="$($inst.CommunicationInterface)";addresses=@($inst.ControllerIP);
    ie1=$inst.GetNetInterfaceMapping(0);ie2=$inst.GetNetInterfaceMapping(1);ie3=$inst.GetNetInterfaceMapping(2)}
}
if ($Action -eq 'host') {
  $runtimeFile = 'C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\Siemens.Simatic.Simulation.Runtime.Manager.exe'
  Emit 'runtime' @{apiPath=$asm.Location;apiVersion=(Get-Item -LiteralPath $asm.Location).VersionInfo.FileVersion;
    managerPath=$runtimeFile;managerProduct=(Get-Item -LiteralPath $runtimeFile).VersionInfo.ProductVersion;
    managerVersion=(Get-Item -LiteralPath $runtimeFile).VersionInfo.FileVersion}
  if ($manager.GetProperty('RegisteredInstanceInfo').GetValue($null).Length -ne 0) { throw 'S12 host requires no other registered simulator instances' }
  $adapter = @(Get-NetAdapter | Where-Object InterfaceDescription -eq 'Siemens PLCSIM Virtual Ethernet Adapter')
  if ($adapter.Count -ne 1 -or $adapter[0].Status -ne 'Up') { throw 'Exactly one enabled Siemens virtual adapter is required' }
  $ip = @(Get-NetIPAddress -InterfaceIndex $adapter[0].ifIndex -AddressFamily IPv4)
  if ($ip.Count -ne 1 -or $ip[0].PrefixLength -ne 16 -or $ip[0].IPAddress -notlike '169.254.*' -or $ip[0].IPAddress -eq $address) { throw 'Virtual adapter must be on the declared link-local subnet' }
  Emit 'virtual-adapter' @{index=$adapter[0].ifIndex;address=$ip[0].IPAddress;prefix=$ip[0].PrefixLength;target=$address}
  $priorMode = $manager.GetProperty('NetworkMode').GetValue($null)
  $newMode = [enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ECommunicationMode'),'Non_Promiscuous')
  $manager.GetProperty('NetworkMode').SetValue($null,$newMode)
  $cpu = [enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ECPUType'),'CPU1516')
  $inst = $manager.GetMethod('RegisterInstance',[type[]]@($cpu.GetType(),[string])).Invoke($null,@($cpu,$instanceName))
  $stopFile = Join-Path $env:TEMP 'plcsim_FrkS12.stop'
  Remove-Item -LiteralPath $stopFile -ErrorAction SilentlyContinue
  try {
    $inst.CommunicationInterface = [enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ECommunicationInterface'),'TCPIP')
    # Delete every physical adapter mapping. The virtual adapter is always local.
    foreach ($interfaceId in 0,1,2) { $inst.SetNetInterfaceMapping($interfaceId,[uint32]0) }
    $powerResult = $inst.PowerOn(60000)
    Emit 'power-on' @{result="$powerResult"}
    $suite = [Activator]::CreateInstance($asm.GetType('Siemens.Simatic.Simulation.Runtime.SIPSuite4'))
    foreach ($pair in @(@('IPAddress',$address),@('SubnetMask','255.255.0.0'),@('DefaultGateway','0.0.0.0'))) {
      $component = [Activator]::CreateInstance($asm.GetType('Siemens.Simatic.Simulation.Runtime.SIP'))
      $component.IPString = $pair[1]
      $suite.($pair[0]) = $component
    }
    $inst.SetIPSuite(0,$suite,$true)
    Instance-Status $inst
    $last = ''
    $deadline = [datetime]::UtcNow.AddMinutes($MaxMinutes)
    while (-not (Test-Path -LiteralPath $stopFile) -and [datetime]::UtcNow -lt $deadline) {
      $state = "$($inst.OperatingState)"
      if ($state -ne $last) { Instance-Status $inst; $last = $state }
      Start-Sleep -Seconds 2
    }
  } finally {
    try { $inst.PowerOff(30000) | Out-Null } catch { Emit 'shutdown-error' @{message=$_.Exception.Message} }
    try { $inst.UnregisterInstance() } catch { Emit 'unregister-error' @{message=$_.Exception.Message} }
    if ($manager.GetProperty('RegisteredInstanceInfo').GetValue($null).Length -eq 0) { $manager.GetProperty('NetworkMode').SetValue($null,$priorMode) }
    Emit 'unregistered' @{name=$instanceName;networkModeRestored="$priorMode"}
    Remove-Item -LiteralPath $stopFile -ErrorAction SilentlyContinue
  }
} else {
  $inst = Find-Instance
  if (-not $inst) { throw 'FrkS12 is not registered' }
  if ($Action -eq 'status') { Instance-Status $inst; exit }
  if ("$($inst.CPUType)" -ne 'CPU1516' -or "$($inst.CommunicationInterface)" -ne 'TCPIP' -or $address -notin @($inst.ControllerIP)) { throw 'S12 simulation target differs' }
  if ($Action -in 'run','halt') {
    if ($inst.GetNetInterfaceMapping(0) -ne 0 -or $inst.GetNetInterfaceMapping(1) -ne 0 -or $inst.GetNetInterfaceMapping(2) -ne 0) { throw 'S12 must have no physical adapter mappings' }
    Instance-Status $inst
    if ($Action -eq 'run') { $inst.Run(30000) } else { $inst.Stop(30000) }
    Instance-Status $inst
    exit
  }
  $details = [enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ETagListDetails'),'DB')
  $filter = (($DataBlocks -split ',') | ForEach-Object { '"' + $_.Trim() + '"' }) -join ','
  $inst.UpdateTagList($details,$false,$filter)
  $count = 0
  foreach ($leafTag in $inst.TagInfos) {
    if ("$($leafTag.PrimitiveDataType)" -in 'Struct','Array' -or $leafTag.Name -notmatch $Match) { continue }
    try {
      $typeName = "$($leafTag.DataType)"
      if ($typeName -eq 'String') { $valueRead = $inst.ReadString($leafTag.Name) }
      elseif ($typeName -eq 'WString') { $valueRead = $inst.ReadWString($leafTag.Name) }
      else { $nativeValue = $inst.Read($leafTag.Name); $valueRead = $nativeValue."$($nativeValue.Type)"; $typeName = "$($nativeValue.Type)" }
      Emit 'tag' @{name=$leafTag.Name;type=$typeName;value=$valueRead}
      $count++
    } catch { Emit 'tag-failed' @{name=$leafTag.Name;message=$_.Exception.InnerException.Message} }
  }
  if ($count -eq 0) { throw 'No readable S12 leaves' }
}
