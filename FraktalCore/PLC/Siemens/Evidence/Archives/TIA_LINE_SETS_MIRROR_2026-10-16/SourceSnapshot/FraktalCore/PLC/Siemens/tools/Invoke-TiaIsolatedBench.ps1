<# Own one newly registered, unmapped CPU1516 bench; preserve every existing instance. #>
param(
  [Parameter(Mandatory=$true)] [string] $Profile,
  [ValidateSet('host','status','run','read','restart','release')] [string] $Action = 'status',
  [string] $StopFile,
  [int] $ExpectedChecks = 0
)
$ErrorActionPreference = 'Stop'
$bench = Get-Content -LiteralPath $Profile -Raw | ConvertFrom-Json
$addressMatch = [regex]::Match([string]$bench.address, '^169\.254\.212\.(5[2-9]|60)$')
if ($bench.name -notmatch '^Frk[A-Za-z0-9]+Test$' -or -not $addressMatch.Success -or
    $bench.secondary -ne ('172.31.254.' + $addressMatch.Groups[1].Value) -or $bench.results -notmatch '^GDB_[A-Za-z0-9]+Test$') {
  throw 'Profile must identify a reserved isolated test CPU and result DB'
}
$benchName = [string]$bench.name
$benchAddress = [string]$bench.address
$secondary = [string]$bench.secondary
$resultBlock = [string]$bench.results
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
  if (-not $instance) { throw 'Bench is not registered' }
  $empty = $AllowEmpty -and "$($instance.CPUType)" -eq 'CPU1500_Unspecified' -and "$($instance.OperatingState)" -eq 'Stop'
  if (("$($instance.CPUType)" -ne 'CPU1516' -and -not $empty) -or "$($instance.CommunicationInterface)" -ne 'TCPIP') { throw 'Bench CPU/transport differs' }
  $ips = @($instance.ControllerIP)
  if ($benchAddress -notin $ips -or @($ips | Where-Object { $_ -notin @($benchAddress,$secondary) }).Count -ne 0 -or $ips.Count -gt 2) { throw 'Bench address differs' }
  foreach ($number in 0,1,2) { if ($instance.GetNetInterfaceMapping($number) -ne 0) { throw 'Bench is mapped to real networking' } }
  Emit 'bench' @{name=$benchName;cpu="$($instance.CPUType)";state="$($instance.OperatingState)";address=$benchAddress;ie1=0;ie2=0;ie3=0}
}
function Release-Bench($instance) {
  if ("$($instance.OperatingState)" -ne 'Off') {
    try { $instance.PowerOff(30000) | Out-Null }
    catch { if ("$($instance.OperatingState)" -ne 'Off') { throw } }
  }
  $instance.UnregisterInstance()
}
if ($Action -eq 'host') {
  $allowedRoot = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Fraktal\TiaSpikes')) + '\'
  if (-not $StopFile -or -not [IO.Path]::GetFullPath($StopFile).StartsWith($allowedRoot,[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $StopFile)) { throw 'A new stop-file inside TiaSpikes is required' }
  $existingBench = Find-Bench
  if ($existingBench) { $existingBench.Dispose(); throw 'Refusing to take ownership of an existing bench' }
  if ("$($manager.GetProperty('NetworkMode').GetValue($null))" -ne 'Non_Promiscuous') { throw 'Preserve network mode; bench requires existing Non_Promiscuous mode' }
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
    if ($instance) {
      try { Release-Bench $instance } finally { $instance.Dispose() }
    }
    $after = @($manager.GetProperty('RegisteredInstanceInfo').GetValue($null) | ForEach-Object { $_.Name })
    Emit 'preserved-instances-after' @{names=$after}
  }
  exit
}
$instance = Find-Bench
try {
Assert-Bench $instance ($Action -eq 'status')
if ($Action -eq 'release') {
  Release-Bench $instance
  Emit 'released' @{name=$benchName;storage='preserved'}
  exit
}
if ($Action -eq 'restart') {
  if ("$($instance.OperatingState)" -ne 'Off') { $instance.PowerOff(30000) | Out-Null }
  $instance.PowerOn(60000) | Out-Null
  Assert-Bench $instance
  $instance.Run(30000) | Out-Null
  Assert-Bench $instance
  exit
}
if ($Action -eq 'run') { $instance.Run(30000) | Out-Null; Assert-Bench $instance; exit }
if ($Action -eq 'status') { exit }
if ($ExpectedChecks -lt 1) { throw 'Expected assertion count is required for a result read' }
$details = [enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ETagListDetails'),'DB')
$instance.UpdateTagList($details,$false,('"'+$resultBlock+'"'))
$values = @{}
foreach ($tag in $instance.TagInfos) {
  if ($tag.Name -notmatch '\.(Done|Checks|Failures|FirstFailure)$') { continue }
  $key = $Matches[1]
  $native = $instance.Read($tag.Name)
  $values[$key] = $native."$($native.Type)"
}
if ($values.Count -ne 4) { throw 'Bench result interface incomplete' }
Emit 'results' $values
if (-not $values.Done -or $values.Failures -ne 0 -or $values.FirstFailure -ne 0 -or $values.Checks -ne $ExpectedChecks) { throw 'Native assertions failed' }
} finally {
  if ($instance) { $instance.Dispose() }
}
