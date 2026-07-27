param(
  # Silent mode: when Components is bound the UI is skipped and the listed
  # components are installed with the supplied endpoints. Escape hatch for
  # Group-Policy/AppLocker hosts where the WinForms UI cannot run, and for
  # scripted deployment.
  [ValidateSet('HMI', 'Gateway', IgnoreCase = $true)]
  [string[]]$Components,
  [string]$HmiEndpoint,
  [string]$GatewayEndpoint
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

# Runs one component's install script synchronously (IExpress deletes the extract
# dir when this wizard exits, so installs must complete before return) and
# returns $true on success. [string]$Output collects a one-line result.
function Invoke-ComponentInstall([string]$Name, [string]$Script, [string]$Endpoint) {
  $scriptPath = Join-Path $PSScriptRoot $Script
  if (-not (Test-Path -LiteralPath $scriptPath)) {
    Write-WizardLog "[$Name] install script missing: $scriptPath"
    return $false
  }
  Write-WizardLog "[$Name] installing ($Endpoint) ..."
  # -Unattended stops the child from opening Notepad/other interactive windows:
  # Start-Process -Wait waits on the whole child process tree, so an editor left
  # open would freeze the wizard (Close/Finish unresponsive) until it was closed.
  # -WindowStyle Hidden (not -NoNewWindow) keeps the child off the wizard's
  # console handles, which is the other way -Wait can appear to hang.
  $childArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath,
    '-Endpoint', $Endpoint, '-Unattended')
  $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $childArgs `
    -Wait -PassThru -WindowStyle Hidden
  if ($proc.ExitCode -eq 0) {
    Write-WizardLog "[$Name] done."
    return $true
  }
  Write-WizardLog "[$Name] FAILED (exit $($proc.ExitCode))."
  return $false
}

$script:LogLines = New-Object System.Collections.Generic.List[string]
function Write-WizardLog([string]$Line) {
  $script:LogLines.Add($line) | Out-Null
  if ($script:progressBox) { $script:progressBox.AppendText("$line`r`n") }
}

function Run-SelectedInstalls([string[]]$Selected, [string]$Hmi, [string]$Gateway) {
  $script:LogLines.Clear()
  $ok = $true
  foreach ($comp in $Selected) {
    if ($comp -eq 'HMI') {
      if (-not (Test-FraktalEndpoint $Hmi)) { Write-WizardLog '[HMI] invalid endpoint.'; $ok = $false; continue }
      $ok = (Invoke-ComponentInstall 'HMI' 'install_hmi.ps1' $Hmi) -and $ok
    } elseif ($comp -eq 'Gateway') {
      if (-not (Test-FraktalEndpoint $Gateway)) { Write-WizardLog '[Gateway] invalid endpoint.'; $ok = $false; continue }
      $ok = (Invoke-ComponentInstall 'Gateway' 'install_gateway.ps1' $Gateway) -and $ok
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
  if (-not $HmiEndpoint) { $HmiEndpoint = 'ads://127.0.0.1.1.1:851' }
  if (-not $GatewayEndpoint) { $GatewayEndpoint = 'opc.tcp://127.0.0.1:4840' }
  $ok = Run-SelectedInstalls $Components $HmiEndpoint $GatewayEndpoint
  if (-not $ok) { exit 1 }
  exit 0
}

# ---- WinForms wizard -------------------------------------------------------
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Fraktal Setup'
$form.Size = New-Object System.Drawing.Size(560, 420)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

# --- Page 0: component selection ---
$componentsPage = New-Object System.Windows.Forms.Panel
$componentsPage.Dock = 'Fill'
$intro = New-Object System.Windows.Forms.Label
$intro.Text = "Choose the Fraktal components to install. Select at least one.`r`n`r`nThe two components are independent: the HMI app connects directly to the PLC (ADS on a TwinCAT host); the Gateway serves the browser-based Web HMI over OPC UA."
$intro.AutoSize = $false
$intro.Size = New-Object System.Drawing.Size(500, 90)
$intro.Location = New-Object System.Drawing.Point(20, 15)

$hmiCheck = New-Object System.Windows.Forms.CheckBox
$hmiCheck.Text = 'Fraktal HMI  (native desktop app, ADS direct to PLC)'
$hmiCheck.Location = New-Object System.Drawing.Point(24, 120)
$hmiCheck.Size = New-Object System.Drawing.Size(500, 30)

$gwCheck = New-Object System.Windows.Forms.CheckBox
$gwCheck.Text = 'Fraktal Gateway + Web HMI  (browser access via OPC UA)'
$gwCheck.Location = New-Object System.Drawing.Point(24, 155)
$gwCheck.Size = New-Object System.Drawing.Size(500, 30)

$componentsPage.Controls.AddRange(@($intro, $hmiCheck, $gwCheck))

# --- Page 1: endpoints ---
$endpointsPage = New-Object System.Windows.Forms.Panel
$endpointsPage.Dock = 'Fill'
$epIntro = New-Object System.Windows.Forms.Label
$epIntro.Text = 'Configure the PLC endpoint for each selected component.'
$epIntro.AutoSize = $false
$epIntro.Size = New-Object System.Drawing.Size(500, 40)
$epIntro.Location = New-Object System.Drawing.Point(20, 15)

$hmiEpLabel = New-Object System.Windows.Forms.Label
$hmiEpLabel.Text = 'HMI endpoint (ads://<AmsNetId>:<port>):'
$hmiEpLabel.Location = New-Object System.Drawing.Point(24, 70)
$hmiEpLabel.Size = New-Object System.Drawing.Size(480, 20)
$hmiEpBox = New-Object System.Windows.Forms.TextBox
$hmiEpBox.Text = 'ads://127.0.0.1.1.1:851'
$hmiEpBox.Location = New-Object System.Drawing.Point(24, 92)
$hmiEpBox.Size = New-Object System.Drawing.Size(480, 24)

$gwEpLabel = New-Object System.Windows.Forms.Label
$gwEpLabel.Text = 'Gateway PLC endpoint (opc.tcp://<host>:<port>):'
$gwEpLabel.Location = New-Object System.Drawing.Point(24, 130)
$gwEpLabel.Size = New-Object System.Drawing.Size(480, 20)
$gwEpBox = New-Object System.Windows.Forms.TextBox
$gwEpBox.Text = 'opc.tcp://127.0.0.1:4840'
$gwEpBox.Location = New-Object System.Drawing.Point(24, 152)
$gwEpBox.Size = New-Object System.Drawing.Size(480, 24)

$endpointsPage.Controls.AddRange(@($epIntro, $hmiEpLabel, $hmiEpBox, $gwEpLabel, $gwEpBox))

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
$backBtn.Location = New-Object System.Drawing.Point(190, 9)

$nextBtn = New-Object System.Windows.Forms.Button
$nextBtn.Text = 'Next'
$nextBtn.Size = New-Object System.Drawing.Size(90, 32)
$nextBtn.Location = New-Object System.Drawing.Point(290, 9)

$cancelBtn = New-Object System.Windows.Forms.Button
$cancelBtn.Text = 'Cancel'
$cancelBtn.Size = New-Object System.Drawing.Size(90, 32)
$cancelBtn.Location = New-Object System.Drawing.Point(390, 9)

$buttonBar.Controls.AddRange(@($backBtn, $nextBtn, $cancelBtn))

$form.Controls.Add($content)
$form.Controls.Add($buttonBar)

$script:pageIndex = 0

function Show-Page([int]$Index) {
  for ($i = 0; $i -lt $pages.Count; $i++) { $pages[$i].Visible = ($i -eq $Index) }
  $script:pageIndex = $Index
  $backBtn.Visible = ($Index -gt 0 -and $Index -lt 2)
  if ($Index -eq 0) {
    $nextBtn.Text = 'Install'
    $nextBtn.Enabled = ($hmiCheck.Checked -or $gwCheck.Checked)
  } elseif ($Index -eq 1) {
    # Only reveal endpoint fields for selected components.
    $hmiEpLabel.Visible = $hmiCheck.Checked
    $hmiEpBox.Visible = $hmiCheck.Checked
    $gwEpLabel.Visible = $gwCheck.Checked
    $gwEpBox.Visible = $gwCheck.Checked
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

$hmiCheck.Add_CheckedChanged({ Update-ComponentsNext })
$gwCheck.Add_CheckedChanged({ Update-ComponentsNext })

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
    if ($hmiCheck.Checked -and -not (Test-FraktalEndpoint $hmiEpBox.Text)) {
      [System.Windows.Forms.MessageBox]::Show($form,
        'Enter a valid HMI endpoint, e.g. ads://192.168.1.6.1.1:851 (six dot-separated parts).',
        'Invalid HMI endpoint', 0, 48)
      return
    }
    if ($gwCheck.Checked -and -not (Test-FraktalEndpoint $gwEpBox.Text)) {
      [System.Windows.Forms.MessageBox]::Show($form,
        'Enter a valid Gateway PLC endpoint, e.g. opc.tcp://192.168.1.6:4840.',
        'Invalid Gateway endpoint', 0, 48)
      return
    }
    $selected = @()
    if ($hmiCheck.Checked) { $selected += 'HMI' }
    if ($gwCheck.Checked) { $selected += 'Gateway' }
    Show-Page 2
    $form.Refresh()
    $script:installOk = Run-SelectedInstalls $selected $hmiEpBox.Text $gwEpBox.Text
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
