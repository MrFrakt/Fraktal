<#
.SYNOPSIS
  Start, inspect or remove an S7-PLCSIM Advanced virtual controller through its
  Runtime API (Part IV s.12, S11) - headless, no UI.

.DESCRIPTION
  start   registers the instance (if absent), powers it on and switches it to RUN
          once a program has been downloaded (RUN fails on an empty CPU; STOP is
          then reported, not an error).
  status  lists registered instances, controller IPs and their operating state.
  halt    switches RUN to STOP without removing the virtual controller.
  off     powers off the instance but keeps its registration and downloaded image.
  stop    powers the instance off and unregisters it.
  read    reads the leaf tags of the named data blocks (-DataBlocks 'A,B'),
          optionally narrowed by a regular expression on the tag name (-Match).
          Read-only: it writes nothing to the virtual controller.
  write   writes one Bool/Int32/UInt32 leaf after validating its native type
          and the exact Softbus controller IP (-ConfirmTarget).

  The instance communicates over the PLCSIM softbus: only engineering on this
  workstation reaches it. Nothing here addresses a physical controller.

.EXAMPLE
  powershell -File Invoke-PlcSimInstance.ps1 -Action start -Name FrkS11
#>
param(
  [ValidateSet('host', 'start', 'status', 'stop', 'halt', 'off', 'run', 'read', 'write')] [string] $Action = 'status',
  [string] $Name = 'FrkS11',
  [string] $ApiVersion = '5.0',
  [int] $MaxMinutes = 120,
  [string] $DataBlocks = '',
  [string] $Match = '.',
  [string] $ConfirmTarget = '',
  [string] $Tag = '',
  [ValidateSet('Bool', 'Int32', 'UInt32')] [string] $ValueType = 'Bool',
  [string] $Value = ''
)
# 'host' owns the session lifecycle: register, power on, log state changes until the
# stop file "<TEMP>\plcsim_<Name>.stop" appears or MaxMinutes pass; then power off
# and unregister. Start it in the background (Start-Process) for a session.

$ErrorActionPreference = 'Stop'
$dll = "C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\$ApiVersion\Siemens.Simatic.Simulation.Runtime.Api.x64.dll"
$asm = [Reflection.Assembly]::LoadFrom($dll)
$manager = $asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')

function Emit($kind, $data) { ([ordered]@{ t = [datetime]::UtcNow.ToString('o'); event = $kind } + $data) | ConvertTo-Json -Compress }

# The first PowerOn after the Runtime Manager process cold-starts can fail with
# "InstanceNotRunning" (-14) while the manager is still coming up (measured
# 2026-10-09); the same call succeeds seconds later. Retry, never loop forever.
function Invoke-PowerOn($inst) {
  for ($try = 1; ; $try++) {
    try { Emit 'power-on' @{ result = "$($inst.PowerOn(60000))"; attempt = $try }; return }
    catch {
      if ($try -ge 3) { throw }
      Emit 'power-on-retry' @{ attempt = $try; message = $_.Exception.InnerException.Message }
      Start-Sleep -Seconds 5
    }
  }
}

function Find-Instance {
  foreach ($info in $manager.GetProperty('RegisteredInstanceInfo').GetValue($null)) {
    if ($info.Name -eq $Name) { return $manager.GetMethod('CreateInterface', [type[]]@([string])).Invoke($null, @($Name)) }
  }
  return $null
}

