<# Bounded, peer-filtered Windows packet trace. No PLC writes or network-setting changes. #>
$ErrorActionPreference='Stop'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
if (-not [Security.Principal.WindowsPrincipal]::new($identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Windows Packet Monitor requires an elevated PowerShell.' }
$work=Join-Path $env:LOCALAPPDATA 'Fraktal/TiaSpikes/Press_Bench_20261017'
if (-not (Test-Path -LiteralPath $work -PathType Container)) { throw 'Commissioning work directory missing' }
& 'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools/Invoke-TiaPressBench.ps1' -Action status
$dir=Join-Path $work ('packet_trace_'+[datetime]::UtcNow.ToString('yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $dir | Out-Null
function Invoke-PacketMonitor([string[]]$Arguments,[string]$LogName) {
  $result=@(& PktMon.exe @Arguments 2>&1)
  $code=$LASTEXITCODE
  $result | Out-File -LiteralPath (Join-Path $dir $LogName) -Encoding utf8
  if ($code -ne 0) { throw ('Packet Monitor failed: '+($Arguments -join ' ')+'. See '+$dir) }
  return $result
}
$sessions=@(& logman.exe query -ets 2>&1)
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify existing ETW sessions' }
if ($sessions -match '(?i)\bPktMon\b') { throw 'Another Packet Monitor trace is running; left unchanged' }
Start-Service -Name PktMon
$filters=@(Invoke-PacketMonitor @('filter','list') 'filters_before.txt')
if (($filters -join "`n") -match '(?m)^\s*\d+\s+') { throw 'Existing Packet Monitor filters found; left unchanged' }
$ownFilters=$false;$started=$false
try {
  Invoke-PacketMonitor @('filter','add','FraktalBenchSend','-t','TCP','-i','192.168.0.10','192.168.0.20','-p','24001') 'filter_send.txt' | Out-Null
  $ownFilters=$true
  Invoke-PacketMonitor @('filter','add','FraktalBenchReturn','-t','TCP','-i','192.168.0.10','192.168.0.20','-p','24002') 'filter_return.txt' | Out-Null
  Invoke-PacketMonitor @('list','--json') 'components.json' | Out-Null
  $etl=Join-Path $dir 'bridge.etl'
  Invoke-PacketMonitor @('start','--capture','--comp','all','--pkt-size','128','--file-size','16','--file-name',$etl) 'start.txt' | Out-Null
  $started=$true
  Start-Sleep -Seconds 20
  Invoke-PacketMonitor @('counters') 'counters.txt' | Out-Null
} finally {
  if ($started) { Invoke-PacketMonitor @('stop') 'stop.txt' | Out-Null }
  if ($ownFilters) { Invoke-PacketMonitor @('filter','remove') 'filters_removed.txt' | Out-Null }
}
Invoke-PacketMonitor @('etl2txt',$etl,'--out',(Join-Path $dir 'bridge.txt'),'--verbose','3','--metadata') 'convert.txt' | Out-Null
Get-NetConnectionProfile | Select-Object InterfaceAlias,NetworkCategory,IPv4Connectivity | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'profiles.json')
& 'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools/Invoke-TiaPressBench.ps1' -Action status | Out-File -LiteralPath (Join-Path $dir 'after.jsonl') -Encoding utf8
Write-Output ('Trace recorded: '+$dir)
