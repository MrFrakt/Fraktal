# Shared instance model for the Fraktal Gateway deployment scripts.
#
# ONE gateway process serves ONE PLC. A host serves several controllers by
# running several gateway instances, and an instance is nothing more than a
# folder:
#
#   %LOCALAPPDATA%\Fraktal\Gateway\instances\<name>\gateway.args
#
# The folder name IS the instance name; every other setting — PLC endpoint,
# loopback port, allowed origin, read/write roots, certificates — lives in that
# one arguments file. There is deliberately no second index file to keep in
# step, so discovery is "every subfolder that has a gateway.args".
#
# That rule is written once here for the wizard, the installer, and the
# uninstaller. The tray implements the same rule in C++
# (gateway/windows_tray/fraktal_gateway_tray.cpp) — keep the two in step.

# A host that needs more than this many PLCs wants a server topology, not a
# tray. The bound also keeps the tray's per-instance menu IDs in a fixed range.
$FraktalMaxInstances = 16

function Get-FraktalDataRoot {
  return (Join-Path $env:LOCALAPPDATA 'Fraktal\Gateway')
}

function Get-FraktalInstanceRoot {
  return (Join-Path (Get-FraktalDataRoot) 'instances')
}

function Get-FraktalInstanceDirectory([string]$Name) {
  return (Join-Path (Get-FraktalInstanceRoot) $Name)
}

function Get-FraktalInstanceConfigPath([string]$Name) {
  return (Join-Path (Get-FraktalInstanceDirectory $Name) 'gateway.args')
}

# The pre-instances layout: a single gateway.args directly in the data root.
# An installation from before multi-instance support keeps working because
# discovery falls back to it, and the installer migrates it on the next run.
function Get-FraktalLegacyConfigPath {
  return (Join-Path (Get-FraktalDataRoot) 'gateway.args')
}

function Test-FraktalInstanceName([string]$Name) {
  if ([string]::IsNullOrWhiteSpace($Name)) { return $false }
  # '.' and '..' match the character class but are path traversal, not names.
  if ($Name -eq '.' -or $Name -eq '..') { return $false }
  return $Name -match '^[A-Za-z0-9._-]{1,32}$'
}

# Validates an endpoint the same way the HMI wizard does, so a bad value fails
# here instead of letting the installed gateway reject it later.
#   scheme in {ws,wss,http,https,opc.tcp,ads}; an ads:// host has 6 dot parts.
function Test-FraktalEndpoint([string]$Endpoint) {
  if ([string]::IsNullOrWhiteSpace($Endpoint)) { return $false }
  try { $uri = [System.Uri]::new($Endpoint.Trim()) } catch { return $false }
  if (-not $uri.IsAbsoluteUri -or [string]::IsNullOrEmpty($uri.Host)) { return $false }
  $scheme = $uri.Scheme.ToLowerInvariant()
  if ($scheme -notin @('ws', 'wss', 'http', 'https', 'opc.tcp', 'ads')) { return $false }
  if ($scheme -eq 'ads' -and ($uri.Host.Split('.') | Measure-Object).Count -ne 6) { return $false }
  return $true
}

# A published root Unit browse path, validated the way the gateway itself does
# (FraktalGatewayConfig._normalizeBrowseRoot): non-empty segments, no '.'/'..',
# no control characters. The SHAPE differs by transport and the installer cannot
# infer it: over ADS a root is `PneumaticPress`, over TF6100 OPC UA the same
# Unit is `PLC1/MAIN/PneumaticPress`. Both are accepted here; the gateway
# compares the value against the paths its own transport publishes.
function Test-FraktalBrowseRoot([string]$Root) {
  if ([string]::IsNullOrWhiteSpace($Root)) { return $false }
  $value = $Root.Trim().TrimEnd('/')
  if ($value.Length -eq 0 -or $value.Length -gt 2048) { return $false }
  foreach ($segment in $value.Split('/')) {
    if ($segment -eq '' -or $segment -eq '.' -or $segment -eq '..') { return $false }
  }
  return -not ($value.ToCharArray() | Where-Object { [int]$_ -lt 32 })
}

