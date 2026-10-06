$ErrorActionPreference = 'SilentlyContinue'

$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Fraktal HMI'
$programsRoot = Join-Path ([Environment]::GetFolderPath('Programs')) 'Fraktal HMI'

Get-Process -Name 'fraktal_hmi' |
  Where-Object { $_.Path -like "$installRoot*" } |
  Stop-Process -Force
Remove-Item -LiteralPath $programsRoot -Recurse -Force
Remove-Item -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\FraktalHMI' -Recurse -Force

# Preserve %APPDATA%\Fraktal\HMI\connection.json: by uninstall time the operator
# has completed the wizard and configured units/languages. A technician may
# remove that data separately.
Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden -ArgumentList @(
  '-NoProfile',
  '-Command',
  "Start-Sleep -Milliseconds 500; Remove-Item -LiteralPath '$installRoot' -Recurse -Force"
)
