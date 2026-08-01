param(
  # The PLC OPC UA endpoint the gateway connects to. When bound, the value is
  # written into gateway.args as the line immediately after `--plc-endpoint`
  # (the documented one-option/value-per-line contract). When omitted, the
  # example default is left in place so a standalone run stays self-documenting.
  [string]$Endpoint,
  # Secure remote access is a separate listener. Caddy terminates HTTPS/WSS
  # while the Dart gateway remains bound to 127.0.0.1.
  [switch]$EnableRemoteAccess,
  [string]$PublicOrigin,
  [string]$ProxyUsername = 'fraktal',
  [switch]$ConfigureFirewall,
  # Trusts the generated private CA only for the Windows account running this
  # installer. Remote operator devices still require an explicit public-root
  # import (or site-managed PKI).
  [switch]$TrustProxyCaForCurrentUser,
  # Set by the combined wizard: suppress interactive follow-ups (Notepad) that
  # would block the caller waiting on this script's process tree.
  [switch]$Unattended
)

$ErrorActionPreference = 'Stop'

$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Fraktal Gateway'
$dataRoot = Join-Path $env:LOCALAPPDATA 'Fraktal\Gateway'
$programsRoot = Join-Path ([Environment]::GetFolderPath('Programs')) 'Fraktal Gateway'
$startupRoot = [Environment]::GetFolderPath('Startup')

Write-Output 'step: stopping any running gateway/tray'
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
Get-Process -Name 'caddy' -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -like "$installRoot*" } |
  Stop-Process -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force -Path $installRoot, $dataRoot, (Join-Path $dataRoot 'logs'), $programsRoot | Out-Null

$payload = @(
  'fraktal_gateway.exe',
  'fraktal_gateway_tray.exe',
  'fraktal_opcua.dll',
  'caddy.exe',
  'CADDY_LICENSE.txt',
  'CADDY_README.md',
  'DEPLOYMENT.md',
  'WEB_HMI_GATEWAY_DEPLOYMENT.md',
  'gateway.args.example',
  'configure_reverse_proxy.ps1',
  'configure_proxy_firewall.ps1',
  'uninstall_gateway.ps1'
)
Write-Output 'step: copying program files'
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
Write-Output 'step: expanding Web HMI bundle'
Expand-Archive -LiteralPath $webArchive -DestinationPath $webNext -Force
if (-not (Test-Path -LiteralPath (Join-Path $webNext 'index.html'))) {
  throw 'The packaged Web HMI is missing index.html.'
}
if (Test-Path -LiteralPath $webRoot) {
  Remove-Item -LiteralPath $webRoot -Recurse -Force
}
Move-Item -LiteralPath $webNext -Destination $webRoot

Write-Output 'step: writing gateway.args'
$configPath = Join-Path $dataRoot 'gateway.args'
if (-not (Test-Path -LiteralPath $configPath)) {
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'gateway.args.example') -Destination $configPath
}

# Replace one option and its following value without depending on the example's
# previous literal. Duplicate occurrences are collapsed so one file has one
# authoritative value for every installer-owned setting.
function Set-FraktalArgument(
  [string]$Path,
  [string]$Option,
  [string]$Value
) {
  $lines = Get-Content -LiteralPath $Path
  $result = New-Object System.Collections.Generic.List[string]
  $found = $false
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i].Trim() -eq $Option) {
      if (-not $found) {
        $result.Add($Option) | Out-Null
        $result.Add($Value) | Out-Null
        $found = $true
      }
      if ($i + 1 -lt $lines.Count -and
          -not $lines[$i + 1].TrimStart().StartsWith('--')) {
        $i++
      }
      continue
    }
    $result.Add($lines[$i]) | Out-Null
  }
  if (-not $found) {
    if ($result.Count -gt 0 -and $result[$result.Count - 1] -ne '') {
      $result.Add('') | Out-Null
    }
    $result.Add($Option) | Out-Null
    $result.Add($Value) | Out-Null
  }
  Set-Content -LiteralPath $Path -Value $result -Encoding UTF8
}