# The operator types one field; a multi-root HMI separates roots with a comma.
function ConvertTo-FraktalBrowseRoots([string]$Text) {
  if ([string]::IsNullOrWhiteSpace($Text)) { return @() }
  return @($Text.Split(',') |
    ForEach-Object { $_.Trim().TrimEnd('/') } |
    Where-Object { $_ })
}

function Test-HttpsOrigin([string]$Origin) {
  if ([string]::IsNullOrWhiteSpace($Origin)) { return $false }
  try { $uri = [System.Uri]::new($Origin.Trim()) } catch { return $false }
  return $uri.IsAbsoluteUri -and
    $uri.Scheme -eq 'https' -and
    -not [string]::IsNullOrWhiteSpace($uri.Host) -and
    [string]::IsNullOrEmpty($uri.UserInfo) -and
    ($uri.AbsolutePath -eq '/' -or $uri.AbsolutePath -eq '') -and
    [string]::IsNullOrEmpty($uri.Query) -and
    [string]::IsNullOrEmpty($uri.Fragment)
}

# The one spelling of an origin every consumer agrees on: the Caddy site
# address, the gateway's --allow-origin, and the browser's Origin header must
# match exactly, so they are all normalized through here.
function Get-NormalizedHttpsOrigin([string]$Value) {
  if (-not (Test-HttpsOrigin $Value)) {
    throw 'The public Web HMI origin must be only https://<host>[:port], with no path, credentials, query, or fragment.'
  }
  $uri = [System.Uri]::new($Value.Trim())
  return $uri.GetComponents(
    [System.UriComponents]::SchemeAndServer,
    [System.UriFormat]::UriEscaped
  ).TrimEnd('/')
}

function New-FraktalInstance(
  [string]$Name,
  [string]$Endpoint,
  [int]$Port,
  [string]$PublicOrigin,
  [string[]]$WriteRoots = @()
) {
  return [PSCustomObject]@{
    Name         = $Name
    Endpoint     = $Endpoint
    Port         = $Port
    PublicOrigin = $PublicOrigin
    # The root Unit browse paths this instance may command. EMPTY MEANS
    # READ-ONLY: the browser shows everything the PLC publishes and every
    # operator command is refused by the gateway before it reaches the PLC.
    # This is the web path's write scope and nothing else — the native HMI
    # talks to the PLC directly and is unaffected, and the PLC re-checks its
    # own §7.6/§7.7 release and access gates regardless.
    WriteRoots   = @($WriteRoots | Where-Object { $_ })
    ConfigPath   = (Get-FraktalInstanceConfigPath $Name)
  }
}

# Reads one option's value out of a gateway.args file. The documented format is
# one option or value per line, so the value is simply the next non-comment line.
function Get-FraktalArgumentValue([string]$Path, [string]$Option) {
  if (-not (Test-Path -LiteralPath $Path)) { return '' }
  $lines = @(Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue)
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i].Trim() -ne $Option) { continue }
    if ($i + 1 -ge $lines.Count) { return '' }
    $value = $lines[$i + 1].Trim()
    if ($value.StartsWith('--') -or $value.StartsWith('#')) { return '' }
    return $value
  }
  return ''
}

# Every value of a REPEATABLE option (--write-root, --read-root, --allow-origin).
# Get-FraktalArgumentValue returns only the first, which would silently drop the
# second and third root of a multi-root HMI on the next upgrade.
function Get-FraktalArgumentValues([string]$Path, [string]$Option) {
  $values = New-Object System.Collections.Generic.List[string]
  if (-not (Test-Path -LiteralPath $Path)) { return $values.ToArray() }
  $lines = @(Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue)
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i].Trim() -ne $Option) { continue }
    if ($i + 1 -ge $lines.Count) { continue }
    $value = $lines[$i + 1].Trim()
    if ($value.StartsWith('--') -or $value.StartsWith('#')) { continue }
    $values.Add($value) | Out-Null
  }
  return $values.ToArray()
}

