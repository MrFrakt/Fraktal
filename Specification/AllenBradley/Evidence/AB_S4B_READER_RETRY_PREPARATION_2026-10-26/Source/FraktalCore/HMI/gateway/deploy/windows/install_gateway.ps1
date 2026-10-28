param(
  # The authoritative gateway instance set, as written by the wizard:
  # a JSON document of {Name, Endpoint, Port, PublicOrigin} entries, one per
  # PLC. When bound it REPLACES the installed set — instances missing from it
  # are retired (their arguments file is kept as gateway.args.removed).
  [string]$InstancesFile,
  # Single-instance shorthand kept for scripted deployments that predate
  # multi-instance support: it retargets the FIRST instance's PLC endpoint and
  # leaves any other configured instance alone.
  [string]$Endpoint,
  # Secure remote access is a separate listener. Caddy terminates HTTPS/WSS
  # while every Dart gateway remains bound to 127.0.0.1.
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

. (Join-Path $PSScriptRoot 'fraktal_instances.ps1')

$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Fraktal Gateway'
$dataRoot = Get-FraktalDataRoot
$instanceRoot = Get-FraktalInstanceRoot
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
# Every instance runs the same executable out of the install root, so one filter
# stops them all.
Get-Process -Name 'fraktal_gateway' -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -like "$installRoot*" } |
  Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name 'caddy' -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -like "$installRoot*" } |
  Stop-Process -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force -Path $installRoot, $dataRoot, $instanceRoot, (Join-Path $dataRoot 'logs'), $programsRoot | Out-Null

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
  'fraktal_instances.ps1',
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

# ---- Instance set ----------------------------------------------------------
# With no arguments at all this is an upgrade: keep exactly what is installed.
$authoritative = $false
if ($InstancesFile) {
  $instances = @(Read-FraktalInstancesFile $InstancesFile)
  $authoritative = $true
} else {
  $instances = @(Get-FraktalInstances)
  if ($instances.Count -eq 0) {
    # A first install with no instance file: one instance carrying the
    # self-documenting example endpoint, which the operator then edits.
    $instances = @(New-FraktalInstance 'default' 'opc.tcp://127.0.0.1:4840' 8080 '')
  }
  if ($Endpoint) { $instances[0].Endpoint = $Endpoint }
  if ($EnableRemoteAccess -and $PublicOrigin) {
    $instances[0].PublicOrigin = $PublicOrigin
  }
}
$problem = Get-FraktalInstanceSetError $instances
if ($problem) { throw $problem }

Write-Output "step: configuring $($instances.Count) gateway instance(s)"

# The pre-instances layout kept one gateway.args in the data root. Seed the
# first instance from it so site edits — write roots, certificates, read
# scoping — survive the move instead of being replaced by the example.
$legacyConfig = Get-FraktalLegacyConfigPath
$legacyConsumed = $false

foreach ($instance in $instances) {
  $instanceDirectory = Get-FraktalInstanceDirectory $instance.Name
  New-Item -ItemType Directory -Force -Path $instanceDirectory | Out-Null
  $configPath = Join-Path $instanceDirectory 'gateway.args'
  $retiredPath = "$configPath.removed"
  if (-not (Test-Path -LiteralPath $configPath)) {
    if (Test-Path -LiteralPath $retiredPath) {
      Move-Item -LiteralPath $retiredPath -Destination $configPath
      Write-Output "  $($instance.Name): restored a previously retired configuration"
    } elseif (-not $legacyConsumed -and (Test-Path -LiteralPath $legacyConfig)) {
      Copy-Item -LiteralPath $legacyConfig -Destination $configPath
      $legacyConsumed = $true
      Write-Output "  $($instance.Name): migrated the single-instance gateway.args"
    } else {
      Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'gateway.args.example') -Destination $configPath
    }
  }

  # Installer-owned settings. Rewriting --port also repairs malformed legacy
  # values such as `8080\`, which otherwise make Dart's int.parse abort before
  # the gateway creates a listener.
  Set-FraktalArgument -Path $configPath -Option '--instance-name' -Value $instance.Name
  Set-FraktalArgument -Path $configPath -Option '--port' -Value "$($instance.Port)"
  Set-FraktalArgument -Path $configPath -Option '--web-root' -Value $webRoot
  if ($instance.Endpoint) {
    Set-FraktalArgument -Path $configPath -Option '--plc-endpoint' -Value $instance.Endpoint
  }
  # The web path's command scope. An empty list removes --write-root, which is
  # what makes the browser a read-only viewer: the gateway refuses every
  # operator command before it reaches the PLC. Installer-owned, so it is
  # rewritten on every run rather than left to drift.
  $writeRoots = @($instance.WriteRoots | Where-Object { $_ })
  Set-FraktalArgumentList -Path $configPath -Option '--write-root' -Values $writeRoots
  if ($writeRoots.Count -eq 0) {
    Write-Output "  $($instance.Name): READ-ONLY (no command scope; the browser can display but not command)"
  } else {
    Write-Output "  $($instance.Name): commands allowed for $($writeRoots -join ', ')"
  }
}

