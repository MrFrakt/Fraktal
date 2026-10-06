param(
  # One HTTPS site per gateway instance: a JSON document of
  # {Name, Port, PublicOrigin} entries, as written by install_gateway.ps1.
  # Each site terminates TLS for exactly one loopback gateway.
  [string]$SitesFile,
  # Single-site shorthand for a manual run against one gateway.
  [string]$PublicOrigin,
  [ValidateRange(1, 65535)]
  [int]$GatewayPort = 8080,
  [Parameter(Mandatory = $true)]
  [string]$Username,
  [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'Programs\Fraktal Gateway'),
  [string]$DataRoot = (Join-Path $env:LOCALAPPDATA 'Fraktal\Gateway'),
  [switch]$ConfigureFirewall,
  [switch]$Unattended
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'fraktal_instances.ps1')

function ConvertTo-CaddyPath([string]$Value) {
  return $Value.Replace('\', '/').Replace('"', '\"')
}

function ConvertFrom-SecureStringPlainText([Security.SecureString]$Value) {
  $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
  }
}

function Read-ProxyPassword([bool]$AllowPreserved) {
  $fromEnvironment = [Environment]::GetEnvironmentVariable(
    'FRAKTAL_PROXY_PASSWORD',
    [EnvironmentVariableTarget]::Process
  )
  if (-not [string]::IsNullOrEmpty($fromEnvironment)) {
    return $fromEnvironment
  }
  if ($AllowPreserved) { return '' }
  if ($Unattended) {
    throw 'FRAKTAL_PROXY_PASSWORD is required when secure remote access is configured unattended.'
  }
  $first = Read-Host 'Remote Web HMI password' -AsSecureString
  $second = Read-Host 'Confirm remote Web HMI password' -AsSecureString
  $firstText = ConvertFrom-SecureStringPlainText $first
  $secondText = ConvertFrom-SecureStringPlainText $second
  if ($firstText -cne $secondText) {
    throw 'The remote Web HMI passwords do not match.'
  }
  return $firstText
}

function Get-CaddyPasswordHash([string]$CaddyPath, [string]$Password) {
  $startInfo = New-Object System.Diagnostics.ProcessStartInfo
  $startInfo.FileName = $CaddyPath
  $startInfo.Arguments = 'hash-password --algorithm argon2id'
  $startInfo.UseShellExecute = $false
  $startInfo.CreateNoWindow = $true
  $startInfo.RedirectStandardInput = $true
  $startInfo.RedirectStandardOutput = $true
  $startInfo.RedirectStandardError = $true
  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = $startInfo
  if (-not $process.Start()) {
    throw 'Caddy password hashing could not be started.'
  }
  try {
    # Caddy's stdin scanner needs LF termination but removes only that LF.
    # PowerShell's default WriteLine emits CRLF, leaving CR in the password and
    # creating a valid hash that no browser login can satisfy.
    $process.StandardInput.Write($Password + [char]10)
    $process.StandardInput.Close()
    $output = $process.StandardOutput.ReadToEnd().Trim()
    $errorOutput = $process.StandardError.ReadToEnd().Trim()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($output)) {
      throw "Caddy password hashing failed: $errorOutput"
    }
    return $output
  } finally {
    $process.Dispose()
  }
}

# Passwords are intentionally unrecoverable, but the site set is not: adding a
# PLC on an upgrade has to rewrite the Caddyfile without asking for the account
# again. Only the account name and its Argon2id hash are kept, beside the
# generated Caddyfile that already contains them.
function Get-StoredProxyCredential([string]$Path, [string]$LegacyConfigPath) {
  if (Test-Path -LiteralPath $Path) {
    $stored = (Get-Content -LiteralPath $Path -Raw).Trim()
    $parts = $stored -split '\s+', 2
    if ($parts.Count -eq 2 -and $parts[1].StartsWith('$argon2id$')) {
      return [PSCustomObject]@{ Username = $parts[0]; Hash = $parts[1] }
    }
  }
  # An installation configured before the credential file existed keeps the
  # only copy inside its validated Caddyfile.
  if (Test-Path -LiteralPath $LegacyConfigPath) {
    foreach ($line in (Get-Content -LiteralPath $LegacyConfigPath)) {
      if ($line -match '^\s*(\S+)\s+(\$argon2id\$\S+)\s*$') {
        return [PSCustomObject]@{
          Username = $Matches[1]
          Hash = $Matches[2]
        }
      }
    }
  }
  return $null
}

