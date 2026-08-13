param(
  # Silent mode: when Components is bound the UI is skipped and the listed
  # components are installed with the supplied endpoints. Escape hatch for
  # Group-Policy/AppLocker hosts where the WinForms UI cannot run, and for
  # scripted deployment.
  [ValidateSet('HMI', 'Gateway', IgnoreCase = $true)]
  [string[]]$Components,
  [string]$HmiEndpoint,
  # Single-gateway shorthand. One gateway process serves one PLC.
  [string]$GatewayEndpoint,
  # One gateway instance per PLC, repeatable. Each value is a spec:
  #   name=<label>;endpoint=<uri>;port=<loopback port>;origin=<https://host[:port]>
  #   ;writeroot=<root Unit path[,root Unit path...]>
  # Only endpoint is required; name defaults to 'default' then instance2,
  # instance3, …, and port to 8080, 8081, ….
  [string[]]$GatewayInstance,
  # The published root Unit path(s) the BROWSER may command, comma-separated.
  # Omitted = a read-only viewer: the Web HMI displays everything the PLC
  # publishes and the gateway refuses every operator command before it reaches
  # the PLC. Shape follows the gateway's transport - `PneumaticPress` over ADS,
  # `PLC1/MAIN/PneumaticPress` over OPC UA. The native HMI is unaffected, and
  # the PLC re-checks its own release/access gates either way.
  [string]$WriteRoot,
  [switch]$EnableRemoteAccess,
  [string]$PublicOrigin,
  [string]$ProxyUsername = 'fraktal',
  [switch]$ConfigureFirewall,
  [switch]$TrustProxyCaForCurrentUser
)

. (Join-Path $PSScriptRoot 'fraktal_instances.ps1')

