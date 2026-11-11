$ErrorActionPreference='Stop'
$dte=[Runtime.InteropServices.Marshal]::GetActiveObject('VisualStudio.DTE.18.0')
$expected=Join-Path $PSScriptRoot 'checkout/FraktalCore/PLC/TwinCAT/Tests/FraktalTests.slnx'
if([IO.Path]::GetFullPath($dte.Solution.FullName) -ne [IO.Path]::GetFullPath($expected)) { throw 'Foreign XAE solution' }
$project=$dte.Solution.Projects.Item(1)
$sm=$project.Object
if($sm.GetTargetNetId() -ne '192.168.1.6.1.1') { throw 'Foreign XAE target' }
if($sm.LookupTreeItem('TIID').ChildCount -ne 0) { throw 'Unexpected I/O devices' }
$inputs=$sm.LookupTreeItem('TIRT^ForceAcceptanceTask^Inputs')
if($inputs.ChildCount -ne 1 -or $inputs.Child(1).Name -ne 'ForceIoWitness') { throw 'Foreign task image contents' }
$sm.LookupTreeItem('TIRT').DeleteChild('ForceAcceptanceTask')
$project.Save('')
$count=$sm.LookupTreeItem('TIRT').ChildCount
if($count -ne 1) { throw "Task count after cleanup: $count" }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'checkout/FraktalCore/PLC/TwinCAT/Tests/FraktalTests.tsproj') -Destination (Join-Path $PSScriptRoot 'logs/AfterForceImage.tsproj')
"Removed only the temporary ForceAcceptanceTask; Target=$($sm.GetTargetNetId()); I/O devices=0; Tasks=$count"
