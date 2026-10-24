param([int]$CapacityProcessId,[string]$Destination)
$ErrorActionPreference='Stop'
if (Test-Path -LiteralPath $Destination) { throw 'New evidence output required' }
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class CapacityWindows {
 public delegate bool Visitor(IntPtr window, IntPtr parameter);
 [DllImport("user32.dll")] public static extern bool EnumWindows(Visitor visitor,IntPtr parameter);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr window,out uint process);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr window,StringBuilder text,int count);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr window,StringBuilder text,int count);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr window);
 [DllImport("user32.dll")] public static extern IntPtr GetMenu(IntPtr window);
 [DllImport("user32.dll")] public static extern int GetMenuItemCount(IntPtr menu);
 [DllImport("user32.dll")] public static extern IntPtr GetSubMenu(IntPtr menu,int position);
 [DllImport("user32.dll")] public static extern uint GetMenuItemID(IntPtr menu,int position);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetMenuString(IntPtr menu,uint item,StringBuilder text,int count,uint flags);
}
'@
$capacityFound=[System.Collections.Generic.List[object]]::new()
$capacityVisitor=[CapacityWindows+Visitor]{
 param($window,$parameter)
 [uint32]$ownerProcess=0
 [void][CapacityWindows]::GetWindowThreadProcessId($window,[ref]$ownerProcess)
 if ($ownerProcess -eq $CapacityProcessId) {
  $windowText=[System.Text.StringBuilder]::new(4096)
  $windowClass=[System.Text.StringBuilder]::new(256)
  [void][CapacityWindows]::GetWindowText($window,$windowText,4096)
  [void][CapacityWindows]::GetClassName($window,$windowClass,256)
  $capacityFound.Add([PSCustomObject]@{Handle=$window.ToInt64();Name=$windowText.ToString();Class=$windowClass.ToString();Visible=[CapacityWindows]::IsWindowVisible($window)})
 }
 return $true
}
[void][CapacityWindows]::EnumWindows($capacityVisitor,[IntPtr]::Zero)
$report=[PSCustomObject]@{ProcessId=$CapacityProcessId;ReadOnly=$true;Windows=@($capacityFound.ToArray())}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Destination -Encoding UTF8
$report | ConvertTo-Json -Depth 6 -Compress
