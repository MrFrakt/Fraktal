$ErrorActionPreference='Stop'
$work=$PSScriptRoot
$guard=Get-Content -LiteralPath (Join-Path $work 'bench_before_tcp_type.json') -Raw | ConvertFrom-Json
$physical=@(Get-Content -LiteralPath (Join-Path $work 'physical_before_tcp_type.jsonl') | ForEach-Object { $_ | ConvertFrom-Json })
if ($guard.'PressDemo.Busy' -or $guard.'PressDemo.ConfigPersist.Pending' -or $guard.'FRK_PersistStatus.Restoring') { throw 'Bench not quiescent' }
if (@($physical | Where-Object { $_.member -eq 'OutputsEnabled' -and $_.value -eq $false }).Count -ne 1) { throw 'Physical output-inhibit proof missing' }
if (((Get-Date).ToUniversalTime()-(Get-Item -LiteralPath (Join-Path $work 'bench_before_tcp_type.json')).LastWriteTimeUtc).TotalSeconds -gt 120) { throw 'Quiescence proof expired' }
$log=Join-Path $work 'tcp_type_diagnostic01.jsonl'
$stream=[IO.File]::Open($log,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
$writer=[IO.StreamWriter]::new($stream,[Text.UTF8Encoding]::new($false))
function Emit($event,$data) { $line=([ordered]@{utc=[datetime]::UtcNow.ToString('o');event=$event}+$data) | ConvertTo-Json -Compress; $writer.WriteLine($line);$writer.Flush();Write-Output $line }
$asm=[Reflection.Assembly]::LoadFrom('C:/Program Files (x86)/Common Files/Siemens/PLCSIMADV/API/7.0/Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$manager=$asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
$instance=$manager.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@('FraktalBench'))
if ($instance.Name -cne 'FraktalBench' -or [string]$instance.CPUType -ne 'CPU1516' -or [string]$instance.OperatingState -ne 'Run' -or (@($instance.ControllerIP | Sort-Object) -join ',') -ne '169.254.212.61,192.168.0.20' -or $instance.GetNetInterfaceMapping(0) -ne 9) { throw 'Bench identity differs' }
$details=[enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ETagListDetails'),'DB')
$instance.UpdateTagList($details,$false,'"GDB_PressIoBridgeClient"')
$prefix='GDB_PressIoBridgeClient.Endpoint.'
$field=$prefix+'ReceiveConnection.ConnectionType';$reset=$prefix+'ReceiveReset'
$changed=$false
try {
  if ($instance.ReadUInt8($field) -ne 17) { throw 'Unexpected initial TCP type' }
  Emit 'tcp-type-before' @{type=17;send=$instance.ReadUInt16($prefix+'SendStatus');receive=$instance.ReadUInt16($prefix+'ReceiveStatus')}
  $instance.WriteUInt8($field,[byte]11);$changed=$true
  $instance.WriteBool($reset,$true)
  for ($slot=0;$slot -lt 15;$slot++) {
    Start-Sleep -Seconds 1
    Emit 'tcp-type-sample' @{slot=$slot;type=$instance.ReadUInt8($field);send=$instance.ReadUInt16($prefix+'SendStatus');receive=$instance.ReadUInt16($prefix+'ReceiveStatus');healthy=$instance.ReadBool($prefix+'LinkHealthy');accepted=$instance.ReadUInt32($prefix+'Protocol.AcceptedFrames');rejected=$instance.ReadUInt32($prefix+'Protocol.RejectedFrames');reset=$instance.ReadBool($reset)}
  }
} finally {
  if ($changed) {
    $actual=$instance.ReadUInt8($field)
    if ($actual -ne 11) { throw 'Diagnostic field changed unexpectedly; inspect before restoring' }
    $instance.WriteUInt8($field,[byte]17)
    $instance.WriteBool($reset,$true)
    Emit 'tcp-type-restored' @{type=$instance.ReadUInt8($field)}
  }
  $writer.Dispose()
}
