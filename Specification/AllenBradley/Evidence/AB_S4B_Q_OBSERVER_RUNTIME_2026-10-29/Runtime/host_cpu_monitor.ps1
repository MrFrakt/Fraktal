# Read-only local CPU. Wildcard process counters can disappear during a sample.
param([Parameter(Mandatory=$true)][string]$OutFile,
      [Parameter(Mandatory=$true)][string]$ReadyFile,
      [Parameter(Mandatory=$true)][string]$StopFile)
$cores=[Environment]::ProcessorCount
$stream=[IO.File]::Open($OutFile,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
$writer=[IO.StreamWriter]::new($stream,[Text.UTF8Encoding]::new($false))
$writer.AutoFlush=$true
$writer.WriteLine('utc,kind,process,cpuPercent')
$ready=$false
$invalid=0
$counterErrors=0
$missingHost=0
try {
  while (-not (Test-Path -LiteralPath $StopFile)) {
    $sampleErrors=@()
    $sample=Get-Counter -Counter @('\Processor(_Total)\% Processor Time','\Process(*)\% Processor Time') -SampleInterval 1 -MaxSamples 1 -ErrorAction SilentlyContinue -ErrorVariable sampleErrors
    $counterErrors += $sampleErrors.Count
    $stamp=(Get-Date).ToUniversalTime().ToString('o')
    $hostSeen=$false
    foreach ($counter in $sample.CounterSamples) {
      $name=[string]$counter.InstanceName
      if ($counter.Status -ne 0 -or [double]::IsNaN($counter.CookedValue) -or [double]::IsInfinity($counter.CookedValue)) {
        $invalid++
        $writer.WriteLine(('{0},invalid,"{1}",' -f $stamp,$name.Replace('"','""')))
        continue
      }
      if ($counter.Path -like '*\processor(_total)\*') {
        $writer.WriteLine(('{0},host,_total,{1}' -f $stamp,[math]::Round($counter.CookedValue,2)))
        $hostSeen=$true
      } elseif ($name -match 'emulatecontrollogix|echo|fraktal_hmi|flutter_tester|dart|python|fraktal_gateway') {
        $writer.WriteLine(('{0},process,"{1}",{2}' -f $stamp,$name.Replace('"','""'),[math]::Round($counter.CookedValue/$cores,2)))
      }
    }
    if (-not $hostSeen) {
      $missingHost++
      $writer.WriteLine(('{0},missing,host,' -f $stamp))
      if ($missingHost -ge 10) {throw 'Ten consecutive CPU samples lack valid host data'}
    } else {
      $missingHost=0
      if (-not $ready) {
        $readyStream=[IO.File]::Open($ReadyFile,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
        $readyWriter=[IO.StreamWriter]::new($readyStream,[Text.UTF8Encoding]::new($false))
        try {$readyWriter.Write('{"ready":true,"readOnly":true}')} finally {$readyWriter.Dispose()}
        $ready=$true
      }
    }
  }
} finally {
  $writer.Dispose()
  @{readOnly=$true;ready=$ready;invalidSamples=$invalid;counterErrors=$counterErrors} | ConvertTo-Json -Compress
}
