<# Read-only comparison of RUNTIME accumulation with the simulator's system clock. #>
param([double] $Minutes = 10, [double] $PeriodSeconds = 5)
$ErrorActionPreference = 'Stop'
$simAsm = [Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\5.0\Siemens.Simatic.Simulation.Runtime.Api.x64.dll')
$simManager = $simAsm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')
$simInstance = $simManager.GetMethod('CreateInterface',[type[]]@([string])).Invoke($null,@('FrkS12'))
if ("$($simInstance.CPUType)" -ne 'CPU1516' -or "$($simInstance.CommunicationInterface)" -ne 'TCPIP' -or
    '169.254.212.49' -notin @($simInstance.ControllerIP)) { throw 'S12 observation target differs' }
foreach ($interfaceId in 0,1,2) {
  if ($simInstance.GetNetInterfaceMapping($interfaceId) -ne 0) { throw 'Physical mapping is present' }
}
$tagDetails = [enum]::Parse($simAsm.GetType('Siemens.Simatic.Simulation.Runtime.ETagListDetails'),'DB')
$simInstance.UpdateTagList($tagDetails,$false,'"S12Probe"')
$observerWatch = [Diagnostics.Stopwatch]::StartNew()
$initialVirtual = $null
$initialMono = 0.0
$lastScans = 0
$valid = $true
while ($true) {
  if ("$($simInstance.OperatingState)" -ne 'Run') { throw 'S12 left RUN' }
  $beforeSeconds = $observerWatch.Elapsed.TotalSeconds
  $virtualStamp = $simInstance.SystemTime
  $monoValue = $simInstance.Read('S12Probe.MonoSec')
  $monoSeconds = $monoValue."$($monoValue.Type)"
  $scanValue = $simInstance.Read('S12Probe.Scans')
  $scanCount = $scanValue."$($scanValue.Type)"
  $badValue = $simInstance.Read('S12Probe.BadDelta')
  $badCount = $badValue."$($badValue.Type)"
  $afterSeconds = $observerWatch.Elapsed.TotalSeconds
  if ($null -eq $initialVirtual) { $initialVirtual = $virtualStamp; $initialMono = $monoSeconds }
  $virtualElapsed = ($virtualStamp - $initialVirtual).TotalSeconds
  $monoElapsed = $monoSeconds - $initialMono
  if ($badCount -ne 0 -or ($lastScans -ne 0 -and $scanCount -le $lastScans) -or
      [math]::Abs($monoElapsed - $virtualElapsed) -gt 0.5) { $valid = $false }
  [ordered]@{t=[datetime]::UtcNow.ToString('o');event='virtual-clock';before=$beforeSeconds;after=$afterSeconds;
    virtualStamp=$virtualStamp.ToString('o');virtualElapsed=$virtualElapsed;plcElapsed=$monoElapsed;
    differenceSeconds=$monoElapsed-$virtualElapsed;scans=$scanCount;badDelta=$badCount;
    scaleFactor=$simInstance.ScaleFactor} | ConvertTo-Json -Compress
  if ($beforeSeconds -ge $Minutes*60) { break }
  $lastScans = $scanCount
  Start-Sleep -Milliseconds ([int]($PeriodSeconds*1000))
}
[ordered]@{t=[datetime]::UtcNow.ToString('o');event='virtual-clock-summary';minimumHostSeconds=$Minutes*60;
  actualHostSeconds=$beforeSeconds;virtualElapsed=$virtualElapsed;plcElapsed=$monoElapsed;
  toleranceSeconds=0.5;passed=$valid;scope='Simulator system clock; not physical drift or UTC sync'} | ConvertTo-Json -Compress
if (-not $valid) { exit 1 }
