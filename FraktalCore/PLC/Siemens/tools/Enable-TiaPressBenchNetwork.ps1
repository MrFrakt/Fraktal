<# Apply the existing FraktalBench adapter mapping through Siemens' elevated vSwitch API.
   No CPU mode, program, storage, IP address or adapter mapping is changed here. #>
$ErrorActionPreference='Stop'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
if (-not [Security.Principal.WindowsPrincipal]::new($identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw 'Run this script from an elevated PowerShell: Siemens SetNetInterfaceBindings requires administrator rights.'
}
$asm=[Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\7.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$manager=$asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
$map=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../Examples/PressIoBridge/00_System/io.json') -Raw | ConvertFrom-Json
$adapter=@(Get-NetAdapter | Where-Object { $_.Name -ceq 'Ethernet1' -and $_.InterfaceDescription -ceq 'Intel(R) 82574L Gigabit Network Connection #2' -and $_.Status -eq 'Up' })
if ($adapter.Count -ne 1) { throw 'Expected enabled bench Ethernet1 adapter is absent' }
$ips=@(Get-NetIPAddress -InterfaceIndex $adapter[0].ifIndex -AddressFamily IPv4)
if ($ips.Count -ne 1 -or $ips[0].IPAddress -ne '192.168.0.123' -or $ips[0].PrefixLength -ne 24) { throw 'Bench adapter address/subnet differs' }
if ([string]$manager.GetProperty('NetworkMode').GetValue($null) -ne 'TCPIPMultipleAdapter') { throw 'Expected existing multiple-adapter mode; this script never changes it' }
function Snapshot {
  $rows=@()
  foreach ($info in $manager.GetProperty('RegisteredInstanceInfo').GetValue($null)) {
    if ($info.Name -cnotin @('Fraktal','FraktalBench')) { throw 'Additional simulation registration present; review its adapter needs first' }
    $cpu=$manager.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@($info.Name))
    $rows += [ordered]@{name=$cpu.Name;state=[string]$cpu.OperatingState;cpu=[string]$cpu.CPUType;comm=[string]$cpu.CommunicationInterface;addresses=@($cpu.ControllerIP);ie1=$cpu.GetNetInterfaceMapping(0);ie2=$cpu.GetNetInterfaceMapping(1);ie3=$cpu.GetNetInterfaceMapping(2);storage=$cpu.StoragePath}
  }
  return @($rows | Sort-Object { $_.name })
}
$before=@(Snapshot)
if ($before.Count -ne 2) { throw 'Both preserved original and prepared bench must be registered' }
foreach ($cpu in $before) {
  if ($cpu.state -ne 'Run' -or $cpu.cpu -ne 'CPU1516' -or $cpu.comm -ne 'TCPIP' -or $cpu.ie2 -ne 0 -or $cpu.ie3 -ne 0) { throw 'Simulation state/type/secondary mapping differs' }
  if ($cpu.name -ceq 'Fraktal') {
    if ($cpu.ie1 -ne 0 -or ($cpu.addresses | Sort-Object) -join ',' -ne '169.254.212.49,192.168.1.1') { throw 'Original Fraktal addresses/mapping differ' }
  } else {
    if ($cpu.ie1 -ne $adapter[0].ifIndex -or ($cpu.addresses | Sort-Object) -join ',' -ne ((@($map.simulator_bench_address,$map.simulator_engineering_address) | Sort-Object) -join ',')) { throw 'Prepared FraktalBench addresses/mapping differ' }
  }
}
$work=Join-Path $env:LOCALAPPDATA 'Fraktal/TiaSpikes/Press_Bench_20261017'
if (-not (Test-Path -LiteralPath $work -PathType Container)) { throw 'Prepared commissioning evidence directory is absent' }
$log=Join-Path $work ('network_bindings_'+[datetime]::UtcNow.ToString('yyyyMMdd_HHmmss_fff')+'.jsonl')
$stream=[IO.File]::Open($log,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
$writer=[IO.StreamWriter]::new($stream,[Text.UTF8Encoding]::new($false))
function Emit($event,$data) {
  $line=([ordered]@{utc=[datetime]::UtcNow.ToString('o');event=$event}+$data) | ConvertTo-Json -Compress -Depth 7
  $writer.WriteLine($line);$writer.Flush();Write-Output $line
}
try {
  Emit 'binding-preflight' @{mode='TCPIPMultipleAdapter';instances=$before;adapterIndex=$adapter[0].ifIndex;adapterName=$adapter[0].Name}
  # Siemens computes the bindings from the existing mappings in Multiple mode.
  # Call once; never replay an uncertain privileged operation.
  $manager.GetMethod('SetNetInterfaceBindings',[type[]]@()).Invoke($null,@()) | Out-Null
  $after=@(Snapshot)
  if (($before | ConvertTo-Json -Depth 6 -Compress) -cne ($after | ConvertTo-Json -Depth 6 -Compress)) { throw 'Instance identity/state changed during the binding operation' }
  $bindings=@($manager.GetProperty('NetInterfaces').GetValue($null) | ForEach-Object { @{index=$_.interfaceIndex;name=$_.interfaceName;enabled=$_.vSwitchBindingEnabled} })
  Emit 'bindings-applied' @{instances=$after;bindings=$bindings}
  Write-Output ('Recorded: '+$log)
} catch {
  Emit 'binding-failed' @{message=$_.Exception.Message}
  throw
} finally { $writer.Dispose() }