function Install-CurrentUserRootCertificate([string]$CertificatePath) {
  if (-not (Test-Path -LiteralPath $CertificatePath)) {
    throw "The exported gateway root CA certificate is missing: $CertificatePath"
  }
  $certificate =
    New-Object System.Security.Cryptography.X509Certificates.X509Certificate2(
      $CertificatePath
    )
  $basicConstraints = $certificate.Extensions |
    Where-Object {
      $_ -is [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]
    } |
    Select-Object -First 1
  if (-not $basicConstraints -or -not $basicConstraints.CertificateAuthority) {
    throw "Refusing to trust a certificate that is not a CA: $CertificatePath"
  }

  $store = New-Object System.Security.Cryptography.X509Certificates.X509Store(
    [System.Security.Cryptography.X509Certificates.StoreName]::Root,
    [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser
  )
  try {
    $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
    $existing = $store.Certificates.Find(
      [System.Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint,
      $certificate.Thumbprint,
      $false
    )
  } finally {
    $store.Close()
  }
  if ($existing.Count -gt 0) {
    $certificate.Dispose()
    return
  }

  # Windows protects root-store changes with an interactive security prompt on
  # some site policies. Deliberately show that prompt to the commissioning user;
  # a hidden X509Store.Add/certutil can otherwise wait forever and make the
  # installer look frozen. The bounded wait turns a missed/blocked prompt into
  # a clear installation error.
  $certutil = Join-Path $env:SystemRoot 'System32\certutil.exe'
  $arguments = @(
    '-user', '-addstore', '-f', 'Root', ('"' + $CertificatePath + '"')
  )
  $process = Start-Process -FilePath $certutil -ArgumentList $arguments `
    -PassThru -WindowStyle Normal
  $null = $process.Handle
  try {
    if (-not $process.WaitForExit(120000)) {
      try { $process.Kill() } catch {}
      throw 'Windows root-CA confirmation timed out after 120 seconds. Re-run the installer and accept the certificate prompt, or clear the trust checkbox and deploy the root through site policy.'
    }
    if ($process.ExitCode -ne 0) {
      throw "Windows did not trust the gateway root CA (certutil exit $($process.ExitCode))."
    }
  } finally {
    $process.Dispose()
  }

  $store = New-Object System.Security.Cryptography.X509Certificates.X509Store(
    [System.Security.Cryptography.X509Certificates.StoreName]::Root,
    [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser
  )
  try {
    $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
    $trusted = $store.Certificates.Find(
      [System.Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint,
      $certificate.Thumbprint,
      $false
    )
    if ($trusted.Count -eq 0) {
      throw 'certutil returned success, but the gateway root CA is absent from the current-user Root store.'
    }
  } finally {
    $store.Close()
    $certificate.Dispose()
  }
}

# The local listener is installer-owned. Rewriting it also repairs malformed
# legacy values such as `8080\`, which otherwise make Dart's int.parse abort
# before the gateway creates a listener.
Set-FraktalArgument -Path $configPath -Option '--port' -Value '8080'
Set-FraktalArgument -Path $configPath -Option '--web-root' -Value $webRoot
if ($Endpoint) {
  Set-FraktalArgument -Path $configPath -Option '--plc-endpoint' -Value $Endpoint
}

if ($EnableRemoteAccess) {
  $proxyConfig = Join-Path $dataRoot 'proxy\Caddyfile'
  $proxyOrigin = Join-Path $dataRoot 'proxy\public-origin.txt'
  if ([string]::IsNullOrWhiteSpace($PublicOrigin) -and
      (Test-Path -LiteralPath $proxyOrigin)) {
    $PublicOrigin = (Get-Content -LiteralPath $proxyOrigin -Raw).Trim()
  }
  if ([string]::IsNullOrWhiteSpace($PublicOrigin)) {
    throw 'PublicOrigin is required when secure remote access is enabled.'
  }
  $proxyPassword = [Environment]::GetEnvironmentVariable(
    'FRAKTAL_PROXY_PASSWORD',
    [EnvironmentVariableTarget]::Process
  )
  if ((Test-Path -LiteralPath $proxyConfig) -and
      (Test-Path -LiteralPath $proxyOrigin) -and
      [string]::IsNullOrEmpty($proxyPassword)) {
    # Passwords are intentionally unrecoverable. An upgrade with no new
    # password preserves the validated site Caddyfile, hash, CA, and firewall
    # rule instead of silently replacing site security.
    $normalizedOrigin = (Get-Content -LiteralPath $proxyOrigin -Raw).Trim()
    $validation = Start-Process -FilePath (Join-Path $installRoot 'caddy.exe') `
      -ArgumentList @(
        'validate', '--config', "`"$proxyConfig`"", '--adapter', 'caddyfile'
      ) `
      -Wait -PassThru -WindowStyle Hidden
    if ($validation.ExitCode -ne 0) {
      throw "The preserved HTTPS proxy configuration is not valid with the packaged Caddy version (exit $($validation.ExitCode))."
    }
  } else {
    $proxyScript = Join-Path $installRoot 'configure_reverse_proxy.ps1'
    & $proxyScript `
      -PublicOrigin $PublicOrigin `
      -Username $ProxyUsername `
      -GatewayPort 8080 `
      -InstallRoot $installRoot `
      -DataRoot $dataRoot `
      -ConfigureFirewall:$ConfigureFirewall `
      -Unattended:$Unattended
    $normalizedOrigin = (Get-Content -LiteralPath $proxyOrigin -Raw).Trim()
  }
  $proxyRoot = Join-Path $dataRoot 'proxy'
  $exportedRoot = Join-Path $proxyRoot 'FraktalGatewayRootCA.crt'
  if (-not (Test-Path -LiteralPath $exportedRoot)) {
    $generatedRoot = Join-Path $proxyRoot 'storage\pki\authorities\local\root.crt'
    if (Test-Path -LiteralPath $generatedRoot) {
      Copy-Item -LiteralPath $generatedRoot -Destination $exportedRoot -Force
    }
  }
  if ($TrustProxyCaForCurrentUser) {
    Install-CurrentUserRootCertificate -CertificatePath $exportedRoot
    $trustedCertificate =
      New-Object System.Security.Cryptography.X509Certificates.X509Certificate2(
        $exportedRoot
      )
    try {
      Set-Content -LiteralPath (Join-Path $proxyRoot 'trusted-current-user-ca.thumbprint') `
        -Value $trustedCertificate.Thumbprint -Encoding ASCII
      Write-Output "Gateway root CA trusted for current Windows user: $($trustedCertificate.Thumbprint)"
    } finally {
      $trustedCertificate.Dispose()
    }
  } else {
    Write-Output 'Gateway root CA exported but not added to Windows trust.'
  }
  Set-FraktalArgument -Path $configPath -Option '--allow-origin' -Value $normalizedOrigin
}

Write-Output 'step: shortcuts and uninstall entry'
$shell = New-Object -ComObject WScript.Shell
function Set-Shortcut(
  [string]$Path,
  [string]$Target,
  [string]$WorkingDirectory,
  [string]$Arguments = ''
) {
  $shortcut = $shell.CreateShortcut($Path)
  $shortcut.TargetPath = $Target
  $shortcut.WorkingDirectory = $WorkingDirectory
  $shortcut.Arguments = $Arguments
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
if ($EnableRemoteAccess) {
  $proxyRoot = Join-Path $dataRoot 'proxy'
  $legacyCaShortcut = Join-Path $programsRoot 'Client CA Certificate.lnk'
  if (Test-Path -LiteralPath $legacyCaShortcut) {
    Remove-Item -LiteralPath $legacyCaShortcut -Force
  }
  Set-Shortcut `
    -Path (Join-Path $programsRoot 'Edit HTTPS Proxy Configuration.lnk') `
    -Target "$env:SystemRoot\System32\notepad.exe" `
    -WorkingDirectory $proxyRoot `
    -Arguments ('"' + (Join-Path $proxyRoot 'Caddyfile') + '"')
  Set-Shortcut `
    -Path (Join-Path $programsRoot 'Exported Gateway Root CA.lnk') `
    -Target "$env:SystemRoot\explorer.exe" `
    -WorkingDirectory $proxyRoot `
    -Arguments ('/select,"' + (Join-Path $proxyRoot 'FraktalGatewayRootCA.crt') + '"')
}

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

# Launch the tray app. It is long-lived and deliberately outlives this script.
#
# Callers must therefore wait on THIS process only, never on its process tree:
# `Start-Process -Wait` puts the child in a job object and waits for the whole
# job to empty, which the running tray never lets happen. fraktal_wizard.ps1 uses
# System.Diagnostics.Process.WaitForExit() for exactly this reason. Trying to
# detach here instead (e.g. `cmd /c start`) does NOT help — job membership is
# inherited and cannot be shed without CREATE_BREAKAWAY_FROM_JOB.
Write-Output 'step: starting tray'
Start-Process -FilePath $trayExe -WorkingDirectory $installRoot

# Only pop Notepad for a direct/standalone run. Under the combined wizard the
# child process tree is waited on, so opening an interactive editor here makes
# the wizard appear hung (its Close button cannot run until this returns).
if (-not $Unattended) {
  Start-Process -FilePath 'notepad.exe' -ArgumentList ('"' + $configPath + '"')
}

Write-Output 'step: done'
