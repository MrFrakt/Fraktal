$ErrorActionPreference='Stop'
$dte=[Runtime.InteropServices.Marshal]::GetActiveObject('VisualStudio.DTE.18.0')
$expected=Join-Path $PSScriptRoot 'checkout/FraktalCore/PLC/TwinCAT/Tests/FraktalTests.slnx'
if([IO.Path]::GetFullPath($dte.Solution.FullName) -ne [IO.Path]::GetFullPath($expected)) { throw 'Foreign XAE solution' }
$project=$dte.Solution.Projects.Item(1)
$sm=$project.Object
if($sm.GetTargetNetId() -ne '192.168.1.6.1.1') { throw 'Foreign XAE target' }
if($sm.LookupTreeItem('TIID').ChildCount -ne 0) { throw 'Test configuration must contain no I/O devices' }
$tasks=$sm.LookupTreeItem('TIRT')
if($tasks.ChildCount -ne 1) { throw 'Unexpected task configuration' }
$projectFile=Join-Path $PSScriptRoot 'checkout/FraktalCore/PLC/TwinCAT/Tests/FraktalTests.tsproj'
Copy-Item -LiteralPath $projectFile -Destination (Join-Path $PSScriptRoot 'logs/BeforeForceImage.tsproj')
$task=$tasks.CreateChild('ForceAcceptanceTask',0,$null,$null)
$inputs=$sm.LookupTreeItem('TIRT^ForceAcceptanceTask^Inputs')
$variable=$inputs.CreateChild('ForceIoWitness',-1,$null,'BOOL')
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'logs/ForceTask.xml'),$task.ProduceXml(),(New-Object Text.UTF8Encoding $false))
$project.Save('')
Copy-Item -LiteralPath $projectFile -Destination (Join-Path $PSScriptRoot 'logs/WithForceImage.tsproj')
"Target=$($sm.GetTargetNetId()); I/O devices=$($sm.LookupTreeItem('TIID').ChildCount); Tasks=$($tasks.ChildCount)"
"Created $($variable.PathName): unlinked BOOL in a software-only task image"
