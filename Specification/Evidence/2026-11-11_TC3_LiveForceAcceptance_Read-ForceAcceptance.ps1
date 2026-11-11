param([string]$Phase = 'baseline')
$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files (x86)\Beckhoff\TwinCAT\3.1\Components\Base\v170\TwinCAT.Ads.dll'
function Read-Bytes {
    param($Client,[string]$Name,[int]$Size)
    $wr=New-Object TwinCAT.Ads.AdsStream (,[Text.Encoding]::ASCII.GetBytes($Name+[char]0))
    $rd=New-Object TwinCAT.Ads.AdsStream ($Size)
    [void]$Client.ReadWrite(0xF004,0,$rd,$wr)
    return $rd.ToArray()
}
function Read-Number { param($Client,[string]$Name) return [BitConverter]::ToInt32((Read-Bytes $Client $Name 4),0) }
function Read-Text { param($Client,[string]$Name,[int]$Size=256) return [Text.Encoding]::ASCII.GetString((Read-Bytes $Client $Name $Size)).Split([char]0)[0] }
function Read-Bool { param($Client,[string]$Name) return (Read-Bytes $Client $Name 1)[0] -ne 0 }
$client=New-Object TwinCAT.Ads.TcAdsClient
try {
    $client.Connect('192.168.1.6.1.1',851)
    $project=Read-Text $client 'TwinCAT_SystemInfoVarList._AppInfo.ProjectName' 64
    if($project -ne 'Fraktal_Tests') { throw "Foreign application: $project" }
    $sample=[ordered]@{Phase=$Phase;ObservedAt=(Get-Date -Format o);Target='192.168.1.6.1.1:851';Project=$project;AdsState=$client.ReadState().AdsState.ToString()}
    foreach($field in @('ActivePlcForces','ActiveIoForces')) { $sample[$field]=Read-Bool $client "TwinCAT_SystemInfoVarList._AppInfo.$field" }
    $sample.ForceWitness=Read-Bool $client 'PRG_PlatformAcceptance.ForceWitness'
    $sample.Available=Read-Bool $client 'PRG_PlatformAcceptance.MaintenanceProbe.Health.MaintenanceAvailable'
    $sample.Demanded=Read-Bool $client 'PRG_PlatformAcceptance.MaintenanceProbe.Health.MaintenanceDemanded'
    $sample.Healthy=Read-Bool $client 'PRG_PlatformAcceptance.MaintenanceUnit.SystemHealth.Healthy'
    $prefix='PRG_PlatformAcceptance.MaintenanceUnit.AlarmLog'
    $events=@()
    for($idx=1;$idx -le 16;$idx++) {
        $path="$prefix.Active[$idx]"
        $state=Read-Number $client "$path.State"
        $reason=Read-Number $client "$path.ReasonCode"
        if($state -ne 0) { $events+= [ordered]@{Slot=$idx;Reason=$reason;State=$state;Severity=(Read-Number $client "$path.Severity");Category=(Read-Number $client "$path.Category");ResetClass=(Read-Number $client "$path.ResetClass");Description=(Read-Text $client "$path.Description");Source=(Read-Text $client "$path.SourcePath");Shelved=(Read-Bool $client "$path.Shelved")} }
    }
    $sample.ActiveEvents=$events
    $head=[BitConverter]::ToInt16((Read-Bytes $client "$prefix.RingHead" 2),0)
    $sample.RingHead=$head
    if($head -gt 0) {
        $path="$prefix.Ring[$head]"
        $sample.LatestClosed=[ordered]@{Reason=(Read-Number $client "$path.ReasonCode");State=(Read-Number $client "$path.State");Description=(Read-Text $client "$path.Description");Source=(Read-Text $client "$path.SourcePath");DurationMs=(Read-Number $client "$path.Duration")}
    }
    $json=$sample | ConvertTo-Json -Depth 8
    $dest=Join-Path $PSScriptRoot "logs/Force-$Phase.json"
    if(Test-Path -LiteralPath $dest) { throw "Snapshot exists: $dest" }
    [IO.File]::WriteAllText($dest,$json+[Environment]::NewLine,(New-Object Text.UTF8Encoding $false))
    $json
} finally { $client.Dispose() }
