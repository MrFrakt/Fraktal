<#
.SYNOPSIS
    One-time engineering-workstation setup for TIA Portal Openness (Part IV §5.4).

.DESCRIPTION
    TIA Portal refuses every Openness session whose Windows account is not a
    member of the local group "Siemens TIA Openness" (EngineeringSecurityException).
    This script adds the account to that group and, optionally, whitelists the
    built Fraktal.Tia.Cli.exe in the Openness firewall so that ATTACHING to a
    running TIA Portal does not raise the interactive prompt. Starting a new,
    headless TIA instance (the default CLI mode) needs only the group membership.

    Run in an ELEVATED PowerShell. Group membership takes effect at the next
    logon: sign out and back in (or reboot) afterwards.

    Each change is printed; nothing is changed when it is already in place.

.PARAMETER User
    Account to add. Default: the current user.

.PARAMETER WhitelistExe
    Optional path to Fraktal.Tia.Cli.exe. Its SHA-256 and timestamp are written
    to HKLM\SOFTWARE\Siemens\Automation\Openness\20.0\Whitelist (Siemens' documented
    format). Re-run after every rebuild: the whitelist is bound to the file hash.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\Enable-TiaOpenness.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\Enable-TiaOpenness.ps1 `
        -WhitelistExe C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\TiaCli\bin\Release\net48\Fraktal.Tia.Cli.exe
    (the exe is what `dotnet build TiaCli.csproj -c Release` produces)
#>
[CmdletBinding()]
param(
    [string]$User = "$env:USERDOMAIN\$env:USERNAME",
    [string]$WhitelistExe
)

$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated (Administrator) PowerShell."
}

$group = 'Siemens TIA Openness'
if (-not (Get-LocalGroup -Name $group -ErrorAction SilentlyContinue)) {
    throw "Local group '$group' not found: TIA Portal Openness is not installed."
}
$shortName = $User.Split('\')[-1]
$isMember = Get-LocalGroupMember -Group $group | Where-Object { $_.Name.Split('\')[-1] -ieq $shortName }
if ($isMember) {
    Write-Host "[=] $User is already a member of '$group'."
} else {
    Add-LocalGroupMember -Group $group -Member $User
    Write-Host "[+] Added $User to '$group'. Sign out and back in for it to take effect."
}

if ($WhitelistExe) {
    $file = Get-Item -LiteralPath $WhitelistExe
    $sha = [Security.Cryptography.SHA256]::Create()
    $stream = $file.OpenRead()
    try { $hash = [Convert]::ToBase64String($sha.ComputeHash($stream)) } finally { $stream.Dispose() }
    $stamp = $file.LastWriteTimeUtc.ToString('yyyy/MM/dd HH:mm:ss.fff', [Globalization.CultureInfo]::InvariantCulture)
    $key = "HKLM:\SOFTWARE\Siemens\Automation\Openness\20.0\Whitelist\$($file.Name)\Entry"
    New-Item -Path $key -Force | Out-Null
    Set-ItemProperty -Path $key -Name Path -Value $file.FullName
    Set-ItemProperty -Path $key -Name DateModified -Value $stamp
    Set-ItemProperty -Path $key -Name FileHash -Value $hash
    Write-Host "[+] Whitelisted $($file.FullName) (SHA-256 $hash, $stamp UTC)."
}
