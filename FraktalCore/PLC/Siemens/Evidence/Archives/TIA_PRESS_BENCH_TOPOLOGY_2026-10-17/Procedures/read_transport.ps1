$ErrorActionPreference='Stop'
$asm=[Reflection.Assembly]::LoadFrom('C:/Program Files (x86)/Common Files/Siemens/PLCSIMADV/API/7.0/Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$manager=$asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
$instance=$manager.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@('FraktalBench'))
if ($instance.Name -cne 'FraktalBench' -or '192.168.0.20' -notin @($instance.ControllerIP) -or [string]$instance.CPUType -ne 'CPU1516') { throw 'Unexpected target' }
$details=[enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ETagListDetails'),'DB')
$instance.UpdateTagList($details,$false,'"GDB_PressIoBridgeClient"')
$count=0
foreach ($tag in $instance.TagInfos) {
  if ($tag.Name -notmatch '\.(SendStatus|ReceiveStatus|AcceptedFrames|RejectedFrames|Connected|PeerEnabled|PeerSignals|LinkHealthy)$') { continue }
  $value=$instance.Read($tag.Name)
  [ordered]@{event='transport-read';tag=$tag.Name;value=$value."$($value.Type)"} | ConvertTo-Json -Compress
  $count++
}
if (-not $count) { throw 'No transport status values read' }
