<#
.SYNOPSIS
  Start, inspect or remove an S7-PLCSIM Advanced virtual controller through its
  Runtime API (Part IV s.12, S11) - headless, no UI.

.DESCRIPTION
  start   registers the instance (if absent), powers it on and switches it to RUN
          once a program has been downloaded (RUN fails on an empty CPU; STOP is
          then reported, not an error).
  status  lists registered instances and their operating state.
  stop    powers the instance off and unregisters it.

  The instance communicates over the PLCSIM softbus: only engineering on this
  workstation reaches it. Nothing here addresses a physical controller.

.EXAMPLE
  powershell -File Invoke-PlcSimInstance.ps1 -Action start -Name FrkS11
#>
param(
  [ValidateSet('host', 'start', 'status', 'stop', 'run')] [string] $Action = 'status',
  [string] $Name = 'FrkS11',
  [string] $ApiVersion = '5.0',
  [int] $MaxMinutes = 120
)
# An instance lives only as long as the process that registered it (measured:
# registered and powered on, then absent from a second process). 'host' therefore
# owns it: register, power on, log every state change, and keep running until the
# stop file "<TEMP>\plcsim_<Name>.stop" appears or MaxMinutes pass; then power off
# and unregister. Start it in the background (Start-Process) for a session.

$ErrorActionPreference = 'Stop'
$dll = "C:\Program Files (x86)\Common Files\Siemens\PLCSIMADV\API\$ApiVersion\Siemens.Simatic.Simulation.Runtime.Api.x64.dll"
$asm = [Reflection.Assembly]::LoadFrom($dll)
$manager = $asm.GetType('Siemens.Simatic.Simulation.Runtime.SimulationRuntimeManager')

function Emit($kind, $data) { ([ordered]@{ t = [datetime]::UtcNow.ToString('o'); event = $kind } + $data) | ConvertTo-Json -Compress }

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
    if ("$($inst.OperatingState)" -eq 'Off') { Emit 'power-on' @{ result = "$($inst.PowerOn(60000))" } }
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
      Emit 'instance' @{ name = $info.Name; id = $info.ID; state = "$($i.OperatingState)"; cpu = "$($i.CPUType)"; comm = "$($i.CommunicationInterface)" }
    }
    Emit 'runtime' @{ version = $manager.GetProperty('Version').GetValue($null); instances = $manager.GetProperty('RegisteredInstanceInfo').GetValue($null).Length }
  }
  'start' {
    $inst = Find-Instance
    if (-not $inst) { $inst = $manager.GetMethod('RegisterInstance', [type[]]@([string])).Invoke($null, @($Name)); Emit 'registered' @{ name = $Name } }
    if ("$($inst.OperatingState)" -eq 'Off') { Emit 'power-on' @{ result = "$($inst.PowerOn(60000))" } }
    Emit 'instance' @{ name = $Name; state = "$($inst.OperatingState)"; cpu = "$($inst.CPUType)"; comm = "$($inst.CommunicationInterface)" }
  }
  'run' {
    $inst = Find-Instance
    if (-not $inst) { throw "instance $Name is not registered" }
    try { Emit 'run' @{ result = "$($inst.Run(30000))" } } catch { Emit 'run-failed' @{ message = $_.Exception.InnerException.Message } }
    Emit 'instance' @{ name = $Name; state = "$($inst.OperatingState)"; cpu = "$($inst.CPUType)" }
  }
  'stop' {
    $inst = Find-Instance
    if ($inst) {
      try { $inst.PowerOff(30000) | Out-Null } catch { }
      $inst.UnregisterInstance(); Emit 'unregistered' @{ name = $Name }
    } else { Emit 'absent' @{ name = $Name } }
  }
}
