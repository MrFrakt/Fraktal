<# Persistent press bench on the physical I/O LAN. The saved Fraktal CPU is observation-only. #>
param(
  [ValidateSet('inspect','start','power-on','engineering-address','status','run')] [string] $Action = 'inspect',
  [string] $EvidenceDirectory = ''
)
$ErrorActionPreference = 'Stop'
$benchName = 'FraktalBench'
$mapping = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../Examples/PressIoBridge/00_System/io.json') -Raw | ConvertFrom-Json
$benchAddress = [string]$mapping.simulator_bench_address
$engineeringAddress = [string]$mapping.simulator_engineering_address
if ($benchAddress -ne '192.168.0.20' -or $mapping.physical_address -ne '192.168.0.10') { throw 'The commissioned bench endpoint pair requires explicit review before changing' }
if ($engineeringAddress -ne '169.254.212.61') { throw 'The reserved engineering address requires explicit review before changing' }
$asm = [Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\7.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$manager = $asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
function Emit($kind,$data) { ([ordered]@{utc=[datetime]::UtcNow.ToString('o');event=$kind}+$data) | ConvertTo-Json -Compress -Depth 6 }
function Find-Instance([string]$name) {
  foreach ($info in $manager.GetProperty('RegisteredInstanceInfo').GetValue($null)) {
    if ($info.Name -ceq $name) { return $manager.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@($name)) }
  }
  return $null
}
function Snapshot($instance) {
  if (-not $instance) { throw 'Required saved instance is absent' }
  return [ordered]@{name=$instance.Name;cpu=[string]$instance.CPUType;state=[string]$instance.OperatingState;comm=[string]$instance.CommunicationInterface;
    addresses=@($instance.ControllerIP);ie1=$instance.GetNetInterfaceMapping(0);ie2=$instance.GetNetInterfaceMapping(1);ie3=$instance.GetNetInterfaceMapping(2)}
}
function Assert-Original($instance) {
  $value=Snapshot $instance
  if ($value.name -cne 'Fraktal' -or $value.cpu -ne 'CPU1516' -or $value.state -ne 'Run' -or $value.comm -ne 'TCPIP' -or
      (@($value.addresses | Sort-Object) -join ',') -ne '169.254.212.49,192.168.1.1' -or $value.ie1 -ne 0 -or $value.ie2 -ne 0 -or $value.ie3 -ne 0) { throw 'Original Fraktal identity/state differs; no controller change allowed' }
  return $value
}
$original=Find-Instance 'Fraktal'
$before=Assert-Original $original
Emit 'preserved-original' $before
$adapter=@(Get-NetAdapter | Where-Object { $_.Name -ceq 'Ethernet1' -and $_.InterfaceDescription -ceq 'Intel(R) 82574L Gigabit Network Connection #2' -and $_.Status -eq 'Up' })
if ($adapter.Count -ne 1) { throw 'Expected physical bench Ethernet1 adapter is absent' }
$addresses=@(Get-NetIPAddress -InterfaceIndex $adapter[0].ifIndex -AddressFamily IPv4)
if ($addresses.Count -ne 1 -or $addresses[0].IPAddress -ne '192.168.0.123' -or $addresses[0].PrefixLength -ne 24) { throw 'Bench adapter subnet differs' }
$sdkAdapter=@($manager.GetProperty('NetInterfaces').GetValue($null) | Where-Object { $_.interfaceIndex -eq $adapter[0].ifIndex })
if ($sdkAdapter.Count -ne 1 -or -not $sdkAdapter[0].vSwitchBindingEnabled -or -not $sdkAdapter[0].isConnected) { throw 'Bench adapter needs its existing enabled PLCSIM Virtual Switch binding' }
Emit 'network' @{mode=[string]$manager.GetProperty('NetworkMode').GetValue($null);benchAddress=$benchAddress;physicalAddress=[string]$mapping.physical_address;adapterIndex=$adapter[0].ifIndex;adapterName=$adapter[0].Name;vSwitch=$true}
if ($Action -eq 'inspect') {
  foreach ($info in $manager.GetProperty('RegisteredInstanceInfo').GetValue($null)) { Emit 'registered-instance' (Snapshot (Find-Instance $info.Name)) }
  exit
}
$instance=Find-Instance $benchName
if ($Action -in @('start','power-on')) {
  if ($Action -eq 'start' -and $instance) { throw 'Bench already registered; use status/run and preserve its saved storage' }
  if ($Action -eq 'power-on' -and (-not $instance -or [string]$instance.OperatingState -ne 'Off')) { throw 'Power-on requires the existing bench in OFF' }
  if (-not $EvidenceDirectory -or -not (Test-Path -LiteralPath $EvidenceDirectory -PathType Container)) { throw 'Existing private evidence directory required' }
  $proofPath=Join-Path $EvidenceDirectory 'before_registration.json'
  if ($Action -eq 'start' -and (Test-Path -LiteralPath $proofPath)) { throw 'New append-only setup evidence directory required' }
  if ($Action -eq 'power-on') {
    if (-not (Test-Path -LiteralPath $proofPath -PathType Leaf)) { throw 'Power-on requires the saved bench creation proof' }
    $proof=Get-Content -LiteralPath $proofPath -Raw | ConvertFrom-Json
    if ($proof.benchName -cne $benchName -or $proof.benchAddress -ne $benchAddress -or $instance.Name -cne $benchName) { throw 'Saved creation proof differs from the selected bench' }
  }
  $infoBefore=@($manager.GetProperty('RegisteredInstanceInfo').GetValue($null))
  foreach ($info in $infoBefore) {
    $other=Find-Instance $info.Name
    if ($Action -eq 'power-on' -and $info.Name -ceq $benchName) { continue }
    foreach ($number in 0,1,2) { if ($other.GetNetInterfaceMapping($number) -eq $adapter[0].ifIndex) { throw 'Bench physical adapter is already assigned to another simulated interface' } }
    if ($benchAddress -in @($other.ControllerIP)) { throw 'Bench address is already assigned' }
  }
  $neighbor=@(Get-NetNeighbor -InterfaceIndex $adapter[0].ifIndex -AddressFamily IPv4 | Where-Object { $_.IPAddress -eq $benchAddress -and $_.State -notin @('Unreachable','Incomplete') })
  if ($neighbor.Count) { throw 'Bench address already has a reachable network neighbor' }
  $initialMode=[string]$manager.GetProperty('NetworkMode').GetValue($null)
  if ($Action -eq 'start') {
    [ordered]@{utc=[datetime]::UtcNow.ToString('o');original=$before;networkMode=$initialMode;adapterIndex=$adapter[0].ifIndex;benchName=$benchName;benchAddress=$benchAddress} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $proofPath -Encoding UTF8
  }
  # Single-adapter mode uses the already enabled physical vSwitch binding;
  # multiple-adapter mode uses an explicit per-instance interface assignment.
  # Changing the global mode requires stopping all CPUs. Preserve it instead.
  if ($initialMode -notin @('TCPIPSingleAdapter','TCPIPMultipleAdapter')) { throw 'Distributed TCP/IP mode must already be selected' }
  if ($Action -eq 'start') {
    $cpu=[enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ECPUType'),'CPU1516')
    $instance=$manager.GetMethod('RegisterInstance',[type[]]@($cpu.GetType(),[string])).Invoke($null,@($cpu,$benchName))
    Emit 'registered' @{name=$benchName;storage=$instance.StoragePath}
  } else { Emit 'resumed-owned-registration' @{name=$benchName;storage=$instance.StoragePath} }
  # API 7 derives this read-only property from the global network selection.
  if ([string]$instance.CommunicationInterface -ne 'TCPIP') { throw 'Bench communication is not TCP/IP' }
  $setInitialAddress=@($instance.ControllerIP).Count -eq 0
  if ($initialMode -eq 'TCPIPMultipleAdapter') {
    $instance.SetNetInterfaceMapping(0,[uint32]$adapter[0].ifIndex)
    $instance.SetNetInterfaceMapping(1,[uint32]0)
    $instance.SetNetInterfaceMapping(2,[uint32]0)
    $check=$instance.CheckNetInterfaceMapping()
    Emit 'mapping-check' @{result=[string]$check}
    if ([int]$check -ne 0) { throw 'PLCSIM refused the bench interface mapping' }
  } else {
    Emit 'existing-single-adapter-binding' @{adapterIndex=$adapter[0].ifIndex;adapterName=$adapter[0].Name}
  }
  $result=$instance.PowerOn(60000)
  Emit 'power-on' @{name=$benchName;result=[string]$result}
  $suite=[Activator]::CreateInstance($asm.GetType('Siemens.Simatic.Simulation.Runtime.SIPSuite4'))
  foreach ($pair in @(@('IPAddress',$benchAddress),@('SubnetMask','255.255.255.0'),@('DefaultGateway','0.0.0.0'))) {
    $part=[Activator]::CreateInstance($asm.GetType('Siemens.Simatic.Simulation.Runtime.SIP'));$part.IPString=$pair[1];$suite.($pair[0])=$part
  }
  if ($setInitialAddress) { $instance.SetIPSuite(0,$suite,$true) }
}
if (-not $instance) { throw 'Persistent bench is not registered' }
$bench=Snapshot $instance
$expectedMapping=0
if ([string]$manager.GetProperty('NetworkMode').GetValue($null) -eq 'TCPIPMultipleAdapter') { $expectedMapping=$adapter[0].ifIndex }
$allowedAddresses=@($benchAddress,$engineeringAddress)
if ($bench.state -eq 'Stop') { $allowedAddresses += '0.0.0.0' } # Blank CPU, before its first project download.
if ($bench.name -cne $benchName -or $bench.comm -ne 'TCPIP' -or $bench.ie1 -ne $expectedMapping -or $bench.ie2 -ne 0 -or $bench.ie3 -ne 0 -or
    $benchAddress -notin $bench.addresses -or @($bench.addresses | Where-Object { $_ -notin $allowedAddresses }).Count -gt 0 -or
    $bench.cpu -notin @('CPU1516','CPU1500_Unspecified')) { throw 'Bench identity/address/mapping differs' }
if ($Action -eq 'engineering-address') {
  if ($bench.state -ne 'Stop') { throw 'Set the initial engineering address only while the bench is in STOP' }
  foreach ($info in $manager.GetProperty('RegisteredInstanceInfo').GetValue($null)) {
    if ($info.Name -cne $benchName -and $engineeringAddress -in @((Find-Instance $info.Name).ControllerIP)) { throw 'Engineering address already belongs to another instance' }
  }
  $suite=[Activator]::CreateInstance($asm.GetType('Siemens.Simatic.Simulation.Runtime.SIPSuite4'))
  foreach ($pair in @(@('IPAddress',$engineeringAddress),@('SubnetMask','255.255.0.0'),@('DefaultGateway','0.0.0.0'))) {
    $part=[Activator]::CreateInstance($asm.GetType('Siemens.Simatic.Simulation.Runtime.SIP'));$part.IPString=$pair[1];$suite.($pair[0])=$part
  }
  $instance.SetIPSuite(1,$suite,$true)
  $bench=Snapshot $instance
}
if ($Action -eq 'run') {
  if ($bench.cpu -ne 'CPU1516' -or $bench.state -ne 'Stop') { throw 'RUN requires the downloaded CPU1516 bench in STOP' }
  $instance.Run(30000) | Out-Null
  $bench=Snapshot $instance
}
Emit 'bench' $bench
$after=Assert-Original $original
if (($before | ConvertTo-Json -Compress) -cne ($after | ConvertTo-Json -Compress)) { throw 'Original Fraktal observation changed' }
Emit 'preserved-original-after' $after
