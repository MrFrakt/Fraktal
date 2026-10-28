$ErrorActionPreference = 'SilentlyContinue'

$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Fraktal Gateway'
$programsRoot = Join-Path ([Environment]::GetFolderPath('Programs')) 'Fraktal Gateway'
$startupShortcut = Join-Path ([Environment]::GetFolderPath('Startup')) 'Fraktal Gateway.lnk'

$trayExe = Join-Path $installRoot 'fraktal_gateway_tray.exe'
if (Test-Path -LiteralPath $trayExe) {
  Start-Process -FilePath $trayExe -ArgumentList '--stop' -Wait -WindowStyle Hidden
  Start-Sleep -Milliseconds 500
}
Get-Process -Name 'fraktal_gateway_tray' | Stop-Process -Force
Get-Process -Name 'fraktal_gateway' |
  Where-Object { $_.Path -like "$installRoot*" } |
  Stop-Process -Force
Get-Process -Name 'caddy' |
  Where-Object { $_.Path -like "$installRoot*" } |
  Stop-Process -Force
Remove-Item -LiteralPath $startupShortcut -Force
Remove-Item -LiteralPath $programsRoot -Recurse -Force
Remove-Item -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\FraktalGateway' -Recurse -Force

# Preserve %LOCALAPPDATA%\Fraktal\Gateway: it contains the site configuration,
# PKI material, and logs. A technician may remove that data separately.
Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden -ArgumentList @(
  '-NoProfile',
  '-Command',
  "Start-Sleep -Milliseconds 500; Remove-Item -LiteralPath '$installRoot' -Recurse -Force"
)