function Invoke-CaddyValidation([string]$CaddyPath, [string]$ConfigPath) {
  $formatResult = Start-Process -FilePath $CaddyPath `
    -ArgumentList @('fmt', '--overwrite', "`"$ConfigPath`"") `
    -Wait -PassThru -WindowStyle Hidden
  if ($formatResult.ExitCode -ne 0) {
    throw "Caddy could not format the generated reverse-proxy configuration (exit $($formatResult.ExitCode))."
  }
  $result = Start-Process -FilePath $CaddyPath `
    -ArgumentList @('validate', '--config', "`"$ConfigPath`"", '--adapter', 'caddyfile') `
    -Wait -PassThru -WindowStyle Hidden
  if ($result.ExitCode -ne 0) {
    throw "Caddy rejected the generated reverse-proxy configuration (exit $($result.ExitCode))."
  }
}

function Set-ProxyFirewallRule([int[]]$Ports, [string]$ProgramPath) {
  $helper = Join-Path $PSScriptRoot 'configure_proxy_firewall.ps1'
  if (-not (Test-Path -LiteralPath $helper)) {
    throw "Windows Firewall helper is missing: $helper"
  }
  $escapedHelper = '"' + $helper.Replace('"', '""') + '"'
  $escapedProgram = '"' + $ProgramPath.Replace('"', '""') + '"'
  $arguments = '-NoProfile -ExecutionPolicy Bypass -File ' + $escapedHelper +
    ' -Port ' + ($Ports -join ',') + ' -ProgramPath ' + $escapedProgram
  $result = Start-Process -FilePath 'powershell.exe' -Verb RunAs `
    -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
  if ($result.ExitCode -ne 0) {
    throw "Windows Firewall configuration failed or was cancelled (exit $($result.ExitCode))."
  }
}

# ---- Sites -----------------------------------------------------------------
$sites = @()
if ($SitesFile) {
  foreach ($entry in (Read-FraktalInstancesFile $SitesFile)) {
    $sites += [PSCustomObject]@{
      Name = $entry.Name
      Origin = (Get-NormalizedHttpsOrigin $entry.PublicOrigin)
      Port = [int]$entry.Port
    }
  }
} elseif ($PublicOrigin) {
  $sites = @([PSCustomObject]@{
    Name = 'default'
    Origin = (Get-NormalizedHttpsOrigin $PublicOrigin)
    Port = $GatewayPort
  })
}
if ($sites.Count -eq 0) {
  throw 'Pass -SitesFile (one site per gateway instance) or -PublicOrigin.'
}
$distinctOrigins = @($sites | ForEach-Object { $_.Origin.ToLowerInvariant() } | Select-Object -Unique)
if ($distinctOrigins.Count -ne $sites.Count) {
  throw 'Two gateway instances share one public origin; give each its own host name or port.'
}
if ($Username -notmatch '^[A-Za-z0-9._-]{1,64}$') {
  throw 'The reverse-proxy username must contain 1-64 letters, digits, dots, underscores, or hyphens.'
}

$caddy = Join-Path $InstallRoot 'caddy.exe'
if (-not (Test-Path -LiteralPath $caddy)) {
  throw "The packaged reverse proxy is missing: $caddy"
}

$proxyRoot = Join-Path $DataRoot 'proxy'
$storageRoot = Join-Path $proxyRoot 'storage'
$logsRoot = Join-Path $DataRoot 'logs'
New-Item -ItemType Directory -Force -Path $proxyRoot, $storageRoot, $logsRoot | Out-Null
$configPath = Join-Path $proxyRoot 'Caddyfile'
$nextConfigPath = Join-Path $proxyRoot 'Caddyfile.next'
$credentialPath = Join-Path $proxyRoot 'basic-auth.txt'

# ---- Account ---------------------------------------------------------------
$stored = Get-StoredProxyCredential $credentialPath $configPath
$password = Read-ProxyPassword ($null -ne $stored -and $stored.Username -eq $Username)
if ([string]::IsNullOrEmpty($password)) {
  # Upgrade with the password fields left blank: keep the site account exactly
  # as it is and regenerate only the routing.
  $passwordHash = $stored.Hash
  Write-Output 'Preserving the existing remote Web HMI account.'
} else {
  if ($password.Length -lt 12) {
    throw 'The remote Web HMI password must contain at least 12 characters.'
  }
  $passwordHash = Get-CaddyPasswordHash -CaddyPath $caddy -Password $password
}
[Environment]::SetEnvironmentVariable(
  'FRAKTAL_PROXY_PASSWORD',
  $null,
  [EnvironmentVariableTarget]::Process
)
$password = $null

# ---- Caddyfile -------------------------------------------------------------
$storageCaddy = ConvertTo-CaddyPath $storageRoot
$accessLogCaddy = ConvertTo-CaddyPath (Join-Path $logsRoot 'proxy-access.log')
$blocks = New-Object System.Collections.Generic.List[string]
$blocks.Add(@"
{
	admin off
	persist_config off
	auto_https disable_redirects
	skip_install_trust
	storage file_system "$storageCaddy"
}
"@) | Out-Null

foreach ($site in $sites) {
  # One site per gateway instance. The Web HMI derives its WebSocket endpoint
  # from the page origin, so an instance needs a whole origin of its own — a
  # shared origin with per-instance paths would break that derivation.
  $blocks.Add(@"

$($site.Origin) {
	tls internal

	basic_auth argon2id {
		$Username $passwordHash
	}

	header {
		X-Content-Type-Options "nosniff"
		Referrer-Policy "no-referrer"
		Permissions-Policy "camera=(), microphone=(), geolocation=()"
	}

	reverse_proxy 127.0.0.1:$($site.Port) {
		health_uri /livez
		health_interval 10s
		health_timeout 2s
		lb_try_duration 5s
		stream_close_delay 5m
	}

	log {
		output file "$accessLogCaddy" {
			roll_size 10MiB
			roll_keep 5
			roll_keep_for 720h
		}
		format json
	}
}
"@) | Out-Null
}

Set-Content -LiteralPath $nextConfigPath -Value ($blocks -join "`r`n") -Encoding UTF8
try {
  Invoke-CaddyValidation -CaddyPath $caddy -ConfigPath $nextConfigPath
  Move-Item -LiteralPath $nextConfigPath -Destination $configPath -Force
} finally {
  if (Test-Path -LiteralPath $nextConfigPath) {
    Remove-Item -LiteralPath $nextConfigPath -Force
  }
}
Set-Content -LiteralPath $credentialPath -Value "$Username $passwordHash" -Encoding ASCII

# Superseded by each instance's own --allow-origin: with several sites there is
# no single "the" public origin, and a stale file would name only the first.
$legacyOriginPath = Join-Path $proxyRoot 'public-origin.txt'
if (Test-Path -LiteralPath $legacyOriginPath) {
  Remove-Item -LiteralPath $legacyOriginPath -Force
}

# Validation provisions the internal CA. Export only its public root certificate
# to a stable, obvious path; private CA material remains below proxy\storage.
$generatedRoot = Join-Path $storageRoot 'pki\authorities\local\root.crt'
$exportedRoot = Join-Path $proxyRoot 'FraktalGatewayRootCA.crt'
if (Test-Path -LiteralPath $generatedRoot) {
  Copy-Item -LiteralPath $generatedRoot -Destination $exportedRoot -Force
}

if ($ConfigureFirewall) {
  $ports = @(
    $sites | ForEach-Object { [System.Uri]::new($_.Origin).Port } | Select-Object -Unique
  )
  Set-ProxyFirewallRule -Ports $ports -ProgramPath $caddy
}

foreach ($site in $sites) {
  Write-Output "Secure remote Web HMI configured at $($site.Origin) -> instance $($site.Name) (127.0.0.1:$($site.Port))"
}
Write-Output "Gateway root CA exported for client-device import: $exportedRoot"
