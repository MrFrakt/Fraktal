param(
  [Parameter(Mandatory = $true)]
  [string]$PublicOrigin,
  [Parameter(Mandatory = $true)]
  [string]$Username,
  [ValidateRange(1, 65535)]
  [int]$GatewayPort = 8080,
  [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'Programs\Fraktal Gateway'),
  [string]$DataRoot = (Join-Path $env:LOCALAPPDATA 'Fraktal\Gateway'),
  [switch]$ConfigureFirewall,
  [switch]$Unattended
)

$ErrorActionPreference = 'Stop'

function Get-NormalizedHttpsOrigin([string]$Value) {
  if ([string]::IsNullOrWhiteSpace($Value)) {
    throw 'The public Web HMI origin is required.'
  }
  try {
    $uri = [System.Uri]::new($Value.Trim())
  } catch {
    throw "Invalid public Web HMI origin: $Value"
  }
  if (-not $uri.IsAbsoluteUri -or
      $uri.Scheme -ne 'https' -or
      [string]::IsNullOrWhiteSpace($uri.Host) -or
      -not [string]::IsNullOrEmpty($uri.UserInfo) -or
      ($uri.AbsolutePath -ne '/' -and $uri.AbsolutePath -ne '') -or
      -not [string]::IsNullOrEmpty($uri.Query) -or
      -not [string]::IsNullOrEmpty($uri.Fragment)) {
    throw 'The public Web HMI origin must be only https://<host>[:port], with no path, credentials, query, or fragment.'
  }
  return $uri.GetComponents(
    [System.UriComponents]::SchemeAndServer,
    [System.UriFormat]::UriEscaped
  ).TrimEnd('/')
}

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

function Read-ProxyPassword {
  $fromEnvironment = [Environment]::GetEnvironmentVariable(
    'FRAKTAL_PROXY_PASSWORD',
    [EnvironmentVariableTarget]::Process
  )
  if (-not [string]::IsNullOrEmpty($fromEnvironment)) {
    return $fromEnvironment
  }
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

function Set-ProxyFirewallRule([int]$Port, [string]$ProgramPath) {
  $helper = Join-Path $PSScriptRoot 'configure_proxy_firewall.ps1'
  if (-not (Test-Path -LiteralPath $helper)) {
    throw "Windows Firewall helper is missing: $helper"
  }
  $escapedHelper = '"' + $helper.Replace('"', '""') + '"'
  $escapedProgram = '"' + $ProgramPath.Replace('"', '""') + '"'
  $arguments = '-NoProfile -ExecutionPolicy Bypass -File ' + $escapedHelper +
    ' -Port ' + $Port + ' -ProgramPath ' + $escapedProgram
  $result = Start-Process -FilePath 'powershell.exe' -Verb RunAs `
    -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
  if ($result.ExitCode -ne 0) {
    throw "Windows Firewall configuration failed or was cancelled (exit $($result.ExitCode))."
  }
}

$origin = Get-NormalizedHttpsOrigin $PublicOrigin
if ($Username -notmatch '^[A-Za-z0-9._-]{1,64}$') {
  throw 'The reverse-proxy username must contain 1-64 letters, digits, dots, underscores, or hyphens.'
}

$caddy = Join-Path $InstallRoot 'caddy.exe'
if (-not (Test-Path -LiteralPath $caddy)) {
  throw "The packaged reverse proxy is missing: $caddy"
}

$password = Read-ProxyPassword
if ($password.Length -lt 12) {
  throw 'The remote Web HMI password must contain at least 12 characters.'
}
[Environment]::SetEnvironmentVariable(
  'FRAKTAL_PROXY_PASSWORD',
  $null,
  [EnvironmentVariableTarget]::Process
)
$passwordHash = Get-CaddyPasswordHash -CaddyPath $caddy -Password $password
$password = $null

$proxyRoot = Join-Path $DataRoot 'proxy'
$storageRoot = Join-Path $proxyRoot 'storage'
$logsRoot = Join-Path $DataRoot 'logs'
New-Item -ItemType Directory -Force -Path $proxyRoot, $storageRoot, $logsRoot | Out-Null

$storageCaddy = ConvertTo-CaddyPath $storageRoot
$accessLogCaddy = ConvertTo-CaddyPath (Join-Path $logsRoot 'proxy-access.log')
$configPath = Join-Path $proxyRoot 'Caddyfile'
$nextConfigPath = Join-Path $proxyRoot 'Caddyfile.next'
$config = @"
{
	admin off
	persist_config off
	auto_https disable_redirects
	skip_install_trust
	storage file_system "$storageCaddy"
}

$origin {
	tls internal

	basic_auth argon2id {
		$Username $passwordHash
	}

	header {
		X-Content-Type-Options "nosniff"
		Referrer-Policy "no-referrer"
		Permissions-Policy "camera=(), microphone=(), geolocation=()"
	}

	reverse_proxy 127.0.0.1:$GatewayPort {
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
"@

Set-Content -LiteralPath $nextConfigPath -Value $config -Encoding UTF8
try {
  Invoke-CaddyValidation -CaddyPath $caddy -ConfigPath $nextConfigPath
  Move-Item -LiteralPath $nextConfigPath -Destination $configPath -Force
} finally {
  if (Test-Path -LiteralPath $nextConfigPath) {
    Remove-Item -LiteralPath $nextConfigPath -Force
  }
}
Set-Content -LiteralPath (Join-Path $proxyRoot 'public-origin.txt') `
  -Value $origin -Encoding ASCII

# Validation provisions the internal CA. Export only its public root certificate
# to a stable, obvious path; private CA material remains below proxy\storage.
$generatedRoot = Join-Path $storageRoot 'pki\authorities\local\root.crt'
$exportedRoot = Join-Path $proxyRoot 'FraktalGatewayRootCA.crt'
if (Test-Path -LiteralPath $generatedRoot) {
  Copy-Item -LiteralPath $generatedRoot -Destination $exportedRoot -Force
}

if ($ConfigureFirewall) {
  $publicUri = [System.Uri]::new($origin)
  Set-ProxyFirewallRule -Port $publicUri.Port -ProgramPath $caddy
}

Write-Output "Secure remote Web HMI configured at $origin"
Write-Output "Gateway root CA exported for client-device import: $exportedRoot"
