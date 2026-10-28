param(
  # Every port an instance's public origin listens on. One rule covers them all
  # because they are the same program, profile, and scope.
  [Parameter(Mandatory = $true)]
  [ValidateRange(1, 65535)]
  [int[]]$Port,
  [Parameter(Mandatory = $true)]
  [string]$ProgramPath
)

$ErrorActionPreference = 'Stop'
$ruleName = 'FraktalHmiHttpsProxy'
$displayName = 'Fraktal HMI HTTPS/WSS proxy (local subnet)'

if (-not (Test-Path -LiteralPath $ProgramPath)) {
  throw "The reverse-proxy executable is missing: $ProgramPath"
}

Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue |
  Remove-NetFirewallRule
New-NetFirewallRule `
  -Name $ruleName `
  -DisplayName $displayName `
  -Description 'Allows authenticated Fraktal Web HMI HTTPS/WSS access from the local subnet only.' `
  -Direction Inbound `
  -Action Allow `
  -Enabled True `
  -Profile Domain,Private `
  -Program $ProgramPath `
  -Protocol TCP `
  -LocalPort $Port `
  -RemoteAddress LocalSubnet | Out-Null
