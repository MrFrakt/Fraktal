<#
.SYNOPSIS
  Start the native Fraktal HMI against a TIA station over the direct s7web://
  link, with the CPU web login taken from a DPAPI-protected secret file.

.DESCRIPTION
  The HMI asks for the CPU web login itself (kept in memory only); this
  script is for unattended or repeated starts, where FRAKTAL_TIA_WEB_USER and
  FRAKTAL_TIA_WEB_PASSWORD take precedence (OPCUA_TRANSPORT "Direct native
  HMI"). It
  decrypts the secret for the current Windows user, sets both variables for
  this process and the HMI it starts only, and clears them when the HMI exits.
  The password never appears on a command line, in a log or in user/system
  environment settings. Enter the endpoint
  s7web://<cpu>?pin=<SHA-256> in the HMI connection wizard (saved afterwards).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File Start-TiaHmiDirect.ps1
  powershell -ExecutionPolicy Bypass -File Start-TiaHmiDirect.ps1 -Exe C:\HMI\fraktal_hmi.exe
#>
param(
  [string] $SecretFile = (Join-Path $env:LOCALAPPDATA 'Fraktal\TiaStations\FrkS12.web.secret'),
  [string] $User = 'fraktal',
  # A built fraktal_hmi.exe; empty runs `flutter run -d windows` from the HMI source tree.
  [string] $Exe = ''
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $SecretFile)) { throw "Secret file not found: $SecretFile" }
$secure = ConvertTo-SecureString ([IO.File]::ReadAllText($SecretFile).Trim())
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $env:FRAKTAL_TIA_WEB_USER = $User
  $env:FRAKTAL_TIA_WEB_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
  if ($Exe) {
    & $Exe
  } else {
    $flutter = (Get-Command flutter -ErrorAction SilentlyContinue).Source
    if (-not $flutter) { throw 'flutter is not on PATH; pass -Exe with a built fraktal_hmi.exe' }
    Push-Location (Join-Path $PSScriptRoot '..\..\..\HMI')
    try { & $flutter run -d windows } finally { Pop-Location }
  }
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
  Remove-Item Env:\FRAKTAL_TIA_WEB_PASSWORD -ErrorAction SilentlyContinue
  Remove-Item Env:\FRAKTAL_TIA_WEB_USER -ErrorAction SilentlyContinue
}
