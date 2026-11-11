$ErrorActionPreference='Stop'
$dte=[Runtime.InteropServices.Marshal]::GetActiveObject('VisualStudio.DTE.18.0')
$solution=$dte.Solution.FullName
$expected='C:\Projects\Fraktal\artifacts\tc3-live-force-2026-11-11\checkout\FraktalCore\PLC\TwinCAT\Tests\FraktalTests.slnx'
if($solution -ne $expected -and $solution -ne ($expected -replace '\.slnx$','.sln')) { throw "Foreign solution: $solution" }
$sm=$dte.Solution.Projects.Item(1).Object
$netId=$sm.GetTargetNetId()
if($netId -ne '192.168.1.6.1.1') { throw "Foreign XAE target: $netId" }
"Solution=$solution"
"XaeTargetNetId=$netId"
"ObservedAt=$(Get-Date -Format o)"