# Rewrite a repeatable option to exactly this list: every existing occurrence is
# dropped, then one option/value pair is appended per value. An empty list
# therefore REMOVES the option, which is how an instance becomes read-only.
function Set-FraktalArgumentList(
  [string]$Path,
  [string]$Option,
  [string[]]$Values
) {
  Remove-FraktalArgument -Path $Path -Option $Option
  foreach ($value in @($Values | Where-Object { $_ })) {
    $lines = @(Get-Content -LiteralPath $Path)
    $result = New-Object System.Collections.Generic.List[string]
    foreach ($line in $lines) { $result.Add($line) | Out-Null }
    if ($result.Count -gt 0 -and $result[$result.Count - 1] -ne '') {
      $result.Add('') | Out-Null
    }
    $result.Add($Option) | Out-Null
    $result.Add($value) | Out-Null
    Set-Content -LiteralPath $Path -Value $result -Encoding UTF8
  }
}

# Replace one option and its following value without depending on the file's
# previous literal. Duplicate occurrences are collapsed so one file has one
# authoritative value for every installer-owned setting.
function Set-FraktalArgument(
  [string]$Path,
  [string]$Option,
  [string]$Value
) {
  $lines = @(Get-Content -LiteralPath $Path)
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

# Drops an option and its value. Needed when an instance loses a setting it
# previously had — an --allow-origin left behind after remote access is turned
# off would keep authorizing that browser origin.
function Remove-FraktalArgument([string]$Path, [string]$Option) {
  if (-not (Test-Path -LiteralPath $Path)) { return }
  $lines = @(Get-Content -LiteralPath $Path)
  $result = New-Object System.Collections.Generic.List[string]
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i].Trim() -eq $Option) {
      if ($i + 1 -lt $lines.Count -and
          -not $lines[$i + 1].TrimStart().StartsWith('--')) {
        $i++
      }
      continue
    }
    $result.Add($lines[$i]) | Out-Null
  }
  Set-Content -LiteralPath $Path -Value $result -Encoding UTF8
}

# Every configured instance, derived from disk. Each instance's own arguments
# file is the single source for its endpoint, port, and public origin.
function Get-FraktalInstances {
  $result = New-Object System.Collections.Generic.List[object]
  $root = Get-FraktalInstanceRoot
  if (Test-Path -LiteralPath $root) {
    $directories = @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
      Sort-Object Name)
    foreach ($directory in $directories) {
      $config = Join-Path $directory.FullName 'gateway.args'
      if (-not (Test-Path -LiteralPath $config)) { continue }
      if (-not (Test-FraktalInstanceName $directory.Name)) { continue }
      $result.Add((New-FraktalInstanceFromConfig $directory.Name $config)) | Out-Null
    }
  }
  if ($result.Count -eq 0) {
    $legacy = Get-FraktalLegacyConfigPath
    if (Test-Path -LiteralPath $legacy) {
      $instance = New-FraktalInstanceFromConfig 'default' $legacy
      $instance.ConfigPath = $legacy
      $result.Add($instance) | Out-Null
    }
  }
  # Emitted unwrapped; every caller collects with @(...) so a lone instance and
  # an empty set both arrive as arrays.
  return $result.ToArray()
}

function New-FraktalInstanceFromConfig([string]$Name, [string]$ConfigPath) {
  $port = 0
  $rawPort = Get-FraktalArgumentValue $ConfigPath '--port'
  if (-not [int]::TryParse($rawPort, [ref]$port) -or $port -lt 1 -or $port -gt 65535) {
    $port = 8080
  }
  return [PSCustomObject]@{
    Name         = $Name
    Endpoint     = (Get-FraktalArgumentValue $ConfigPath '--plc-endpoint')
    Port         = $port
    PublicOrigin = (Get-FraktalArgumentValue $ConfigPath '--allow-origin')
    # Read back as a LIST: an upgrade must not silently drop the second and
    # third root of a multi-root HMI, nor turn a commanding instance read-only.
    WriteRoots   = @(Get-FraktalArgumentValues $ConfigPath '--write-root')
    ConfigPath   = $ConfigPath
  }
}