# Runs one component's install script synchronously (IExpress deletes the extract
# dir when this wizard exits, so installs must complete before return) and
# returns $true on success. [string]$Output collects a one-line result.
function Invoke-ComponentInstall(
  [string]$Name,
  [string]$Script,
  [string]$Detail,
  [string[]]$Arguments
) {
  $scriptPath = Join-Path $PSScriptRoot $Script
  if (-not (Test-Path -LiteralPath $scriptPath)) {
    Write-WizardLog "[$Name] install script missing: $scriptPath"
    return $false
  }
  Write-WizardLog "[$Name] installing ($Detail) ..."
  # The child runs hidden, so WITHOUT capturing its streams a stall here is
  # invisible: the wizard just sits on "installing ..." forever with no clue
  # which step is blocking. Redirect to files (not pipes — a full pipe buffer
  # would deadlock a hidden child that nobody is draining) and replay them into
  # the wizard log, so the install script's own progress markers are visible.
  #
  # -Unattended stops the child opening Notepad, which would block this wait
  # behind an invisible window.
  $childArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath,
    '-Unattended')
  $childArgs += $Arguments
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
  [object[]]$Instances,
  [bool]$RemoteAccess,
  [string]$RemoteUsername,
  [bool]$OpenFirewall,
  [bool]$TrustLocalProxyCa
) {
  $script:LogLines.Clear()
  $ok = $true
  foreach ($comp in $Selected) {
    if ($comp -eq 'HMI') {
      if (-not (Test-FraktalEndpoint $Hmi)) { Write-WizardLog '[HMI] invalid endpoint.'; $ok = $false; continue }
      $ok = (Invoke-ComponentInstall 'HMI' 'install_hmi.ps1' $Hmi @('-Endpoint', $Hmi)) -and $ok
    } elseif ($comp -eq 'Gateway') {
      $problem = Get-FraktalInstanceSetError $Instances
      if ($problem) { Write-WizardLog "[Gateway] $problem"; $ok = $false; continue }
      if ($RemoteAccess -and $RemoteUsername -notmatch '^[A-Za-z0-9._-]{1,64}$') {
        Write-WizardLog '[Gateway] invalid remote-access username.'
        $ok = $false
        continue
      }
      # The instance set is handed over as a file: a name, a URI, and an origin
      # per instance do not survive nested PowerShell quoting reliably.
      $instancesFile = Join-Path $env:TEMP `
        ('fraktal-instances-' + [guid]::NewGuid().ToString('N') + '.json')
      Write-FraktalInstancesFile $instancesFile $Instances
      try {
        $extra = @('-InstancesFile', $instancesFile)
        if ($RemoteAccess) {
          $extra += @('-EnableRemoteAccess', '-ProxyUsername', $RemoteUsername)
          if ($OpenFirewall) { $extra += '-ConfigureFirewall' }
          if ($TrustLocalProxyCa) { $extra += '-TrustProxyCaForCurrentUser' }
        }
        $detail = ($Instances | ForEach-Object { "$($_.Name)=$($_.Endpoint)@$($_.Port)" }) -join ', '
        $ok = (Invoke-ComponentInstall 'Gateway' 'install_gateway.ps1' $detail $extra) -and $ok
      } finally {
        Remove-Item -LiteralPath $instancesFile -Force -ErrorAction SilentlyContinue
      }
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
  $instances = @()
  if ($GatewayInstance) {
    $index = 0
    foreach ($spec in $GatewayInstance) {
      $fields = @{}
      foreach ($pair in ($spec -split ';')) {
        if (-not $pair.Trim()) { continue }
        $parts = $pair.Split('=', 2)
        if ($parts.Count -ne 2) {
          [Console]::Error.WriteLine("Malformed -GatewayInstance field: $pair")
          exit 2
        }
        $fields[$parts[0].Trim().ToLowerInvariant()] = $parts[1].Trim()
      }
      $name = if ($fields.ContainsKey('name')) {
        $fields['name']
      } elseif ($index -eq 0) {
        'default'
      } else {
        "instance$($index + 1)"
      }
      $port = 8080 + $index
      if ($fields.ContainsKey('port')) { $port = [int]$fields['port'] }
      $endpoint = if ($fields.ContainsKey('endpoint')) { $fields['endpoint'] } else { $HmiEndpoint }
      $origin = if ($fields.ContainsKey('origin')) { $fields['origin'] } else { '' }
      # writeroot= is what makes the instance commandable; omitting it installs
      # a read-only viewer, exactly as clearing the wizard's checkbox does.
      $roots = if ($fields.ContainsKey('writeroot')) {
        ConvertTo-FraktalBrowseRoots $fields['writeroot']
      } else {
        @()
      }
      $instances += (New-FraktalInstance $name $endpoint $port $origin $roots)
      $index++
    }
  } else {
    if (-not $GatewayEndpoint) { $GatewayEndpoint = $HmiEndpoint }
    $instances = @(New-FraktalInstance 'default' $GatewayEndpoint 8080 $PublicOrigin `
      (ConvertTo-FraktalBrowseRoots $WriteRoot))
  }
  if ($EnableRemoteAccess -and
      -not (@($instances | Where-Object { $_.PublicOrigin }).Count)) {
    [Console]::Error.WriteLine('-PublicOrigin (or an origin= field) is required with -EnableRemoteAccess.')
    exit 2
  }
  $ok = Run-SelectedInstalls $Components $HmiEndpoint $instances `
    $EnableRemoteAccess.IsPresent $ProxyUsername `
    $ConfigureFirewall.IsPresent $TrustProxyCaForCurrentUser.IsPresent
  if (-not $ok) { exit 1 }
  exit 0
}

# ---- WinForms wizard -------------------------------------------------------
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$installedProxyConfig = Join-Path (Get-FraktalDataRoot) 'proxy\Caddyfile'
$proxyAlreadyConfigured = Test-Path -LiteralPath $installedProxyConfig
$localAds = Get-LocalAdsEndpoint

