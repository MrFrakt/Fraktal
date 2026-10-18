<# Fixed, disposable native-protocol bench. Never modifies the owner's Fraktal instance. #>
param(
  [ValidateSet('host','status','read','run')] [string] $Action = 'status',
  [string] $StopFile
)
$ErrorActionPreference = 'Stop'
$benchName = 'FrkIoBridgeTest'
$benchAddress = '169.254.212.51'
$asm = [Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\5.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$manager = $asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
function Emit($kind,$value) { (@{event=$kind}+$value) | ConvertTo-Json -Compress -Depth 5 }
function Find-Bench {
  foreach ($info in $manager.GetProperty('RegisteredInstanceInfo').GetValue($null)) {
    if ($info.Name -eq $benchName) {
      return $manager.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@($benchName))
    }
  }
  return $null
}
function Assert-Bench($instance,[bool]$AllowEmpty=$false) {
  if (-not $instance) { throw 'Protocol bench is not registered' }
  $empty = $AllowEmpty -and "$($instance.CPUType)" -eq 'CPU1500_Unspecified' -and "$($instance.OperatingState)" -eq 'Stop'
  if (("$($instance.CPUType)" -ne 'CPU1516' -and -not $empty) -or "$($instance.CommunicationInterface)" -ne 'TCPIP') { throw 'Protocol bench CPU/transport differs' }
  $ips = @($instance.ControllerIP)
  if ($benchAddress -notin $ips -or @($ips | Where-Object { $_ -notin @($benchAddress,'172.31.254.51') }).Count -ne 0 -or $ips.Count -gt 2) { throw 'Protocol bench address differs' }
  foreach ($number in 0,1,2) { if ($instance.GetNetInterfaceMapping($number) -ne 0) { throw 'Protocol bench is mapped to real networking' } }
  Emit 'bench' @{name=$benchName;cpu="$($instance.CPUType)";state="$($instance.OperatingState)";address=$benchAddress;ie1=0;ie2=0;ie3=0}
}
if ($Action -eq 'host') {
  if (-not $StopFile -or (Test-Path -LiteralPath $StopFile)) { throw 'A new, absent stop-file path is required' }
  if (Find-Bench) { throw 'Refusing to take ownership of an existing protocol bench' }
  if ("$($manager.GetProperty('NetworkMode').GetValue($null))" -ne 'Non_Promiscuous') { throw 'Preserve network mode; this bench requires existing Non_Promiscuous mode' }
  $adapter = @(Get-NetAdapter | Where-Object InterfaceDescription -eq 'Siemens PLCSIM Virtual Ethernet Adapter')
  if ($adapter.Count -ne 1 -or $adapter[0].Status -ne 'Up') { throw 'Exactly one enabled virtual adapter is required' }
  $addresses = @(Get-NetIPAddress -InterfaceIndex $adapter[0].ifIndex -AddressFamily IPv4)
  if ($addresses.Count -ne 1 -or $addresses[0].PrefixLength -ne 16 -or $addresses[0].IPAddress -notlike '169.254.*' -or $addresses[0].IPAddress -eq $benchAddress) { throw 'Unexpected virtual adapter configuration' }
  $before = @($manager.GetProperty('RegisteredInstanceInfo').GetValue($null) | ForEach-Object { $_.Name })
  Emit 'preserved-instances' @{names=$before}
  $cpu = [enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ECPUType'),'CPU1516')
  $instance = $manager.GetMethod('RegisterInstance',[type[]]@($cpu.GetType(),[string])).Invoke($null,@($cpu,$benchName))
  try {
    $instance.CommunicationInterface = [enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ECommunicationInterface'),'TCPIP')
    foreach ($number in 0,1,2) { $instance.SetNetInterfaceMapping($number,[uint32]0) }
    $result = $instance.PowerOn(60000)
    Emit 'power-on' @{result="$result"}
    $suite = [Activator]::CreateInstance($asm.GetType('Siemens.Simatic.Simulation.Runtime.SIPSuite4'))
    foreach ($pair in @(@('IPAddress',$benchAddress),@('SubnetMask','255.255.0.0'),@('DefaultGateway','0.0.0.0'))) {
      $part = [Activator]::CreateInstance($asm.GetType('Siemens.Simatic.Simulation.Runtime.SIP'))
      $part.IPString = $pair[1]
      $suite.($pair[0]) = $part
    }
    $instance.SetIPSuite(0,$suite,$true)
    Assert-Bench $instance $true
    $deadline = [datetime]::UtcNow.AddMinutes(30)
    while (-not (Test-Path -LiteralPath $StopFile) -and [datetime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 500 }
  } finally {
    # Only the newly registered bench is ours. Keep its storage and every
    # pre-existing registration; no directory cleanup or global mode changes.
    if ($instance) {
      $instance.PowerOff(30000) | Out-Null
      $instance.UnregisterInstance()
    }
    $after = @($manager.GetProperty('RegisteredInstanceInfo').GetValue($null) | ForEach-Object { $_.Name })
    Emit 'preserved-instances-after' @{names=$after}
  }
  exit
}
$instance = Find-Bench
Assert-Bench $instance ($Action -eq 'status')
if ($Action -eq 'run') { $instance.Run(30000) | Out-Null; Assert-Bench $instance; exit }
if ($Action -eq 'status') { exit }
$details = [enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ETagListDetails'),'DB')
$instance.UpdateTagList($details,$false,'"GDB_IoBridgeProtocolTest"')
$values = @{}
foreach ($tag in $instance.TagInfos) {
  if ($tag.Name -notmatch '\.(Done|Checks|Failures|FirstFailure)$') { continue }
  $key = $Matches[1]
  $native = $instance.Read($tag.Name)
  $values[$key] = $native."$($native.Type)"
}
if ($values.Count -ne 4) { throw 'Protocol bench result interface incomplete' }
Emit 'protocol-results' $values
if (-not $values.Done -or $values.Failures -ne 0 -or $values.FirstFailure -ne 0 -or $values.Checks -ne 18) { throw 'Native protocol checks failed' }
