param(
  # The PLC OPC UA endpoint the gateway connects to. When bound, the value is
  # written into gateway.args as the line immediately after `--plc-endpoint`
  # (the documented one-option/value-per-line contract). When omitted, the
  # example default is left in place so a standalone run stays self-documenting.
  [string]$Endpoint,
  # Set by the combined wizard: suppress interactive follow-ups (Notepad) that
  # would block the caller waiting on this script's process tree.
  [switch]$Unattended
)

$ErrorActionPreference = 'Stop'

$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Fraktal Gateway'
$dataRoot = Join-Path $env:LOCALAPPDATA 'Fraktal\Gateway'
$programsRoot = Join-Path ([Environment]::GetFolderPath('Programs')) 'Fraktal Gateway'
$startupRoot = [Environment]::GetFolderPath('Startup')

$existingTray = Join-Path $installRoot 'fraktal_gateway_tray.exe'
if (Test-Path -LiteralPath $existingTray) {
  Start-Process -FilePath $existingTray -ArgumentList '--stop' -Wait -WindowStyle Hidden
  Start-Sleep -Milliseconds 500
}
Get-Process -Name 'fraktal_gateway_tray' -ErrorAction SilentlyContinue |
  Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name 'fraktal_gateway' -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -like "$installRoot*" } |
  Stop-Process -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force -Path $installRoot, $dataRoot, (Join-Path $dataRoot 'logs'), $programsRoot | Out-Null

$payload = @(
  'fraktal_gateway.exe',
  'fraktal_gateway_tray.exe',
  'fraktal_opcua.dll',
  'DEPLOYMENT.md',
  'WEB_HMI_GATEWAY_DEPLOYMENT.md',
  'gateway.args.example',
  'uninstall_gateway.ps1'
)
foreach ($name in $payload) {
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $installRoot $name) -Force
}

# fraktal_ads.dll is optional (present only when the gateway was built with the
# TwinCAT ADS SDK). When bundled, install it beside the gateway exe so an ads://
# --plc-endpoint works; its absence leaves opc.tcp:// fully functional.
$adsDll = Join-Path $PSScriptRoot 'fraktal_ads.dll'
if (Test-Path -LiteralPath $adsDll) {
  Copy-Item -LiteralPath $adsDll -Destination (Join-Path $installRoot 'fraktal_ads.dll') -Force
}

$webArchive = Join-Path $PSScriptRoot 'web_hmi.zip'
$webNext = Join-Path $installRoot 'web.next'
$webRoot = Join-Path $installRoot 'web'
if (Test-Path -LiteralPath $webNext) {
  Remove-Item -LiteralPath $webNext -Recurse -Force
}
Expand-Archive -LiteralPath $webArchive -DestinationPath $webNext -Force
if (-not (Test-Path -LiteralPath (Join-Path $webNext 'index.html'))) {
  throw 'The packaged Web HMI is missing index.html.'
}
if (Test-Path -LiteralPath $webRoot) {
  Remove-Item -LiteralPath $webRoot -Recurse -Force
}
Move-Item -LiteralPath $webNext -Destination $webRoot

$configPath = Join-Path $dataRoot 'gateway.args'
if (-not (Test-Path -LiteralPath $configPath)) {
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'gateway.args.example') -Destination $configPath
} elseif (-not (Select-String -LiteralPath $configPath -Pattern '^--web-root\s*$' -Quiet)) {
  Add-Content -LiteralPath $configPath -Value "`r`n# Web HMI installed with the gateway`r`n--web-root`r`n$webRoot"
}

# Line-aware --plc-endpoint injection: find the `--plc-endpoint` line and
# overwrite the value on the following line. Never regex-replace the literal
# default URI — it is fragile if the example ever changes. A missing option line
# is appended so the configured endpoint always takes effect.
if ($Endpoint) {
  $lines = Get-Content -LiteralPath $configPath
  $idx = -1
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^\s*--plc-endpoint\s*$') { $idx = $i; break }
  }
  if ($idx -ge 0 -and $idx + 1 -lt $lines.Count) {
    $lines[$idx + 1] = $Endpoint
    Set-Content -LiteralPath $configPath -Value $lines -Encoding ASCII
  } else {
    Add-Content -LiteralPath $configPath -Value "`r`n--plc-endpoint`r`n$Endpoint"
  }
}

$shell = New-Object -ComObject WScript.Shell
function Set-Shortcut([string]$Path, [string]$Target, [string]$WorkingDirectory) {
  $shortcut = $shell.CreateShortcut($Path)
  $shortcut.TargetPath = $Target
  $shortcut.WorkingDirectory = $WorkingDirectory
  $shortcut.Description = 'Fraktal OPC UA WebSocket Gateway'
  $shortcut.Save()
}

$trayExe = Join-Path $installRoot 'fraktal_gateway_tray.exe'
Set-Shortcut -Path (Join-Path $startupRoot 'Fraktal Gateway.lnk') -Target $trayExe -WorkingDirectory $installRoot
Set-Shortcut -Path (Join-Path $programsRoot 'Fraktal Gateway.lnk') -Target $trayExe -WorkingDirectory $installRoot
Set-Shortcut -Path (Join-Path $programsRoot 'Edit Gateway Configuration.lnk') -Target 'notepad.exe' -WorkingDirectory $dataRoot
$editShortcut = $shell.CreateShortcut((Join-Path $programsRoot 'Edit Gateway Configuration.lnk'))
$editShortcut.TargetPath = "$env:SystemRoot\System32\notepad.exe"
$editShortcut.Arguments = '"' + $configPath + '"'
$editShortcut.WorkingDirectory = $dataRoot
$editShortcut.Save()

$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\FraktalGateway'
New-Item -Path $uninstallKey -Force | Out-Null
Set-ItemProperty -Path $uninstallKey -Name DisplayName -Value 'Fraktal Gateway'
Set-ItemProperty -Path $uninstallKey -Name DisplayVersion -Value '0.1.0'
Set-ItemProperty -Path $uninstallKey -Name Publisher -Value 'Fraktal'
Set-ItemProperty -Path $uninstallKey -Name InstallLocation -Value $installRoot
Set-ItemProperty -Path $uninstallKey -Name DisplayIcon -Value $trayExe
New-ItemProperty -Path $uninstallKey -Name NoModify -PropertyType DWord -Value 1 -Force | Out-Null
New-ItemProperty -Path $uninstallKey -Name NoRepair -PropertyType DWord -Value 1 -Force | Out-Null
$uninstallScript = Join-Path $installRoot 'uninstall_gateway.ps1'
$uninstallCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $uninstallScript + '"'
Set-ItemProperty -Path $uninstallKey -Name UninstallString -Value $uninstallCommand

Start-Process -FilePath $trayExe -WorkingDirectory $installRoot
# Only pop Notepad for a direct/standalone run. Under the combined wizard the
# child process tree is waited on, so opening an interactive editor here makes
# the wizard appear hung (its Close button cannot run until this returns).
if (-not $Unattended) {
  Start-Process -FilePath 'notepad.exe' -ArgumentList ('"' + $configPath + '"')
}