if ($legacyConsumed) {
  Move-Item -LiteralPath $legacyConfig -Destination "$legacyConfig.migrated" -Force
}

# Instances the operator removed. The arguments file is preserved under a name
# discovery ignores, because it may hold hand-written site scoping the operator
# would otherwise have to reconstruct from memory.
if ($authoritative) {
  $configuredNames = @($instances | ForEach-Object { $_.Name })
  $existingDirectories = @(
    Get-ChildItem -LiteralPath $instanceRoot -Directory -ErrorAction SilentlyContinue
  )
  foreach ($directory in $existingDirectories) {
    if ($configuredNames -contains $directory.Name) { continue }
    $orphan = Join-Path $directory.FullName 'gateway.args'
    if (-not (Test-Path -LiteralPath $orphan)) { continue }
    Move-Item -LiteralPath $orphan -Destination "$orphan.removed" -Force
    Write-Output "  $($directory.Name): retired (configuration kept as gateway.args.removed)"
  }
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

if ($EnableRemoteAccess) {
  $sites = @($instances | Where-Object { -not [string]::IsNullOrWhiteSpace($_.PublicOrigin) })
  if ($sites.Count -eq 0) {
    throw 'PublicOrigin is required when secure remote access is enabled.'
  }
  Write-Output "step: configuring the HTTPS proxy for $($sites.Count) site(s)"
  $sitesFile = Join-Path $env:TEMP `
    ('fraktal-proxy-sites-' + [guid]::NewGuid().ToString('N') + '.json')
  Write-FraktalInstancesFile $sitesFile $sites
  try {
    $proxyScript = Join-Path $installRoot 'configure_reverse_proxy.ps1'
    & $proxyScript `
      -SitesFile $sitesFile `
      -Username $ProxyUsername `
      -InstallRoot $installRoot `
      -DataRoot $dataRoot `
      -ConfigureFirewall:$ConfigureFirewall `
      -Unattended:$Unattended
  } finally {
    Remove-Item -LiteralPath $sitesFile -Force -ErrorAction SilentlyContinue
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

  # Each instance authorizes exactly its own browser origin. The gateway itself
  # stays on loopback; this is the second, application-layer boundary.
  foreach ($instance in $instances) {
    $configPath = Get-FraktalInstanceConfigPath $instance.Name
    if ([string]::IsNullOrWhiteSpace($instance.PublicOrigin)) {
      Remove-FraktalArgument -Path $configPath -Option '--allow-origin'
      continue
    }
    Set-FraktalArgument -Path $configPath -Option '--allow-origin' `
      -Value (Get-NormalizedHttpsOrigin $instance.PublicOrigin)
  }
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

# One configuration shortcut per instance. Stale ones are removed first so a
# renamed or retired instance cannot leave a shortcut to a file nobody reads.
Get-ChildItem -LiteralPath $programsRoot -Filter 'Edit Gateway Configuration*.lnk' `
  -ErrorAction SilentlyContinue |
  Remove-Item -Force -ErrorAction SilentlyContinue
foreach ($instance in $instances) {
  $configPath = Get-FraktalInstanceConfigPath $instance.Name
  $shortcutName = if ($instances.Count -eq 1) {
    'Edit Gateway Configuration.lnk'
  } else {
    "Edit Gateway Configuration ($($instance.Name)).lnk"
  }
  Set-Shortcut `
    -Path (Join-Path $programsRoot $shortcutName) `
    -Target "$env:SystemRoot\System32\notepad.exe" `
    -WorkingDirectory (Get-FraktalInstanceDirectory $instance.Name) `
    -Arguments ('"' + $configPath + '"')
}

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

# Launch the tray app. It supervises one gateway process per configured
# instance and is long-lived, deliberately outliving this script.
#
# Callers must therefore wait on THIS process only, never on its process tree:
# `Start-Process -Wait` puts the child in a job object and waits for the whole
# job to empty, which the running tray never lets happen. fraktal_wizard.ps1 uses
# System.Diagnostics.Process.WaitForExit() for exactly this reason. Trying to
# detach here instead (e.g. `cmd /c start`) does NOT help — job membership is
# inherited and cannot be shed without CREATE_BREAKAWAY_FROM_JOB.
Write-Output 'step: starting tray'
Start-Process -FilePath $trayExe -WorkingDirectory $installRoot

# Only pop Notepad for a direct/standalone run of a single-instance install.
# Under the combined wizard the child process tree is waited on, so opening an
# interactive editor here makes the wizard appear hung (its Close button cannot
# run until this returns).
if (-not $Unattended -and $instances.Count -eq 1) {
  Start-Process -FilePath 'notepad.exe' `
    -ArgumentList ('"' + (Get-FraktalInstanceConfigPath $instances[0].Name) + '"')
}

Write-Output 'step: done'