# Prefill from the installation on this PC when there is one, so an upgrade
# never asks the operator to retype a working instance set.
$script:instances = New-Object System.Collections.Generic.List[object]
foreach ($installed in (Get-FraktalInstances)) {
  $script:instances.Add((New-FraktalInstance `
    $installed.Name $installed.Endpoint $installed.Port $installed.PublicOrigin `
    $installed.WriteRoots)) | Out-Null
}
if ($script:instances.Count -eq 0) {
  $script:instances.Add((New-FraktalInstance `
    'default' $localAds.Endpoint 8080 (Get-SuggestedPublicOrigin))) | Out-Null
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Fraktal Setup'
$form.Size = New-Object System.Drawing.Size(720, 780)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

# --- Page 0: component selection ---
$componentsPage = New-Object System.Windows.Forms.Panel
$componentsPage.Dock = 'Fill'
$intro = New-Object System.Windows.Forms.Label
$intro.Text = "Choose the Fraktal components to install. Select at least one.`r`n`r`nThe native HMI and Gateway can share the same local ADS connection to the PLC. The Gateway serves the browser-based Web HMI, and can run one instance per PLC on this host."
$intro.AutoSize = $false
$intro.Size = New-Object System.Drawing.Size(650, 100)
$intro.Location = New-Object System.Drawing.Point(20, 15)

$hmiCheck = New-Object System.Windows.Forms.CheckBox
$hmiCheck.Text = 'Fraktal HMI  (native desktop app, ADS direct to PLC)'
$hmiCheck.Location = New-Object System.Drawing.Point(24, 125)
$hmiCheck.Size = New-Object System.Drawing.Size(620, 30)

$gwCheck = New-Object System.Windows.Forms.CheckBox
$gwCheck.Text = 'Fraktal Gateway + Web HMI  (browser access via ADS or OPC UA)'
$gwCheck.Location = New-Object System.Drawing.Point(24, 160)
$gwCheck.Size = New-Object System.Drawing.Size(620, 30)

$componentsPage.Controls.AddRange(@($intro, $hmiCheck, $gwCheck))

# --- Page 1: endpoints and gateway instances ---
$endpointsPage = New-Object System.Windows.Forms.Panel
$endpointsPage.Dock = 'Fill'
$epIntro = New-Object System.Windows.Forms.Label
$epIntro.Text = 'Configure the PLC endpoint for each selected component.'
$epIntro.AutoSize = $false
$epIntro.Size = New-Object System.Drawing.Size(650, 30)
$epIntro.Location = New-Object System.Drawing.Point(20, 12)

$hmiEpLabel = New-Object System.Windows.Forms.Label
$hmiEpLabel.Text = 'HMI / local PLC endpoint (ads://<AmsNetId>:<port>):'
$hmiEpLabel.Location = New-Object System.Drawing.Point(24, 44)
$hmiEpLabel.Size = New-Object System.Drawing.Size(640, 20)
$hmiEpBox = New-Object System.Windows.Forms.TextBox
$hmiEpBox.Text = $localAds.Endpoint
$hmiEpBox.Location = New-Object System.Drawing.Point(24, 66)
$hmiEpBox.Size = New-Object System.Drawing.Size(640, 24)

$adsDetectionLabel = New-Object System.Windows.Forms.Label
$adsDetectionLabel.Text = $localAds.Detail
$adsDetectionLabel.ForeColor = if ($localAds.Detected) {
  [System.Drawing.Color]::DarkGreen
} else {
  [System.Drawing.Color]::DarkOrange
}
$adsDetectionLabel.Location = New-Object System.Drawing.Point(24, 94)
$adsDetectionLabel.Size = New-Object System.Drawing.Size(640, 20)

$sameEndpointCheck = New-Object System.Windows.Forms.CheckBox
$sameEndpointCheck.Text = 'Use the HMI / local PLC endpoint for the first Gateway instance'
$sameEndpointCheck.Checked = $true
$sameEndpointCheck.Location = New-Object System.Drawing.Point(24, 118)
$sameEndpointCheck.Size = New-Object System.Drawing.Size(640, 26)

$instancesLabel = New-Object System.Windows.Forms.Label
$instancesLabel.Text = 'Gateway instances — one per PLC. Each instance owns its own loopback port, and its own public HTTPS origin when remote access is enabled.'
$instancesLabel.AutoSize = $false
$instancesLabel.Location = New-Object System.Drawing.Point(24, 146)
$instancesLabel.Size = New-Object System.Drawing.Size(640, 34)

$instancesList = New-Object System.Windows.Forms.ListView
$instancesList.View = 'Details'
$instancesList.FullRowSelect = $true
$instancesList.MultiSelect = $false
$instancesList.HideSelection = $false
$instancesList.Location = New-Object System.Drawing.Point(24, 180)
$instancesList.Size = New-Object System.Drawing.Size(640, 124)
$instancesList.Columns.Add('Instance', 92) | Out-Null
$instancesList.Columns.Add('PLC endpoint', 186) | Out-Null
$instancesList.Columns.Add('Port', 48) | Out-Null
$instancesList.Columns.Add('Public HTTPS origin', 168) | Out-Null
$instancesList.Columns.Add('Commands', 140) | Out-Null

$addButton = New-Object System.Windows.Forms.Button
$addButton.Text = 'Add PLC...'
$addButton.Location = New-Object System.Drawing.Point(24, 310)
$addButton.Size = New-Object System.Drawing.Size(110, 28)

$editButton = New-Object System.Windows.Forms.Button
$editButton.Text = 'Edit...'
$editButton.Location = New-Object System.Drawing.Point(142, 310)
$editButton.Size = New-Object System.Drawing.Size(110, 28)

$removeButton = New-Object System.Windows.Forms.Button
$removeButton.Text = 'Remove'
$removeButton.Location = New-Object System.Drawing.Point(260, 310)
$removeButton.Size = New-Object System.Drawing.Size(110, 28)

$remoteCheck = New-Object System.Windows.Forms.CheckBox
$remoteCheck.Text = if ($proxyAlreadyConfigured) {
  'Secure remote Web HMI is installed (upgrade preserves it)'
} else {
  'Enable secure remote Web HMI (authenticated HTTPS/WSS reverse proxy)'
}
$remoteCheck.Checked = $true
$remoteCheck.Enabled = -not $proxyAlreadyConfigured
$remoteCheck.Location = New-Object System.Drawing.Point(24, 348)
$remoteCheck.Size = New-Object System.Drawing.Size(640, 26)

$accountLabel = New-Object System.Windows.Forms.Label
$accountLabel.Text = 'One browser account serves every published instance.'
$accountLabel.Location = New-Object System.Drawing.Point(44, 376)
$accountLabel.Size = New-Object System.Drawing.Size(600, 20)

$userLabel = New-Object System.Windows.Forms.Label
$userLabel.Text = 'Remote-access username:'
$userLabel.Location = New-Object System.Drawing.Point(44, 400)
$userLabel.Size = New-Object System.Drawing.Size(270, 20)
$userBox = New-Object System.Windows.Forms.TextBox
$userBox.Text = 'fraktal'
$userBox.Location = New-Object System.Drawing.Point(44, 422)
$userBox.Size = New-Object System.Drawing.Size(270, 24)

$passwordLabel = New-Object System.Windows.Forms.Label
$passwordLabel.Text = if ($proxyAlreadyConfigured) {
  'New password (leave blank to preserve):'
} else {
  'Password (minimum 12 characters):'
}
$passwordLabel.Location = New-Object System.Drawing.Point(354, 400)
$passwordLabel.Size = New-Object System.Drawing.Size(290, 20)
$passwordBox = New-Object System.Windows.Forms.TextBox
$passwordBox.UseSystemPasswordChar = $true
$passwordBox.Location = New-Object System.Drawing.Point(354, 422)
$passwordBox.Size = New-Object System.Drawing.Size(290, 24)

$confirmLabel = New-Object System.Windows.Forms.Label
$confirmLabel.Text = 'Confirm password:'
$confirmLabel.Location = New-Object System.Drawing.Point(354, 450)
$confirmLabel.Size = New-Object System.Drawing.Size(290, 20)
$confirmBox = New-Object System.Windows.Forms.TextBox
$confirmBox.UseSystemPasswordChar = $true
$confirmBox.Location = New-Object System.Drawing.Point(354, 472)
$confirmBox.Size = New-Object System.Drawing.Size(290, 24)

$firewallCheck = New-Object System.Windows.Forms.CheckBox
$firewallCheck.Text = 'Allow HTTPS/WSS from the local subnet in Windows Firewall (requires UAC)'
$firewallCheck.Checked = $true
$firewallCheck.Location = New-Object System.Drawing.Point(44, 504)
$firewallCheck.Size = New-Object System.Drawing.Size(600, 26)

$trustCurrentUserCheck = New-Object System.Windows.Forms.CheckBox
$trustCurrentUserCheck.Text = 'Trust this gateway CA for the current Windows user on this PC'
$trustCurrentUserCheck.Checked = $true
$trustCurrentUserCheck.Location = New-Object System.Drawing.Point(44, 532)
$trustCurrentUserCheck.Size = New-Object System.Drawing.Size(600, 26)

$trustNotice = New-Object System.Windows.Forms.Label
$trustNotice.Text = if ($proxyAlreadyConfigured) {
  'Existing proxy security was detected. Blank password fields preserve its account hash and CA. Trust on this PC does not trust remote operator PCs; import the exported public root on each client.'
} else {
  'A private factory-LAN CA is created. This checkbox trusts it only on this Windows account. Import the exported public root on every remote HMI client; the private key stays on the gateway.'
}
$trustNotice.AutoSize = $false
$trustNotice.Location = New-Object System.Drawing.Point(44, 562)
$trustNotice.Size = New-Object System.Drawing.Size(600, 60)

$endpointsPage.Controls.AddRange(@(
  $epIntro, $hmiEpLabel, $hmiEpBox, $adsDetectionLabel, $sameEndpointCheck,
  $instancesLabel, $instancesList, $addButton, $editButton, $removeButton,
  $remoteCheck, $accountLabel, $userLabel, $userBox,
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
$backBtn.Location = New-Object System.Drawing.Point(350, 9)

$nextBtn = New-Object System.Windows.Forms.Button
$nextBtn.Text = 'Next'
$nextBtn.Size = New-Object System.Drawing.Size(90, 32)
$nextBtn.Location = New-Object System.Drawing.Point(450, 9)

$cancelBtn = New-Object System.Windows.Forms.Button
$cancelBtn.Text = 'Cancel'
$cancelBtn.Size = New-Object System.Drawing.Size(90, 32)
$cancelBtn.Location = New-Object System.Drawing.Point(550, 9)

$buttonBar.Controls.AddRange(@($backBtn, $nextBtn, $cancelBtn))

$form.Controls.Add($content)
$form.Controls.Add($buttonBar)

$script:pageIndex = 0

# A modal editor for one instance. Returns the edited copy, or $null on cancel,
# so the caller decides whether to commit it to the list.
function Show-InstanceDialog(
  [string]$Title,
  [object]$Instance,
  [bool]$LockEndpoint
) {
  $dialog = New-Object System.Windows.Forms.Form
  $dialog.Text = $Title
  $dialog.Size = New-Object System.Drawing.Size(520, 415)
  $dialog.StartPosition = 'CenterParent'
  $dialog.FormBorderStyle = 'FixedDialog'
  $dialog.MaximizeBox = $false
  $dialog.MinimizeBox = $false

  $nameLabel = New-Object System.Windows.Forms.Label
  $nameLabel.Text = 'Instance name (folder + log):'
  $nameLabel.Location = New-Object System.Drawing.Point(16, 14)
  $nameLabel.Size = New-Object System.Drawing.Size(210, 20)
  $nameBox = New-Object System.Windows.Forms.TextBox
  $nameBox.Text = $Instance.Name
  $nameBox.Location = New-Object System.Drawing.Point(16, 36)
  $nameBox.Size = New-Object System.Drawing.Size(200, 24)

  $portLabel = New-Object System.Windows.Forms.Label
  $portLabel.Text = 'Loopback port:'
  $portLabel.Location = New-Object System.Drawing.Point(260, 14)
  $portLabel.Size = New-Object System.Drawing.Size(226, 20)
  $portBox = New-Object System.Windows.Forms.TextBox
  $portBox.Text = "$($Instance.Port)"
  $portBox.Location = New-Object System.Drawing.Point(260, 36)
  $portBox.Size = New-Object System.Drawing.Size(100, 24)

  $endpointLabel = New-Object System.Windows.Forms.Label
  $endpointLabel.Text = if ($LockEndpoint) {
    'PLC endpoint (shared with the HMI / local endpoint):'
  } else {
    'PLC endpoint (ads://<AmsNetId>:851 or opc.tcp://<host>:4840):'
  }
  $endpointLabel.Location = New-Object System.Drawing.Point(16, 72)
  $endpointLabel.Size = New-Object System.Drawing.Size(470, 20)
  $endpointBox = New-Object System.Windows.Forms.TextBox
  $endpointBox.Text = $Instance.Endpoint
  $endpointBox.Enabled = -not $LockEndpoint
  $endpointBox.Location = New-Object System.Drawing.Point(16, 94)
  $endpointBox.Size = New-Object System.Drawing.Size(470, 24)

  $originLabel = New-Object System.Windows.Forms.Label
  $originLabel.Text = 'Public Web HMI origin (https://<host>[:port]; blank = local only):'
  $originLabel.Location = New-Object System.Drawing.Point(16, 130)
  $originLabel.Size = New-Object System.Drawing.Size(470, 20)
  $originBox = New-Object System.Windows.Forms.TextBox
  $originBox.Text = $Instance.PublicOrigin
  $originBox.Location = New-Object System.Drawing.Point(16, 152)
  $originBox.Size = New-Object System.Drawing.Size(470, 24)

  # The web path's command scope. Deliberately an explicit choice rather than a
  # blank field with a default: an instance with no scope is a viewer, and
  # discovering that from "every command is refused" at commissioning time is
  # exactly the failure this dialog exists to prevent.
  $commandCheck = New-Object System.Windows.Forms.CheckBox
  $commandCheck.Text = 'Allow operator commands from the browser'
  $commandCheck.Checked = (@($Instance.WriteRoots).Count -gt 0)
  $commandCheck.Location = New-Object System.Drawing.Point(16, 186)
  $commandCheck.Size = New-Object System.Drawing.Size(470, 24)

  $rootLabel = New-Object System.Windows.Forms.Label
  $rootLabel.Text = 'Commandable root Unit path(s), comma-separated:'
  $rootLabel.Location = New-Object System.Drawing.Point(36, 212)
  $rootLabel.Size = New-Object System.Drawing.Size(450, 20)
  $rootBox = New-Object System.Windows.Forms.TextBox
  $rootBox.Text = (@($Instance.WriteRoots) -join ', ')
  $rootBox.Location = New-Object System.Drawing.Point(36, 234)
  $rootBox.Size = New-Object System.Drawing.Size(450, 24)

  $hint = New-Object System.Windows.Forms.Label
  $hint.Text = 'Each instance needs its own port and origin (the Web HMI derives its WebSocket endpoint from the page origin). The command scope is the published root Unit: PneumaticPress over ADS, PLC1/MAIN/PneumaticPress over OPC UA. Unchecked = the browser displays but cannot command; the PLC still applies its own release and access gates either way.'
  $hint.AutoSize = $false
  $hint.Location = New-Object System.Drawing.Point(16, 264)
  $hint.Size = New-Object System.Drawing.Size(470, 62)

  $okBtn = New-Object System.Windows.Forms.Button
  $okBtn.Text = 'OK'
  $okBtn.Size = New-Object System.Drawing.Size(90, 30)
  $okBtn.Location = New-Object System.Drawing.Point(286, 330)
  $cancelDialogBtn = New-Object System.Windows.Forms.Button
  $cancelDialogBtn.Text = 'Cancel'
  $cancelDialogBtn.Size = New-Object System.Drawing.Size(90, 30)
  $cancelDialogBtn.Location = New-Object System.Drawing.Point(386, 330)
  $cancelDialogBtn.DialogResult = [System.Windows.Forms.DialogResult]::Cancel

  $syncCommandFields = {
    $rootLabel.Enabled = $commandCheck.Checked
    $rootBox.Enabled = $commandCheck.Checked
  }
  $commandCheck.Add_CheckedChanged($syncCommandFields)
  & $syncCommandFields

  $okBtn.Add_Click({
    if (-not (Test-FraktalInstanceName $nameBox.Text)) {
      [System.Windows.Forms.MessageBox]::Show($dialog,
        'The instance name must be 1-32 letters, digits, dots, underscores, or hyphens.',
        'Invalid instance name', 0, 48)
      return
    }
    if (-not (Test-FraktalEndpoint $endpointBox.Text)) {
      [System.Windows.Forms.MessageBox]::Show($dialog,
        'Enter a valid PLC endpoint, e.g. ads://192.168.1.6.1.1:851 (six dot-separated parts) or opc.tcp://192.168.1.6:4840.',
        'Invalid PLC endpoint', 0, 48)
      return
    }
    $parsedPort = 0
    if (-not [int]::TryParse($portBox.Text.Trim(), [ref]$parsedPort) -or
        $parsedPort -lt 1 -or $parsedPort -gt 65535) {
      [System.Windows.Forms.MessageBox]::Show($dialog,
        'Enter a loopback port between 1 and 65535, e.g. 8080.',
        'Invalid port', 0, 48)
      return
    }
    if ($originBox.Text.Trim() -and -not (Test-HttpsOrigin $originBox.Text)) {
      [System.Windows.Forms.MessageBox]::Show($dialog,
        'Enter only an HTTPS origin, e.g. https://192.168.100.126 or https://hmi-cell-01.example:8443 — or leave it blank for a local-only instance.',
        'Invalid public Web HMI origin', 0, 48)
      return
    }
    if ($commandCheck.Checked) {
      $roots = ConvertTo-FraktalBrowseRoots $rootBox.Text
      if ($roots.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show($dialog,
          'Enter the published root Unit path this instance may command, e.g. PneumaticPress over ADS or PLC1/MAIN/PneumaticPress over OPC UA — or clear the checkbox to install a read-only viewer.',
          'Command scope required', 0, 48)
        return
      }
      foreach ($root in $roots) {
        if (Test-FraktalBrowseRoot $root) { continue }
        [System.Windows.Forms.MessageBox]::Show($dialog,
          "'$root' is not a valid browse path. Use the published root Unit path, with '/' between segments and no empty, '.' or '..' segment.",
          'Invalid command scope', 0, 48)
        return
      }
    }
    $dialog.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $dialog.Close()
  })

  $dialog.Controls.AddRange(@(
    $nameLabel, $nameBox, $portLabel, $portBox,
    $endpointLabel, $endpointBox, $originLabel, $originBox,
    $commandCheck, $rootLabel, $rootBox, $hint,
    $okBtn, $cancelDialogBtn
  ))
  $dialog.AcceptButton = $okBtn
  $dialog.CancelButton = $cancelDialogBtn
  $result = $dialog.ShowDialog($form)
  if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
    $dialog.Dispose()
    return $null
  }
  $port = 0
  [void][int]::TryParse($portBox.Text.Trim(), [ref]$port)
  $roots = if ($commandCheck.Checked) {
    ConvertTo-FraktalBrowseRoots $rootBox.Text
  } else {
    @()
  }
  $edited = New-FraktalInstance `
    $nameBox.Text.Trim() $endpointBox.Text.Trim() $port $originBox.Text.Trim() $roots
  $dialog.Dispose()
  return $edited
}

function Update-InstanceList {
  $selected = if ($instancesList.SelectedIndices.Count -gt 0) {
    $instancesList.SelectedIndices[0]
  } else {
    -1
  }
  $instancesList.BeginUpdate()
  $instancesList.Items.Clear()
  foreach ($instance in $script:instances) {
    $item = New-Object System.Windows.Forms.ListViewItem($instance.Name)
    $item.SubItems.Add($instance.Endpoint) | Out-Null
    $item.SubItems.Add("$($instance.Port)") | Out-Null
    $item.SubItems.Add($(if ($instance.PublicOrigin) { $instance.PublicOrigin } else { '(local only)' })) | Out-Null
    $roots = @($instance.WriteRoots | Where-Object { $_ })
    $item.SubItems.Add($(if ($roots.Count -gt 0) { $roots -join ', ' } else { 'READ-ONLY' })) | Out-Null
    if ($roots.Count -eq 0) {
      # Visible at a glance: a viewer is a legitimate choice, but it must never
      # be a surprise discovered when the first operator command is refused.
      $item.UseItemStyleForSubItems = $false
      $item.SubItems[4].ForeColor = [System.Drawing.Color]::DarkOrange
    }
    $instancesList.Items.Add($item) | Out-Null
  }
  $instancesList.EndUpdate()
  if ($instancesList.Items.Count -gt 0) {
    $index = [Math]::Min([Math]::Max($selected, 0), $instancesList.Items.Count - 1)
    $instancesList.Items[$index].Selected = $true
  }
  $removeButton.Enabled = $instancesList.Items.Count -gt 1
  $addButton.Enabled = $instancesList.Items.Count -lt $FraktalMaxInstances
}

function Update-RemoteControls {
  $showRemote = $gwCheck.Checked
  $remoteCheck.Visible = $showRemote
  $remoteFields = @(
    $accountLabel, $userLabel, $userBox,
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
  # The shared value is authored once in the HMI/local field, so the first
  # instance follows it and the two persisted endpoints cannot drift.
  if ($shareEndpoint -and $script:instances.Count -gt 0) {
    $script:instances[0].Endpoint = $hmiEpBox.Text.Trim()
    Update-InstanceList
  }

  $showHmiEndpoint = $hmiCheck.Checked -or $shareEndpoint
  foreach ($control in @($hmiEpLabel, $hmiEpBox, $adsDetectionLabel)) {
    $control.Visible = $showHmiEndpoint
  }
  $sameEndpointCheck.Visible = $gwCheck.Checked
  foreach ($control in @($instancesLabel, $instancesList, $addButton, $editButton, $removeButton)) {
    $control.Visible = $gwCheck.Checked
  }
}

function Show-Page([int]$Index) {
  for ($i = 0; $i -lt $pages.Count; $i++) { $pages[$i].Visible = ($i -eq $Index) }
  $script:pageIndex = $Index
  $backBtn.Visible = ($Index -gt 0 -and $Index -lt 2)
  if ($Index -eq 0) {
    $nextBtn.Text = 'Next'
    $nextBtn.Enabled = ($hmiCheck.Checked -or $gwCheck.Checked)
  } elseif ($Index -eq 1) {
    Update-InstanceList
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
  if ($sameEndpointCheck.Checked -and $script:instances.Count -gt 0) {
    $script:instances[0].Endpoint = $hmiEpBox.Text.Trim()
    Update-InstanceList
  }
})
$remoteCheck.Add_CheckedChanged({ Update-RemoteControls })

$addButton.Add_Click({
  $usedPorts = @($script:instances)
  $suggestedPort = Get-FraktalNextFreePort $usedPorts
  $suggestedName = "instance$($script:instances.Count + 1)"
  $candidate = New-FraktalInstance $suggestedName '' $suggestedPort `
    (Get-SuggestedPublicOrigin (8442 + $script:instances.Count))
  $added = Show-InstanceDialog 'Add a PLC' $candidate $false
  if ($null -eq $added) { return }
  $script:instances.Add($added) | Out-Null
  Update-InstanceList
})

$editButton.Add_Click({
  if ($instancesList.SelectedIndices.Count -eq 0) { return }
  $index = $instancesList.SelectedIndices[0]
  $lockEndpoint = ($index -eq 0) -and $sameEndpointCheck.Checked
  $edited = Show-InstanceDialog 'Edit a PLC' $script:instances[$index] $lockEndpoint
  if ($null -eq $edited) { return }
  $script:instances[$index] = $edited
  if ($lockEndpoint) { $hmiEpBox.Text = $edited.Endpoint }
  Update-InstanceList
})

$removeButton.Add_Click({
  if ($instancesList.SelectedIndices.Count -eq 0) { return }
  if ($script:instances.Count -le 1) { return }
  $index = $instancesList.SelectedIndices[0]
  $name = $script:instances[$index].Name
  $answer = [System.Windows.Forms.MessageBox]::Show($form,
    "Remove the gateway instance '$name'? Its arguments file is kept as gateway.args.removed, so nothing is lost, but the tray stops serving that PLC.",
    'Remove instance', 4, 32)
  if ($answer -ne [System.Windows.Forms.DialogResult]::Yes) { return }
  $script:instances.RemoveAt($index)
  Update-InstanceList
})

$instancesList.Add_DoubleClick({ $editButton.PerformClick() })

$backBtn.Add_Click({
  if ($script:pageIndex -eq 1) { Show-Page 0 }
})

$nextBtn.Add_Click({
  if ($script:pageIndex -eq 0) {
    Show-Page 1
    return
  }
  if ($script:pageIndex -eq 1) {
    # Validate the visible fields before installing.
    $sharedGatewayEndpoint = $gwCheck.Checked -and $sameEndpointCheck.Checked
    if (($hmiCheck.Checked -or $sharedGatewayEndpoint) -and
        -not (Test-FraktalEndpoint $hmiEpBox.Text)) {
      [System.Windows.Forms.MessageBox]::Show($form,
        'Enter a valid local PLC endpoint, e.g. ads://192.168.1.6.1.1:851 (six dot-separated parts).',
        'Invalid local PLC endpoint', 0, 48)
      return
    }
    if ($sharedGatewayEndpoint -and $script:instances.Count -gt 0) {
      $script:instances[0].Endpoint = $hmiEpBox.Text.Trim()
    }
    if ($gwCheck.Checked) {
      $problem = Get-FraktalInstanceSetError $script:instances
      if ($problem) {
        [System.Windows.Forms.MessageBox]::Show($form, $problem,
          'Gateway instances', 0, 48)
        return
      }
    }
    if ($gwCheck.Checked -and $remoteCheck.Checked) {
      $published = @($script:instances | Where-Object { $_.PublicOrigin })
      if ($published.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show($form,
          'Secure remote access is enabled but no instance has a public HTTPS origin. Give at least one instance an origin, or clear the remote-access option.',
          'No published instance', 0, 48)
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
    if ($gwCheck.Checked) {
      # A read-only instance is a supported choice, not an error — but it is
      # confirmed, because the alternative is finding out at commissioning when
      # every operator command is refused with no obvious cause.
      $viewers = @($script:instances |
        Where-Object { @($_.WriteRoots | Where-Object { $_ }).Count -eq 0 })
      if ($viewers.Count -gt 0) {
        $names = ($viewers | ForEach-Object { $_.Name }) -join ', '
        $answer = [System.Windows.Forms.MessageBox]::Show($form,
          "These gateway instances will be READ-ONLY: $names`r`n`r`nThe browser will display everything the PLC publishes, but every operator command - mode changes, start/stop, manual commands - will be refused by the gateway before it reaches the PLC. The native HMI is unaffected.`r`n`r`nInstall them as read-only viewers?",
          'Read-only instances', 4, 32)
        if ($answer -ne [System.Windows.Forms.DialogResult]::Yes) { return }
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
        $script:instances.ToArray() `
        ($gwCheck.Checked -and $remoteCheck.Checked) `
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
