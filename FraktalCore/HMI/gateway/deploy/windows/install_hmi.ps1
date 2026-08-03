param(
  # The PLC endpoint the HMI connects to (e.g. ads://192.168.1.6.1.1:854 on a
  # TwinCAT host, or opc.tcp://plc:4840 elsewhere). Written into the HMI's
  # connection.json on first install only — never clobbering a completed setup.
  [Parameter(Mandatory = $true)][string]$Endpoint,
  # Accepted for symmetry with install_gateway.ps1 so the combined wizard can
  # pass the same switch to every component. This script starts nothing
  # interactive, so there is no behaviour to suppress.
  [switch]$Unattended
)

$ErrorActionPreference = 'Stop'

$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Fraktal HMI'
$programsRoot = Join-Path ([Environment]::GetFolderPath('Programs')) 'Fraktal HMI'
$appDataRoot = Join-Path $env:APPDATA 'Fraktal\HMI'

# Stop a previously installed HMI so its files can be replaced.
Get-Process -Name 'fraktal_hmi' -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -like "$installRoot*" } |
  Stop-Process -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force -Path $installRoot, $programsRoot, $appDataRoot | Out-Null

# Extract the packaged app into a sibling staging dir, verify the executable,
# then swap it into place (mirrors the gateway's web.next atomic-ish swap).
$archive = Join-Path $PSScriptRoot 'hmi_app.zip'
$nextDir = Join-Path $installRoot '..\fraktal_hmi.next'
if (Test-Path -LiteralPath $nextDir) { Remove-Item -LiteralPath $nextDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $nextDir | Out-Null
Write-Output 'step: expanding HMI app bundle'
Expand-Archive -LiteralPath $archive -DestinationPath $nextDir -Force
if (-not (Test-Path -LiteralPath (Join-Path $nextDir 'fraktal_hmi.exe'))) {
  throw 'The packaged HMI app is missing fraktal_hmi.exe.'
}
if (Test-Path -LiteralPath $installRoot) { Remove-Item -LiteralPath $installRoot -Recurse -Force }
Move-Item -LiteralPath $nextDir -Destination $installRoot

# Drop Mark-of-the-Web blocks inherited from a downloaded installer so the
# engine and plugin DLLs load. No-op when the files were never blocked.
Get-ChildItem -LiteralPath $installRoot -Recurse -Include *.exe, *.dll |
  ForEach-Object { Unblock-File -LiteralPath $_.FullName -ErrorAction SilentlyContinue }

# Seed the HMI connection settings on first install only. A reinstall/upgrade
# keeps the operator's completed wizard config. The full v3 object is required:
# ConnectionSettings.fromJson returns null (and the app silently falls back to
# the default endpoint) if any field is missing or mistyped.
$settingsPath = Join-Path $appDataRoot 'connection.json'
if (-not (Test-Path -LiteralPath $settingsPath)) {
  $settings = [ordered]@{
    schemaVersion            = 3
    transport                = 'gateway'   # native direct path (ADS on Windows)
    endpoint                 = $Endpoint
    everConnected            = $false      # show the wizard, endpoint pre-filled
    selectedUnitPaths        = @()
    unitSelectionComplete    = $false
    enabledLanguageCodes     = @()
    activeLanguageCode       = 'en'
    languageSelectionComplete = $false
  }
  $json = $settings | ConvertTo-Json -Depth 5
  # No-BOM UTF-8: the HMI loader (jsonDecode(file.readAsString())) does not strip
  # a BOM, so Set-Content's default UTF8 (with BOM) would make fromJson return
  # null and silently fall back to the default endpoint.
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($settingsPath, $json, $utf8NoBom)
}

# Start Menu shortcut only — the HMI is an on-demand GUI, not a background tray.
Write-Output 'step: shortcut and uninstall entry'
$shell = New-Object -ComObject WScript.Shell
$hmiExe = Join-Path $installRoot 'fraktal_hmi.exe'
$shortcut = $shell.CreateShortcut((Join-Path $programsRoot 'Fraktal HMI.lnk'))
$shortcut.TargetPath = $hmiExe
$shortcut.WorkingDirectory = $installRoot
$shortcut.Description = 'Fraktal HMI'
$shortcut.Save()

# Self-uninstall capability + Add/Remove Programs entry (per-user, distinct key).
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'uninstall_hmi.ps1') -Destination (Join-Path $installRoot 'uninstall_hmi.ps1') -Force
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\FraktalHMI'
New-Item -Path $uninstallKey -Force | Out-Null
Set-ItemProperty -Path $uninstallKey -Name DisplayName -Value 'Fraktal HMI'
Set-ItemProperty -Path $uninstallKey -Name DisplayVersion -Value '0.1.0'
Set-ItemProperty -Path $uninstallKey -Name Publisher -Value 'Fraktal'
Set-ItemProperty -Path $uninstallKey -Name InstallLocation -Value $installRoot
Set-ItemProperty -Path $uninstallKey -Name DisplayIcon -Value $hmiExe
New-ItemProperty -Path $uninstallKey -Name NoModify -PropertyType DWord -Value 1 -Force | Out-Null
New-ItemProperty -Path $uninstallKey -Name NoRepair -PropertyType DWord -Value 1 -Force | Out-Null
$uninstallScript = Join-Path $installRoot 'uninstall_hmi.ps1'
$uninstallCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $uninstallScript + '"'
Set-ItemProperty -Path $uninstallKey -Name UninstallString -Value $uninstallCommand

Write-Output 'step: done'
