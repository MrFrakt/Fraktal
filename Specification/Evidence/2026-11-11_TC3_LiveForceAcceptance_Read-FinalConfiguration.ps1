$ErrorActionPreference='Stop'
$dte=[Runtime.InteropServices.Marshal]::GetActiveObject('VisualStudio.DTE.18.0')
$expected=Join-Path $PSScriptRoot 'checkout/FraktalCore/PLC/TwinCAT/Tests/FraktalTests.slnx'
if([IO.Path]::GetFullPath($dte.Solution.FullName) -ne [IO.Path]::GetFullPath($expected)) { throw 'Foreign XAE solution' }
$sm=$dte.Solution.Projects.Item(1).Object
if($sm.GetTargetNetId() -ne '192.168.1.6.1.1') { throw 'Foreign XAE target' }
$tasks=$sm.LookupTreeItem('TIRT')
if($tasks.ChildCount -ne 1 -or $tasks.Child(1).Name -ne 'PlcTask') { throw 'Temporary task remains' }
if($sm.LookupTreeItem('TIID').ChildCount -ne 0) { throw 'Unexpected I/O devices' }
$plc=$sm.LookupTreeItem('TIPC^Fraktal_Tests')
if($plc.BootProjectAutostart) { throw 'Test boot autostart enabled' }
"Solution=$($dte.Solution.FullName)"
"Target=192.168.1.6.1.1; Tasks=1 (PlcTask); I/O devices=0; BootProjectAutostart=False"
"ObservedAt=$(Get-Date -Format o)"
