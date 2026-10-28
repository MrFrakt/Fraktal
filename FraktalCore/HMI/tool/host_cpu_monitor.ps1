# Read-only host CPU sampler for S4b native sessions (canonical publication
# plan WP4b.3). Samples \Process(*)\% Processor Time once per second for the
# Echo emulator, the HMI, Python and Dart, from session start to stop, and
# appends one CSV line per sample. It reads performance counters only: no
# controller access, no process control.
#
#   powershell -File host_cpu_monitor.ps1 -OutFile <session>\host_cpu.csv
#
# Stop with Ctrl+C; the CSV is flushed line by line, so partial sessions keep
# their samples. Processor time is per-core-normalized (100% = one core).
param(
  [Parameter(Mandatory = $true)][string]$OutFile,
  [string[]]$ProcessNames = @(
    'FactoryTalk Logix Echo Service*', 'flutter_tester*', 'fraktal_hmi*',
    'dart*', 'python*', 'fraktal_gateway*')
)

$cores = [Environment]::ProcessorCount
'iso8601,process,cpuPercent' | Set-Content -Encoding utf8 $OutFile
Write-Host "Sampling every 1 s into $OutFile ($cores cores). Ctrl+C to stop."
while ($true) {
  $sample = Get-Counter '\Process(*)\% Processor Time' -SampleInterval 1 -ErrorAction SilentlyContinue
  $stamp = (Get-Date).ToUniversalTime().ToString('o')
  foreach ($counter in $sample.CounterSamples) {
    $instance = $counter.InstanceName
    $matched = $false
    foreach ($pattern in $ProcessNames) {
      if ($instance -like $pattern) { $matched = $true; break }
    }
    if (-not $matched -or $instance -in @ '_total', 'idle') { continue }
    $percent = [math]::Round($counter.CookedValue / $cores, 1)
    "$stamp,$instance,$percent" | Add-Content -Encoding utf8 $OutFile
  }
}
