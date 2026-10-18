$ErrorActionPreference='Stop'
$asm=[Reflection.Assembly]::LoadFrom('C:/Program Files (x86)/Common Files/Siemens/PLCSIMADV/API/7.0/Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$m=$asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
$cpu=$m.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@('FraktalBench'))
if ($cpu.Name -cne 'FraktalBench' -or '192.168.0.20' -notin @($cpu.ControllerIP)) { throw 'Wrong bench target' }
$d=[enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ETagListDetails'),'DB');$cpu.UpdateTagList($d,$false,'"GDB_PressIoBridgeClient"')
$p='GDB_PressIoBridgeClient.Endpoint.'
$path=Join-Path $PSScriptRoot 'link_stability01.jsonl'
$stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);$writer=[IO.StreamWriter]::new($stream,[Text.UTF8Encoding]::new($false))
$rows=@()
try {
 for ($slot=0;$slot -lt 150;$slot++) {
  $row=[ordered]@{utc=[datetime]::UtcNow.ToString('o');slot=$slot;healthy=$cpu.ReadBool($p+'LinkHealthy');accepted=$cpu.ReadUInt32($p+'Protocol.AcceptedFrames');rejected=$cpu.ReadUInt32($p+'Protocol.RejectedFrames');send=$cpu.ReadUInt16($p+'SendStatus');receive=$cpu.ReadUInt16($p+'ReceiveStatus');echo=$cpu.ReadBool($p+'Protocol.EchoGood');sendReset=$cpu.ReadBool($p+'SendReset');receiveReset=$cpu.ReadBool($p+'ReceiveReset')}
  $rows+=,$row;$writer.WriteLine(($row | ConvertTo-Json -Compress));$writer.Flush();Start-Sleep -Milliseconds 200
 }
} finally { $writer.Dispose() }
$bad=@($rows | Where-Object { -not $_.healthy }).Count
[ordered]@{samples=$rows.Count;unhealthy=$bad;firstAccepted=$rows[0].accepted;lastAccepted=$rows[-1].accepted;rejected=$rows[-1].rejected} | ConvertTo-Json -Compress
if ($bad -or $rows[-1].accepted -le $rows[0].accepted -or $rows[-1].rejected) { exit 1 }