# Returns '' when the set can be installed, otherwise the one problem to show
# the operator. Ports and origins must be unique because each instance owns a
# whole listener: two instances on one port silently leave one PLC unreachable.
function Get-FraktalInstanceSetError([object[]]$Instances) {
  if ($null -eq $Instances -or $Instances.Count -eq 0) {
    return 'Configure at least one gateway instance.'
  }
  if ($Instances.Count -gt $FraktalMaxInstances) {
    return "A host supports at most $FraktalMaxInstances gateway instances."
  }
  $names = @()
  $ports = @()
  $origins = @()
  foreach ($instance in $Instances) {
    $name = "$($instance.Name)"
    if (-not (Test-FraktalInstanceName $name)) {
      return "Instance name '$name' must be 1-32 letters, digits, dots, underscores, or hyphens."
    }
    if ($names -contains $name.ToLowerInvariant()) {
      return "Instance name '$name' is used twice."
    }
    $names += $name.ToLowerInvariant()
    if (-not (Test-FraktalEndpoint $instance.Endpoint)) {
      return "Instance '$name' has an invalid PLC endpoint: $($instance.Endpoint)"
    }
    $port = 0
    if (-not [int]::TryParse("$($instance.Port)", [ref]$port) -or
        $port -lt 1 -or $port -gt 65535) {
      return "Instance '$name' has an invalid local port: $($instance.Port)"
    }
    if ($ports -contains $port) {
      return "Local port $port is configured twice; each instance owns its own listener."
    }
    $ports += $port
    foreach ($root in @($instance.WriteRoots)) {
      if (-not (Test-FraktalBrowseRoot $root)) {
        return "Instance '$name' has an invalid command scope: '$root'. Use the published root Unit browse path, e.g. PneumaticPress (ADS) or PLC1/MAIN/PneumaticPress (OPC UA)."
      }
    }
    if (-not [string]::IsNullOrWhiteSpace($instance.PublicOrigin)) {
      if (-not (Test-HttpsOrigin $instance.PublicOrigin)) {
        return "Instance '$name' has an invalid public HTTPS origin: $($instance.PublicOrigin)"
      }
      $origin = $instance.PublicOrigin.Trim().ToLowerInvariant()
      if ($origins -contains $origin) {
        return "Public origin $($instance.PublicOrigin) is configured twice; give each instance its own host name or port."
      }
      $origins += $origin
    }
  }
  return ''
}

# The lowest loopback port at or above 8080 that no listed instance uses.
function Get-FraktalNextFreePort([object[]]$Instances) {
  $used = @()
  foreach ($instance in $Instances) {
    $port = 0
    if ([int]::TryParse("$($instance.Port)", [ref]$port)) { $used += $port }
  }
  for ($candidate = 8080; $candidate -le 8180; $candidate++) {
    if ($used -notcontains $candidate) { return $candidate }
  }
  return 8080
}

