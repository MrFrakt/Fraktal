param([long]$WindowHandle,[int]$CapacityProcessId,[string]$Destination)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $Destination){throw 'New evidence required'}
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;using System.Text;using System.Runtime.InteropServices;
public static class CapacityProperties {
 public delegate void EventProc(IntPtr hook,uint eventId,IntPtr window,int objectId,int childId,uint thread,uint time);
 public static EventProc Keeper;
 [DllImport("user32.dll")] public static extern IntPtr SetWinEventHook(uint first,uint last,IntPtr module,EventProc callback,uint process,uint thread,uint flags);
 [DllImport("user32.dll")] public static extern bool UnhookWinEvent(IntPtr hook);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr window,out uint process);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr window,StringBuilder text,int count);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr window,uint message,IntPtr wparam,IntPtr lparam);
 [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr window,int index);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr window,int command);
}
'@
[uint32]$owner=0
[void][CapacityProperties]::GetWindowThreadProcessId([IntPtr]$WindowHandle,[ref]$owner)
$caption=[System.Text.StringBuilder]::new(2048)
[void][CapacityProperties]::GetWindowText([IntPtr]$WindowHandle,$caption,2048)
if($owner -ne $CapacityProcessId -or $caption.ToString() -notmatch '^Logix Designer - .* in capacity_review\.ACD '){throw 'Unexpected offline review window'}
$controls=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'capacity_controls_frame_01.json')|ConvertFrom-Json
if($controls.ProcessId -ne $CapacityProcessId -or -not ($controls.Controls.Name -contains 'Offline')){throw 'Offline UI proof missing'}
$resources=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'capacity_menu_resources_02.json')|ConvertFrom-Json
$command=@($resources.Matches|Where-Object { $_.Resource -eq 101 -and ($_.Path -replace '&','') -eq '/Edit/Controller Properties' })
if($command.Count -ne 1 -or $command[0].Command -ne 32023){throw 'Properties command not established from installed resources'}
$hidden=[System.Collections.Generic.List[long]]::new()
[CapacityProperties]::Keeper=[CapacityProperties+EventProc]{param($hook,$eventId,$window,$objectId,$childId,$thread,$time)
 if($window -ne [IntPtr]::Zero -and $objectId -eq 0 -and (([CapacityProperties]::GetWindowLong($window,-16) -band 0x40000000) -eq 0)) {
  [void][CapacityProperties]::ShowWindow($window,0)
  $hidden.Add($window.ToInt64())
 }
}
$hook=[CapacityProperties]::SetWinEventHook(0x8002,0x8002,[IntPtr]::Zero,[CapacityProperties]::Keeper,[uint32]$CapacityProcessId,0,0)
if($hook -eq [IntPtr]::Zero){throw 'Background UI visibility hook failed'}
try {
 if(-not [CapacityProperties]::PostMessage([IntPtr]$WindowHandle,0x111,[IntPtr]32023,[IntPtr]::Zero)){throw 'Properties command failed'}
 for($tick=0;$tick -lt 200;$tick++){[System.Windows.Forms.Application]::DoEvents();Start-Sleep -Milliseconds 10}
} finally {[void][CapacityProperties]::UnhookWinEvent($hook)}
$report=[PSCustomObject]@{ReadOnly=$true;ProcessId=$CapacityProcessId;SourceTitle=$caption.ToString();Command='Controller Properties';CommandId=32023;Offline=$true;HiddenWindows=@($hidden.ToArray())}
$report|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $Destination -Encoding UTF8
$report|ConvertTo-Json -Depth 5 -Compress
