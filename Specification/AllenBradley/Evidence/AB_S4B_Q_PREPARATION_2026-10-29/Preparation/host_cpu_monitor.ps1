# Read-only local host/process CPU; no controller or process-control operations.
param([Parameter(Mandatory=$true)][string]$OutFile,
      [Parameter(Mandatory=$true)][string]$ReadyFile,
      [Parameter(Mandatory=$true)][string]$StopFile)
$cores=[Environment]::ProcessorCount
$stream=[IO.File]::Open($OutFile,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
$writer=[IO.StreamWriter]::new($stream,[Text.UTF8Encoding]::new($false))
$writer.AutoFlush=$true
$writer.WriteLine('utc,kind,process,cpuPercent')
$ready=$false
try {
  while (-not (Test-Path -LiteralPath $StopFile)) {
    $sample=Get-Counter -Counter @('\Processor(_Total)\% Processor Time','\Process(*)\% Processor Time') -SampleInterval 1 -MaxSamples 1 -ErrorAction Stop
    $stamp=(Get-Date).ToUniversalTime().ToString('o')
    foreach ($counter in $sample.CounterSamples) {
      $name=$counter.InstanceName
      if ($counter.Path -like '*\processor(_total)\*') {
        $writer.WriteLine(('{0},host,_total,{1}' -f $stamp,[math]::Round($counter.CookedValue,2)))
      } elseif ($name -match 'emulatecontrollogix|echo|fraktal_hmi|flutter_tester|dart|python|fraktal_gateway') {
        $writer.WriteLine(('{0},process,"{1}",{2}' -f $stamp,$name.Replace('"','""'),[math]::Round($counter.CookedValue/$cores,2)))
      }
    }
    if (-not $ready) {
      $readyStream=[IO.File]::Open($ReadyFile,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
      $readyWriter=[IO.StreamWriter]::new($readyStream,[Text.UTF8Encoding]::new($false))
      try {$readyWriter.Write('{"ready":true,"readOnly":true}')} finally {$readyWriter.Dispose()}
      $ready=$true
    }
  }
} finally {$writer.Dispose()}