switch ($Action) {
  'host' {
    $stopFile = Join-Path $env:TEMP "plcsim_$Name.stop"
    Remove-Item $stopFile -ErrorAction SilentlyContinue
    $inst = Find-Instance
    if (-not $inst) { $inst = $manager.GetMethod('RegisterInstance', [type[]]@([string])).Invoke($null, @($Name)); Emit 'registered' @{ name = $Name } }
    if ("$($inst.OperatingState)" -eq 'Off') { Invoke-PowerOn $inst }
    $last = ''
    $deadline = [datetime]::UtcNow.AddMinutes($MaxMinutes)
    try {
      while (-not (Test-Path $stopFile) -and [datetime]::UtcNow -lt $deadline) {
        $now = "$($inst.OperatingState)|$($inst.CPUType)"
        if ($now -ne $last) { Emit 'instance' @{ name = $Name; state = "$($inst.OperatingState)"; cpu = "$($inst.CPUType)"; comm = "$($inst.CommunicationInterface)" }; $last = $now }
        Start-Sleep -Seconds 2
      }
    } finally {
      try { $inst.PowerOff(30000) | Out-Null } catch { }
      try { $inst.UnregisterInstance() } catch { }
      Remove-Item $stopFile -ErrorAction SilentlyContinue
      Emit 'unregistered' @{ name = $Name; reason = $(if ([datetime]::UtcNow -ge $deadline) { 'max-minutes' } else { 'stop-file' }) }
    }
  }
  'status' {
    foreach ($info in $manager.GetProperty('RegisteredInstanceInfo').GetValue($null)) {
      $i = $manager.GetMethod('CreateInterface', [type[]]@([string])).Invoke($null, @($info.Name))
      Emit 'instance' @{ name = $info.Name; id = $info.ID; state = "$($i.OperatingState)"; cpu = "$($i.CPUType)"; comm = "$($i.CommunicationInterface)"; addresses = @($i.ControllerIP) }
    }
    Emit 'runtime' @{ version = $manager.GetProperty('Version').GetValue($null); instances = $manager.GetProperty('RegisteredInstanceInfo').GetValue($null).Length }
  }
  'start' {
    $inst = Find-Instance
    if (-not $inst) { $inst = $manager.GetMethod('RegisterInstance', [type[]]@([string])).Invoke($null, @($Name)); Emit 'registered' @{ name = $Name } }
    if ("$($inst.OperatingState)" -eq 'Off') { Invoke-PowerOn $inst }
    Emit 'instance' @{ name = $Name; state = "$($inst.OperatingState)"; cpu = "$($inst.CPUType)"; comm = "$($inst.CommunicationInterface)" }
  }
  { $_ -in 'run', 'halt', 'off' } {
    $inst = Find-Instance
    if (-not $inst) { throw "instance $Name is not registered" }
    $addresses = @($inst.ControllerIP)
    if (-not $ConfirmTarget -or $ConfirmTarget -notin $addresses -or "$($inst.CommunicationInterface)" -ne 'Softbus') {
      throw 'mode change requires -ConfirmTarget matching a Softbus controller IP from status'
    }
    Emit 'target-confirmed' @{ name = $Name; cpu = "$($inst.CPUType)"; address = $ConfirmTarget; comm = "$($inst.CommunicationInterface)" }
    if ($Action -eq 'run') { $inst.Run(30000) }
    elseif ($Action -eq 'halt') { $inst.Stop(30000) }
    else { $inst.PowerOff(30000) }
    Emit $Action @{ result = 'success' }
    Emit 'instance' @{ name = $Name; state = "$($inst.OperatingState)"; cpu = "$($inst.CPUType)" }
  }
  'read' {
    $inst = Find-Instance
    if (-not $inst) { throw "instance $Name is not registered" }
    $details = [enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ETagListDetails'), 'DB')
    # the filter takes each block name in double quotes ('"A","B"'); bare names are
    # refused with WrongArgument (-8), measured on API 5.0
    $filter = (($DataBlocks -split ',') | Where-Object { $_.Trim() } | ForEach-Object { '"' + $_.Trim().Trim('"') + '"' }) -join ','
    $inst.UpdateTagList($details, $false, $filter)
    $readCount = 0
    foreach ($leafTag in $inst.TagInfos) {
      if ("$($leafTag.PrimitiveDataType)" -eq 'Struct' -or $leafTag.Name -notmatch $Match) { continue }
      try {
        $v = $inst.Read($leafTag.Name)
        Emit 'tag' @{ name = $leafTag.Name; type = "$($v.Type)"; value = $v."$($v.Type)" }
        $readCount++
      } catch { Emit 'tag-failed' @{ name = $leafTag.Name; message = $_.Exception.InnerException.Message } }
    }
    if ($readCount -eq 0) { throw 'no matching readable tags; an empty harvest is not evidence' }
  }
  'write' {
    $inst = Find-Instance
    if (-not $inst) { throw "instance $Name is not registered" }
    if (-not $ConfirmTarget -or $ConfirmTarget -notin @($inst.ControllerIP) -or "$($inst.CommunicationInterface)" -ne 'Softbus') {
      throw 'tag write requires -ConfirmTarget matching a Softbus controller IP from status'
    }
    if (-not $Tag -or $Tag -notmatch '^([A-Za-z_]\w*)\.') { throw 'Tag must be a qualified DB member name' }
    $blockName = $Matches[1]
    $details = [enum]::Parse($asm.GetType('Siemens.Simatic.Simulation.Runtime.ETagListDetails'), 'DB')
    $inst.UpdateTagList($details, $false, '"' + $blockName + '"')
    $matchesTag = @($inst.TagInfos | Where-Object { $_.Name -ceq $Tag })
    if ($matchesTag.Count -ne 1 -or "$($matchesTag[0].PrimitiveDataType)" -ne $ValueType) {
      throw 'tag must exist exactly once and match ValueType'
    }
    Emit 'target-confirmed' @{ name = $Name; address = $ConfirmTarget; cpu = "$($inst.CPUType)"; comm = "$($inst.CommunicationInterface)" }
    switch ($ValueType) {
      'Bool' { $typedValue = [bool]::Parse($Value); $inst.WriteBool($Tag, $typedValue) }
      'Int32' { $typedValue = [int]::Parse($Value, [Globalization.CultureInfo]::InvariantCulture); $inst.WriteInt32($Tag, $typedValue) }
      'UInt32' { $typedValue = [uint32]::Parse($Value, [Globalization.CultureInfo]::InvariantCulture); $inst.WriteUInt32($Tag, $typedValue) }
    }
    Emit 'tag-write' @{ tag = $Tag; type = $ValueType; value = $typedValue }
  }
  'stop' {
    $inst = Find-Instance
    if ($inst) {
      try { $inst.PowerOff(30000) | Out-Null } catch { }
      $inst.UnregisterInstance(); Emit 'unregistered' @{ name = $Name }
    } else { Emit 'absent' @{ name = $Name } }
  }
}
