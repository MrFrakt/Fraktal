param([ValidateSet('Off','On')][string]$Action)
$ErrorActionPreference='Stop'
$asm=[Reflection.Assembly]::LoadFrom('C:/Program Files (x86)/Common Files/Siemens/PLCSIMADV/API/7.0/Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$m=$asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
function Cpu([string]$name) { $m.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@($name)) }
function View($cpu) { [ordered]@{name=$cpu.Name;state=[string]$cpu.OperatingState;cpu=[string]$cpu.CPUType;addresses=@($cpu.ControllerIP);ie1=$cpu.GetNetInterfaceMapping(0);ie2=$cpu.GetNetInterfaceMapping(1);ie3=$cpu.GetNetInterfaceMapping(2);storage=$cpu.StoragePath} }
$o=Cpu 'Fraktal';$b=Cpu 'FraktalBench';$original=View $o;$before=View $b
if ($original.name -cne 'Fraktal' -or $original.state -ne 'Run' -or $original.cpu -ne 'CPU1516' -or ($original.addresses | Sort-Object) -join ',' -ne '169.254.212.49,192.168.1.1' -or $original.ie1 -ne 0 -or $original.ie2 -ne 0 -or $original.ie3 -ne 0) { throw 'Original guard failed' }
if ($before.cpu -ne 'CPU1516' -or ($before.addresses | Sort-Object) -join ',' -ne '169.254.212.61,192.168.0.20' -or $before.ie1 -ne 9 -or $before.ie2 -ne 0 -or $before.ie3 -ne 0 -or -not $before.storage.EndsWith('\FraktalBench')) { throw 'Bench identity differs' }
if ($Action -eq 'Off') {
 if ($before.state -ne 'Run') { throw 'Bench must start RUN' }
 $q=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'bench_before_link_loss.json') -Raw | ConvertFrom-Json
 if ($q.'PressDemo.Busy' -or $q.'PressDemo.ConfigPersist.Pending' -or $q.'FRK_PersistStatus.Restoring') { throw 'Bench not quiescent' }
 if (((Get-Date).ToUniversalTime()-(Get-Item -LiteralPath (Join-Path $PSScriptRoot 'bench_before_link_loss.json')).LastWriteTimeUtc).TotalSeconds -gt 120) { throw 'Fresh quiescence proof required' }
 $b.PowerOff(30000) | Out-Null
} else {
 if ($before.state -ne 'Off') { throw 'Bench must start OFF' }
 $b.PowerOn(60000) | Out-Null
 if ([string]$b.OperatingState -eq 'Stop') { $b.Run(30000) | Out-Null }
}
$after=View $b;$originalAfter=View $o
if (($original | ConvertTo-Json -Compress) -cne ($originalAfter | ConvertTo-Json -Compress)) { throw 'Original changed' }
[ordered]@{utc=[datetime]::UtcNow.ToString('o');event='bench-power';action=$Action;before=$before;after=$after;original=$originalAfter} | ConvertTo-Json -Compress -Depth 6
