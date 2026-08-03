param(
  # Silent mode: when Components is bound the UI is skipped and the listed
  # components are installed with the supplied endpoints. Escape hatch for
  # Group-Policy/AppLocker hosts where the WinForms UI cannot run, and for
  # scripted deployment.
  [ValidateSet('HMI', 'Gateway', IgnoreCase = $true)]
  [string[]]$Components,
  [string]$HmiEndpoint,
  [string]$GatewayEndpoint,
  [switch]$EnableRemoteAccess,
  [string]$PublicOrigin,
  [string]$ProxyUsername = 'fraktal',
  [switch]$ConfigureFirewall,
  [switch]$TrustProxyCaForCurrentUser
)

# Validates an endpoint the same way the HMI wizard does, so a bad value fails
# here instead of letting the installed app reject it later.
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

function Get-SuggestedPublicOrigin {
  try {
    $address = [System.Net.Dns]::GetHostAddresses($env:COMPUTERNAME) |
      Where-Object {
        $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and
        -not [System.Net.IPAddress]::IsLoopback($_)
      } |
      Select-Object -First 1
    if ($address) { return "https://$($address.IPAddressToString)" }
  } catch {
    # A hostname remains a valid editable default when address discovery fails.
  }
  return "https://$env:COMPUTERNAME"
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

# Runs one component's install script synchronously (IExpress deletes the extract
# dir when this wizard exits, so installs must complete before return) and
# returns $true on success. [string]$Output collects a one-line result.
function Invoke-ComponentInstall(
  [string]$Name,
  [string]$Script,
  [string]$Endpoint,
  [string[]]$AdditionalArguments = @()
) {
  $scriptPath = Join-Path $PSScriptRoot $Script
  if (-not (Test-Path -LiteralPath $scriptPath)) {
    Write-WizardLog "[$Name] install script missing: $scriptPath"
    return $false
  }
  Write-WizardLog "[$Name] installing ($Endpoint) ..."
  # The child runs hidden, so WITHOUT capturing its streams a stall here is
  # invisible: the wizard just sits on "installing ..." forever with no clue
  # which step is blocking. Redirect to files (not pipes — a full pipe buffer
  # would deadlock a hidden child that nobody is draining) and replay them into
  # the wizard log, so the install script's own progress markers are visible.
  #
  # -Unattended stops the child opening Notepad, which would block this wait
  # behind an invisible window.
  $childArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath,
    '-Endpoint', $Endpoint, '-Unattended')
  $childArgs += $AdditionalArguments
  $outFile = [System.IO.Path]::GetTempFileName()
  $errFile = [System.IO.Path]::GetTempFileName()
  $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $childArgs `
    -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $outFile -RedirectStandardError $errFile

  # Touch .Handle NOW, while the child is still alive. `Start-Process -PassThru`
  # (without -Wait) hands back a Process object that has not cached the native
  # handle; once the child exits, Windows releases it and .ExitCode reads back as
  # $null. That makes a completely successful install report "FAILED (exit )".
  # Reading .Handle forces the object to cache it, keeping .ExitCode valid.
  $null = $proc.Handle

  # Bounded wait. An unbounded one turns any unforeseen stall into a wizard that
  # can never be closed; a timeout degrades that to a reported failure.
  $timedOut = -not $proc.WaitForExit($script:InstallTimeoutMs)
  if ($timedOut) {
    try { $proc.Kill() } catch {}
    try { $proc.WaitForExit(5000) | Out-Null } catch {}
  }

  foreach ($f in @($outFile, $errFile)) {
    if (Test-Path -LiteralPath $f) {
      Get-Content -LiteralPath $f -ErrorAction SilentlyContinue |
        Where-Object { $_ -and $_.Trim() } |
        ForEach-Object { Write-WizardLog "    | $_" }
      Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue
    }
  }

  if ($timedOut) {
    Write-WizardLog ("[$Name] TIMED OUT after " +
      [int]($script:InstallTimeoutMs / 1000) +
      's - the last line above is the step that stalled.')
    return $false
  }
  $exit = $null
  try { $exit = $proc.ExitCode } catch { $exit = $null }
  if ($exit -eq 0) {
    Write-WizardLog "[$Name] done."
    return $true
  }
  if ($null -eq $exit) {
    # Should not happen now the handle is cached. Never render this as a bare
    # "FAILED (exit )" — that reads as a real failure and hides the fact that the
    # install itself may have completed.
    Write-WizardLog "[$Name] FAILED (exit code unavailable - install state unknown)."
  } else {
    Write-WizardLog "[$Name] FAILED (exit $exit)."
  }
  return $false
}

# Per-component install timeout. Generous — an industrial IPC unpacking ~50 MB
# over a slow disk is legitimately slow — but finite, so a stalled step reports
# itself instead of leaving a wizard that can never be closed.
$script:InstallTimeoutMs = 900000  # 15 minutes

$script:LogLines = New-Object System.Collections.Generic.List[string]
function Write-WizardLog([string]$Line) {
  $script:LogLines.Add($line) | Out-Null
  if ($script:progressBox) { $script:progressBox.AppendText("$line`r`n") }
}

function Run-SelectedInstalls(
  [string[]]$Selected,
  [string]$Hmi,
  [string]$Gateway,
  [bool]$RemoteAccess,
  [string]$RemoteOrigin,
  [string]$RemoteUsername,
  [bool]$OpenFirewall,
  [bool]$TrustLocalProxyCa
) {
  $script:LogLines.Clear()
  $ok = $true
  foreach ($comp in $Selected) {
    if ($comp -eq 'HMI') {
      if (-not (Test-FraktalEndpoint $Hmi)) { Write-WizardLog '[HMI] invalid endpoint.'; $ok = $false; continue }
      $ok = (Invoke-ComponentInstall 'HMI' 'install_hmi.ps1' $Hmi) -and $ok
    } elseif ($comp -eq 'Gateway') {
      if (-not (Test-FraktalEndpoint $Gateway)) { Write-WizardLog '[Gateway] invalid endpoint.'; $ok = $false; continue }
      $extra = @()
      if ($RemoteAccess) {
        if (-not (Test-HttpsOrigin $RemoteOrigin)) {
          Write-WizardLog '[Gateway] invalid public HTTPS origin.'
          $ok = $false
          continue
        }
        if ($RemoteUsername -notmatch '^[A-Za-z0-9._-]{1,64}$') {
          Write-WizardLog '[Gateway] invalid remote-access username.'
          $ok = $false
          continue
        }
        $extra += @('-EnableRemoteAccess', '-PublicOrigin', $RemoteOrigin,
          '-ProxyUsername', $RemoteUsername)
        if ($OpenFirewall) { $extra += '-ConfigureFirewall' }
        if ($TrustLocalProxyCa) { $extra += '-TrustProxyCaForCurrentUser' }
      }
      $ok = (Invoke-ComponentInstall 'Gateway' 'install_gateway.ps1' $Gateway $extra) -and $ok
    }
  }
  Write-WizardLog ''
  Write-WizardLog "$(if ($ok) { 'Installation finished.' } else { 'Installation finished with errors — see the lines above.' })"
  return $ok
}

# ---- Silent path -----------------------------------------------------------
if ($PSBoundParameters.ContainsKey('Components')) {
  if ($Components.Count -eq 0) {
    [Console]::Error.WriteLine('No components selected. Pass -Components HMI and/or Gateway.')
    exit 2
  }
  if (-not $HmiEndpoint) { $HmiEndpoint = (Get-LocalAdsEndpoint).Endpoint }
  if (-not $GatewayEndpoint) { $GatewayEndpoint = $HmiEndpoint }
  if ($EnableRemoteAccess -and -not $PublicOrigin) {
    [Console]::Error.WriteLine('-PublicOrigin is required with -EnableRemoteAccess.')
    exit 2
  }
  $ok = Run-SelectedInstalls $Components $HmiEndpoint $GatewayEndpoint `
    $EnableRemoteAccess.IsPresent $PublicOrigin $ProxyUsername `
    $ConfigureFirewall.IsPresent $TrustProxyCaForCurrentUser.IsPresent
  if (-not $ok) { exit 1 }
  exit 0
}

# ---- WinForms wizard -------------------------------------------------------
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$installedProxyRoot = Join-Path $env:LOCALAPPDATA 'Fraktal\Gateway\proxy'
$installedProxyConfig = Join-Path $installedProxyRoot 'Caddyfile'
$installedProxyOrigin = Join-Path $installedProxyRoot 'public-origin.txt'
$proxyAlreadyConfigured = (Test-Path -LiteralPath $installedProxyConfig) -and
  (Test-Path -LiteralPath $installedProxyOrigin)
$localAds = Get-LocalAdsEndpoint

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Fraktal Setup'
$form.Size = New-Object System.Drawing.Size(680, 680)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

# --- Page 0: component selection ---
$componentsPage = New-Object System.Windows.Forms.Panel
$componentsPage.Dock = 'Fill'
$intro = New-Object System.Windows.Forms.Label
$intro.Text = "Choose the Fraktal components to install. Select at least one.`r`n`r`nThe native HMI and Gateway can share the same local ADS connection to the PLC. The Gateway serves the browser-based Web HMI."
$intro.AutoSize = $false
$intro.Size = New-Object System.Drawing.Size(620, 90)
$intro.Location = New-Object System.Drawing.Point(20, 15)

$hmiCheck = New-Object System.Windows.Forms.CheckBox
$hmiCheck.Text = 'Fraktal HMI  (native desktop app, ADS direct to PLC)'
$hmiCheck.Location = New-Object System.Drawing.Point(24, 120)
$hmiCheck.Size = New-Object System.Drawing.Size(620, 30)

$gwCheck = New-Object System.Windows.Forms.CheckBox
$gwCheck.Text = 'Fraktal Gateway + Web HMI  (browser access via OPC UA)'
$gwCheck.Location = New-Object System.Drawing.Point(24, 155)
$gwCheck.Size = New-Object System.Drawing.Size(620, 30)

$componentsPage.Controls.AddRange(@($intro, $hmiCheck, $gwCheck))

# --- Page 1: endpoints ---
$endpointsPage = New-Object System.Windows.Forms.Panel
$endpointsPage.Dock = 'Fill'
$epIntro = New-Object System.Windows.Forms.Label
$epIntro.Text = 'Configure the PLC endpoint for each selected component.'
$epIntro.AutoSize = $false
$epIntro.Size = New-Object System.Drawing.Size(620, 40)
$epIntro.Location = New-Object System.Drawing.Point(20, 15)

$hmiEpLabel = New-Object System.Windows.Forms.Label
$hmiEpLabel.Text = 'HMI / local PLC endpoint (ads://<AmsNetId>:<port>):'
$hmiEpLabel.Location = New-Object System.Drawing.Point(24, 55)
$hmiEpLabel.Size = New-Object System.Drawing.Size(600, 20)
$hmiEpBox = New-Object System.Windows.Forms.TextBox
$hmiEpBox.Text = $localAds.Endpoint
$hmiEpBox.Location = New-Object System.Drawing.Point(24, 77)
$hmiEpBox.Size = New-Object System.Drawing.Size(600, 24)

$adsDetectionLabel = New-Object System.Windows.Forms.Label
$adsDetectionLabel.Text = $localAds.Detail
$adsDetectionLabel.ForeColor = if ($localAds.Detected) {
  [System.Drawing.Color]::DarkGreen
} else {
  [System.Drawing.Color]::DarkOrange
}
$adsDetectionLabel.Location = New-Object System.Drawing.Point(24, 105)
$adsDetectionLabel.Size = New-Object System.Drawing.Size(600, 20)

$sameEndpointCheck = New-Object System.Windows.Forms.CheckBox
$sameEndpointCheck.Text = 'Use the HMI / local PLC endpoint for the Gateway'
$sameEndpointCheck.Checked = $true
$sameEndpointCheck.Location = New-Object System.Drawing.Point(24, 130)
$sameEndpointCheck.Size = New-Object System.Drawing.Size(600, 28)

$gwEpLabel = New-Object System.Windows.Forms.Label
$gwEpLabel.Text = 'Gateway PLC endpoint (ADS or OPC UA):'
$gwEpLabel.Location = New-Object System.Drawing.Point(24, 162)
$gwEpLabel.Size = New-Object System.Drawing.Size(600, 20)
$gwEpBox = New-Object System.Windows.Forms.TextBox
$gwEpBox.Text = $localAds.Endpoint
$gwEpBox.Location = New-Object System.Drawing.Point(24, 184)
$gwEpBox.Size = New-Object System.Drawing.Size(600, 24)

$remoteCheck = New-Object System.Windows.Forms.CheckBox
$remoteCheck.Text = if ($proxyAlreadyConfigured) {
  'Secure remote Web HMI is installed (upgrade preserves it)'
} else {
  'Enable secure remote Web HMI (authenticated HTTPS/WSS reverse proxy)'
}
$remoteCheck.Checked = $true
$remoteCheck.Enabled = -not $proxyAlreadyConfigured
$remoteCheck.Location = New-Object System.Drawing.Point(24, 225)
$remoteCheck.Size = New-Object System.Drawing.Size(610, 28)

$originLabel = New-Object System.Windows.Forms.Label
$originLabel.Text = 'Public Web HMI origin (https://<PLC IP or DNS name>[:port]):'
$originLabel.Location = New-Object System.Drawing.Point(44, 260)
$originLabel.Size = New-Object System.Drawing.Size(570, 20)
$originBox = New-Object System.Windows.Forms.TextBox
$originBox.Text = if ($proxyAlreadyConfigured) {
  (Get-Content -LiteralPath $installedProxyOrigin -Raw).Trim()
} else {
  Get-SuggestedPublicOrigin
}
$originBox.Location = New-Object System.Drawing.Point(44, 282)
$originBox.Size = New-Object System.Drawing.Size(570, 24)

$userLabel = New-Object System.Windows.Forms.Label
$userLabel.Text = 'Remote-access username:'
$userLabel.Location = New-Object System.Drawing.Point(44, 317)
$userLabel.Size = New-Object System.Drawing.Size(270, 20)
$userBox = New-Object System.Windows.Forms.TextBox
$userBox.Text = 'fraktal'
$userBox.Location = New-Object System.Drawing.Point(44, 339)
$userBox.Size = New-Object System.Drawing.Size(270, 24)

$passwordLabel = New-Object System.Windows.Forms.Label
$passwordLabel.Text = if ($proxyAlreadyConfigured) {
  'New password (leave blank to preserve):'
} else {
  'Password (minimum 12 characters):'
}
$passwordLabel.Location = New-Object System.Drawing.Point(334, 317)
$passwordLabel.Size = New-Object System.Drawing.Size(280, 20)
$passwordBox = New-Object System.Windows.Forms.TextBox
$passwordBox.UseSystemPasswordChar = $true
$passwordBox.Location = New-Object System.Drawing.Point(334, 339)
$passwordBox.Size = New-Object System.Drawing.Size(280, 24)

$confirmLabel = New-Object System.Windows.Forms.Label
$confirmLabel.Text = 'Confirm password:'
$confirmLabel.Location = New-Object System.Drawing.Point(334, 375)
$confirmLabel.Size = New-Object System.Drawing.Size(280, 20)
$confirmBox = New-Object System.Windows.Forms.TextBox
$confirmBox.UseSystemPasswordChar = $true
$confirmBox.Location = New-Object System.Drawing.Point(334, 397)
$confirmBox.Size = New-Object System.Drawing.Size(280, 24)

$firewallCheck = New-Object System.Windows.Forms.CheckBox
$firewallCheck.Text = 'Allow HTTPS/WSS from the local subnet in Windows Firewall (requires UAC)'
$firewallCheck.Checked = $true
$firewallCheck.Location = New-Object System.Drawing.Point(44, 435)
$firewallCheck.Size = New-Object System.Drawing.Size(570, 28)

$trustCurrentUserCheck = New-Object System.Windows.Forms.CheckBox
$trustCurrentUserCheck.Text = 'Trust this gateway CA for the current Windows user on this PC'
$trustCurrentUserCheck.Checked = $true
$trustCurrentUserCheck.Location = New-Object System.Drawing.Point(44, 465)
$trustCurrentUserCheck.Size = New-Object System.Drawing.Size(570, 28)

$trustNotice = New-Object System.Windows.Forms.Label
$trustNotice.Text = if ($proxyAlreadyConfigured) {
  'Existing proxy security was detected. Blank password fields preserve its account hash and CA. Trust on this PC does not trust remote operator PCs; import the exported public root on each client.'
} else {
  'A private factory-LAN CA is created. This checkbox trusts it only on this Windows account. Import the exported public root on every remote HMI client; the private key stays on the gateway.'
}
$trustNotice.AutoSize = $false
$trustNotice.Location = New-Object System.Drawing.Point(44, 497)
$trustNotice.Size = New-Object System.Drawing.Size(570, 50)

$endpointsPage.Controls.AddRange(@(
  $epIntro, $hmiEpLabel, $hmiEpBox, $adsDetectionLabel,
  $sameEndpointCheck, $gwEpLabel, $gwEpBox,
  $remoteCheck, $originLabel, $originBox, $userLabel, $userBox,
  $passwordLabel, $passwordBox, $confirmLabel, $confirmBox,
  $firewallCheck, $trustCurrentUserCheck, $trustNotice
))

# --- Page 2: progress ---
$progressPage = New-Object System.Windows.Forms.Panel
$progressPage.Dock = 'Fill'
$script:progressBox = New-Object System.Windows.Forms.TextBox
$script:progressBox.Multiline = $true
$script:progressBox.ReadOnly = $true
$script:progressBox.ScrollBars = 'Vertical'
$script:progressBox.Dock = 'Fill'
$script:progressBox.Font = New-Object System.Drawing.Font('Consolas', 9)
$progressPage.Controls.Add($script:progressBox)

# --- Content host + page switching ---
$content = New-Object System.Windows.Forms.Panel
$content.Dock = 'Fill'
$content.Padding = New-Object System.Windows.Forms.Padding(0, 0, 0, 50)
$pages = @($componentsPage, $endpointsPage, $progressPage)
foreach ($p in $pages) { $content.Controls.Add($p) }

$buttonBar = New-Object System.Windows.Forms.Panel
$buttonBar.Dock = 'Bottom'
$buttonBar.Height = 50

$backBtn = New-Object System.Windows.Forms.Button
$backBtn.Text = 'Back'
$backBtn.Size = New-Object System.Drawing.Size(90, 32)
$backBtn.Location = New-Object System.Drawing.Point(310, 9)

$nextBtn = New-Object System.Windows.Forms.Button
$nextBtn.Text = 'Next'
$nextBtn.Size = New-Object System.Drawing.Size(90, 32)
$nextBtn.Location = New-Object System.Drawing.Point(410, 9)

$cancelBtn = New-Object System.Windows.Forms.Button
$cancelBtn.Text = 'Cancel'
$cancelBtn.Size = New-Object System.Drawing.Size(90, 32)
$cancelBtn.Location = New-Object System.Drawing.Point(510, 9)

$buttonBar.Controls.AddRange(@($backBtn, $nextBtn, $cancelBtn))

$form.Controls.Add($content)
$form.Controls.Add($buttonBar)

$script:pageIndex = 0

function Update-RemoteControls {
  $showRemote = $gwCheck.Checked
  $remoteCheck.Visible = $showRemote
  $remoteFields = @(
    $originLabel, $originBox, $userLabel, $userBox,
    $passwordLabel, $passwordBox, $confirmLabel, $confirmBox,
    $firewallCheck, $trustCurrentUserCheck, $trustNotice
  )
  foreach ($control in $remoteFields) {
    $control.Visible = $showRemote
    $control.Enabled = $showRemote -and $remoteCheck.Checked
  }
}

function Update-EndpointControls {
  $shareEndpoint = $gwCheck.Checked -and $sameEndpointCheck.Checked
  if ($shareEndpoint) { $gwEpBox.Text = $hmiEpBox.Text }

  $showHmiEndpoint = $hmiCheck.Checked -or $shareEndpoint
  foreach ($control in @($hmiEpLabel, $hmiEpBox, $adsDetectionLabel)) {
    $control.Visible = $showHmiEndpoint
  }
  $sameEndpointCheck.Visible = $gwCheck.Checked
  $gwEpLabel.Visible = $gwCheck.Checked
  $gwEpBox.Visible = $gwCheck.Checked
  # The shared value is authored once in the HMI/local field. Keeping the
  # derived Gateway box read-only prevents the two persisted endpoints drifting.
  $gwEpBox.Enabled = $gwCheck.Checked -and -not $shareEndpoint
}

function Show-Page([int]$Index) {
  for ($i = 0; $i -lt $pages.Count; $i++) { $pages[$i].Visible = ($i -eq $Index) }
  $script:pageIndex = $Index
  $backBtn.Visible = ($Index -gt 0 -and $Index -lt 2)
  if ($Index -eq 0) {
    $nextBtn.Text = 'Install'
    $nextBtn.Enabled = ($hmiCheck.Checked -or $gwCheck.Checked)
  } elseif ($Index -eq 1) {
    Update-EndpointControls
    Update-RemoteControls
    $nextBtn.Text = 'Install'
    $nextBtn.Enabled = $true
  } else {
    $backBtn.Visible = $false
    $nextBtn.Text = 'Finish'
    $nextBtn.Enabled = $false
    $cancelBtn.Text = 'Close'
  }
}

function Update-ComponentsNext {
  if ($script:pageIndex -eq 0) {
    $nextBtn.Enabled = ($hmiCheck.Checked -or $gwCheck.Checked)
  }
}

$hmiCheck.Add_CheckedChanged({
  Update-ComponentsNext
  Update-EndpointControls
})
$gwCheck.Add_CheckedChanged({
  Update-ComponentsNext
  Update-EndpointControls
  Update-RemoteControls
})
$sameEndpointCheck.Add_CheckedChanged({ Update-EndpointControls })
$hmiEpBox.Add_TextChanged({
  if ($sameEndpointCheck.Checked) { $gwEpBox.Text = $hmiEpBox.Text }
})
$remoteCheck.Add_CheckedChanged({ Update-RemoteControls })

$backBtn.Add_Click({
  if ($script:pageIndex -eq 1) { Show-Page 0 }
})

$nextBtn.Add_Click({
  if ($script:pageIndex -eq 0) {
    Show-Page 1
    return
  }
  if ($script:pageIndex -eq 1) {
    # Validate the visible endpoint fields before installing.
    $sharedGatewayEndpoint = $gwCheck.Checked -and $sameEndpointCheck.Checked
    if (($hmiCheck.Checked -or $sharedGatewayEndpoint) -and
        -not (Test-FraktalEndpoint $hmiEpBox.Text)) {
      [System.Windows.Forms.MessageBox]::Show($form,
        'Enter a valid local PLC endpoint, e.g. ads://192.168.1.6.1.1:851 (six dot-separated parts).',
        'Invalid local PLC endpoint', 0, 48)
      return
    }
    if ($sharedGatewayEndpoint) { $gwEpBox.Text = $hmiEpBox.Text }
    if ($gwCheck.Checked -and -not (Test-FraktalEndpoint $gwEpBox.Text)) {
      [System.Windows.Forms.MessageBox]::Show($form,
        'Enter a valid Gateway PLC endpoint, e.g. opc.tcp://192.168.1.6:4840.',
        'Invalid Gateway endpoint', 0, 48)
      return
    }
    if ($gwCheck.Checked -and $remoteCheck.Checked) {
      if (-not (Test-HttpsOrigin $originBox.Text)) {
        [System.Windows.Forms.MessageBox]::Show($form,
          'Enter only an HTTPS origin, e.g. https://192.168.100.126 or https://hmi-cell-01.example:8443.',
          'Invalid public Web HMI origin', 0, 48)
        return
      }
      if ($userBox.Text -notmatch '^[A-Za-z0-9._-]{1,64}$') {
        [System.Windows.Forms.MessageBox]::Show($form,
          'The remote-access username must contain 1-64 letters, digits, dots, underscores, or hyphens.',
          'Invalid username', 0, 48)
        return
      }
      $preserveExistingPassword = $proxyAlreadyConfigured -and
        [string]::IsNullOrEmpty($passwordBox.Text) -and
        [string]::IsNullOrEmpty($confirmBox.Text)
      if (-not $preserveExistingPassword -and $passwordBox.Text.Length -lt 12) {
        [System.Windows.Forms.MessageBox]::Show($form,
          'Use a remote-access password with at least 12 characters.',
          'Password too short', 0, 48)
        return
      }
      if (-not $preserveExistingPassword -and
          $passwordBox.Text -cne $confirmBox.Text) {
        [System.Windows.Forms.MessageBox]::Show($form,
          'The remote-access passwords do not match.',
          'Password mismatch', 0, 48)
        return
      }
    }
    $selected = @()
    if ($hmiCheck.Checked) { $selected += 'HMI' }
    if ($gwCheck.Checked) { $selected += 'Gateway' }
    Show-Page 2
    $form.Refresh()
    if ($gwCheck.Checked -and
        $remoteCheck.Checked -and
        -not [string]::IsNullOrEmpty($passwordBox.Text)) {
      [Environment]::SetEnvironmentVariable(
        'FRAKTAL_PROXY_PASSWORD',
        $passwordBox.Text,
        [EnvironmentVariableTarget]::Process
      )
    }
    try {
      $script:installOk = Run-SelectedInstalls `
        $selected `
        $hmiEpBox.Text `
        $gwEpBox.Text `
        ($gwCheck.Checked -and $remoteCheck.Checked) `
        $originBox.Text `
        $userBox.Text `
        $firewallCheck.Checked `
        $trustCurrentUserCheck.Checked
    } finally {
      [Environment]::SetEnvironmentVariable(
        'FRAKTAL_PROXY_PASSWORD',
        $null,
        [EnvironmentVariableTarget]::Process
      )
      $passwordBox.Clear()
      $confirmBox.Clear()
    }
    $nextBtn.Enabled = $true
    return
  }
  if ($script:pageIndex -eq 2) { $form.Close() }
})

$cancelBtn.Add_Click({
  if ($script:pageIndex -eq 2) { $form.DialogResult = [System.Windows.Forms.DialogResult]::OK; $form.Close() }
  else { $form.Close() }
})

$form.Add_Load({ Show-Page 0 })
[void]$form.ShowDialog()