# Instances are handed between the wizard and the installer as a file rather
# than as command-line arguments: a URI, an origin, and a name per instance do
# not survive nested PowerShell quoting reliably.
function Read-FraktalInstancesFile([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "The gateway instance file is missing: $Path"
  }
  $raw = Get-Content -LiteralPath $Path -Raw
  if ([string]::IsNullOrWhiteSpace($raw)) {
    throw "The gateway instance file is empty: $Path"
  }
  $parsed = $raw | ConvertFrom-Json
  if ($null -ne $parsed -and $parsed.PSObject.Properties.Name -contains 'instances') {
    $parsed = $parsed.instances
  }
  $result = New-Object System.Collections.Generic.List[object]
  foreach ($entry in @($parsed)) {
    if ($null -eq $entry) { continue }
    $port = 0
    [void][int]::TryParse("$($entry.Port)", [ref]$port)
    $result.Add((New-FraktalInstance `
      "$($entry.Name)" `
      "$($entry.Endpoint)" `
      $port `
      "$($entry.PublicOrigin)" `
      @($entry.WriteRoots | Where-Object { $_ }))) | Out-Null
  }
  return $result.ToArray()
}

function Write-FraktalInstancesFile([string]$Path, [object[]]$Instances) {
  # A single-element array collapses to a bare object through the pipeline
  # form of ConvertTo-Json, so the list is always nested in a property.
  $document = @{
    instances = @(
      foreach ($instance in $Instances) {
        [ordered]@{
          Name         = "$($instance.Name)"
          Endpoint     = "$($instance.Endpoint)"
          Port         = [int]$instance.Port
          PublicOrigin = "$($instance.PublicOrigin)"
          WriteRoots   = @($instance.WriteRoots | Where-Object { $_ })
        }
      }
    )
  }
  Set-Content -LiteralPath $Path `
    -Value (ConvertTo-Json -InputObject $document -Depth 4) -Encoding UTF8
}

# Ask the local TwinCAT ADS router for its authoritative six-byte AMS Net ID.
# The router API is preferable to deriving a Net ID from a NIC address: a
# controller may have multiple adapters and its configured Net ID need not equal
# any current IPv4 address. Discovery is best-effort so installation remains
# usable while TwinCAT is stopped or on a non-TwinCAT engineering PC.
function Get-LocalAdsEndpoint {
  $fallback = [PSCustomObject]@{
    Endpoint = 'ads://127.0.0.1.1.1:851'
    Detected = $false
    Detail = 'TwinCAT router discovery was unavailable; confirm the loopback endpoint.'
  }
  try {
    if (-not ('Fraktal.Installer.AdsRouter' -as [type])) {
      Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

namespace Fraktal.Installer {
  [StructLayout(LayoutKind.Sequential, Pack = 1)]
  public struct AmsAddress {
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 6)]
    public byte[] NetId;
    public ushort Port;
  }

  public static class AdsRouter {
    [DllImport("TcAdsDll.dll", CallingConvention = CallingConvention.StdCall)]
    public static extern int AdsPortOpenEx();

    [DllImport("TcAdsDll.dll", CallingConvention = CallingConvention.StdCall)]
    public static extern int AdsPortCloseEx(int port);

    [DllImport("TcAdsDll.dll", CallingConvention = CallingConvention.StdCall)]
    public static extern int AdsGetLocalAddressEx(
      int port,
      ref AmsAddress address
    );
  }
}
'@ -ErrorAction Stop
    }

    $adsPort = [Fraktal.Installer.AdsRouter]::AdsPortOpenEx()
    if ($adsPort -eq 0) { return $fallback }
    try {
      $address = New-Object Fraktal.Installer.AmsAddress
      $address.NetId = New-Object byte[] 6
      $result = [Fraktal.Installer.AdsRouter]::AdsGetLocalAddressEx(
        $adsPort,
        [ref]$address
      )
      if ($result -ne 0 -or
          $address.NetId.Count -ne 6 -or
          (@($address.NetId | Where-Object { $_ -ne 0 }).Count -eq 0)) {
        return $fallback
      }
      $netId = $address.NetId -join '.'
      return [PSCustomObject]@{
        Endpoint = "ads://${netId}:851"
        Detected = $true
        Detail = "Detected local TwinCAT AMS Net ID $netId (runtime port 851)."
      }
    } finally {
      [Fraktal.Installer.AdsRouter]::AdsPortCloseEx($adsPort) | Out-Null
    }
  } catch {
    return $fallback
  }
}

function Get-SuggestedPublicOrigin([int]$Port = 443) {
  $suffix = if ($Port -eq 443) { '' } else { ":$Port" }
  try {
    $address = [System.Net.Dns]::GetHostAddresses($env:COMPUTERNAME) |
      Where-Object {
        $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and
        -not [System.Net.IPAddress]::IsLoopback($_)
      } |
      Select-Object -First 1
    if ($address) { return "https://$($address.IPAddressToString)$suffix" }
  } catch {
    # A hostname remains a valid editable default when address discovery fails.
  }
  return "https://$env:COMPUTERNAME$suffix"
}
