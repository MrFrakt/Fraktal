param([ValidateSet('Run','Stop')][string]$State)
$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files (x86)\Beckhoff\TwinCAT\3.1\Components\Base\v170\TwinCAT.Ads.dll'
function Read-Bytes {
 param($Client,[string]$Name,[int]$Size)
 $wr=New-Object TwinCAT.Ads.AdsStream (,[Text.Encoding]::ASCII.GetBytes($Name+[char]0))
 $rd=New-Object TwinCAT.Ads.AdsStream ($Size)
 [void]$Client.ReadWrite(0xF004,0,$rd,$wr)
 return $rd.ToArray()
}
$client=New-Object TwinCAT.Ads.TcAdsClient
try {
 $client.Connect('192.168.1.6.1.1',851)
 $project=[Text.Encoding]::ASCII.GetString((Read-Bytes $client 'TwinCAT_SystemInfoVarList._AppInfo.ProjectName' 64)).Split([char]0)[0]
 if($project -ne 'Fraktal_Tests') { throw "Foreign application: $project" }
 foreach($flag in @('ActivePlcForces','ActiveIoForces')) {
  if((Read-Bytes $client "TwinCAT_SystemInfoVarList._AppInfo.$flag" 1)[0] -ne 0) { throw "Release $flag before changing state" }
 }
 $before=$client.ReadState().AdsState
 if($State -eq 'Run') { $requested=[TwinCAT.Ads.AdsState]::Run } else { $requested=[TwinCAT.Ads.AdsState]::Stop }
 $client.WriteControl((New-Object TwinCAT.Ads.StateInfo $requested, $client.ReadState().DeviceState))
 $after=$client.ReadState().AdsState
 if($after -ne $requested) { throw "State change not observed: $after" }
 "Target=192.168.1.6.1.1:851; Project=$project; $before -> $after; both force flags clear"
 "ObservedAt=$(Get-Date -Format o)"
} finally { $client.Dispose() }
