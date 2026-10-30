$ErrorActionPreference='Stop'
$work=Split-Path -Parent $MyInvocation.MyCommand.Path
$script:cpuProbeIteration=0
function Get-Counter {
  [CmdletBinding()]
  param($Counter,$SampleInterval,$MaxSamples)
  $script:cpuProbeIteration++
  if ($script:cpuProbeIteration -eq 1) {Write-Error 'Injected disappearing-process sample'}
  if ($script:cpuProbeIteration -eq 3) {[IO.File]::WriteAllText((Join-Path $work 'cpu_churn_stop_02.json'),'{}')}
  [pscustomobject]@{CounterSamples=@(
    [pscustomobject]@{Path='\processor(_total)\% Processor Time';InstanceName='_total';Status=0;CookedValue=42.0},
    [pscustomobject]@{Path='\process(emulatecontrollogix5580)\% Processor Time';InstanceName='emulatecontrollogix5580';Status=0;CookedValue=20.0},
    [pscustomobject]@{Path='\process(disappeared)\% Processor Time';InstanceName='disappeared';Status=2147485649;CookedValue=[double]::NaN}
  )}
}
& (Join-Path $work 'host_cpu_monitor.ps1') -OutFile (Join-Path $work 'cpu_churn_02.csv') -ReadyFile (Join-Path $work 'cpu_churn_ready_02.json') -StopFile (Join-Path $work 'cpu_churn_stop_02.json')
$rows=Import-Csv -LiteralPath (Join-Path $work 'cpu_churn_02.csv')
if (($rows | Where-Object kind -eq host).Count -ne 3 -or ($rows | Where-Object kind -eq process).Count -ne 3 -or ($rows | Where-Object kind -eq invalid).Count -ne 3) {throw 'Sampler dropped valid host/process data on invalid samples'}
Write-Output 'PASS: disappearing process samples retained; host and emulator sampling continued'
