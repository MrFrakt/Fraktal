param([long]$WindowHandle,[int]$CapacityProcessId,[string]$Destination)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $Destination){throw 'New evidence required'}
Add-Type @'
using System;using System.Text;using System.Runtime.InteropServices;
public static class CapacityControls {
 public delegate bool Visitor(IntPtr window,IntPtr parameter);
 [StructLayout(LayoutKind.Sequential)] public struct Rect {public int Left,Top,Right,Bottom;}
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr parent,Visitor visitor,IntPtr parameter);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr window,out uint process);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr window,StringBuilder text,int count);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr window,StringBuilder text,int count);
 [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr window);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr window,out Rect rect);
 [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr window,int index);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr window);
 [DllImport("user32.dll")] public static extern IntPtr GetParent(IntPtr window);
}
'@
[uint32]$rootProcess=0
[void][CapacityControls]::GetWindowThreadProcessId([IntPtr]$WindowHandle,[ref]$rootProcess)
if($rootProcess -ne $CapacityProcessId){throw 'Unexpected UI owner process'}
$capacityFound=[System.Collections.Generic.List[object]]::new()
$capacityVisitor=[CapacityControls+Visitor]{param($window,$parameter)
 $caption=[System.Text.StringBuilder]::new(2048);$class=[System.Text.StringBuilder]::new(256)
 [void][CapacityControls]::GetClassName($window,$class,256)
 $isPassword=$class.ToString() -match 'Edit' -and (([CapacityControls]::GetWindowLong($window,-16) -band 0x20) -ne 0)
 if(-not $isPassword){[void][CapacityControls]::GetWindowText($window,$caption,2048)}
 $rect=[CapacityControls+Rect]::new();[void][CapacityControls]::GetWindowRect($window,[ref]$rect)
 $capacityFound.Add([PSCustomObject]@{Handle=$window.ToInt64();Parent=[CapacityControls]::GetParent($window).ToInt64();Id=[CapacityControls]::GetDlgCtrlID($window);Class=$class.ToString();Name=$caption.ToString();Visible=[CapacityControls]::IsWindowVisible($window);PasswordSkipped=$isPassword;Left=$rect.Left;Top=$rect.Top;Right=$rect.Right;Bottom=$rect.Bottom})
 return $true
}
[void][CapacityControls]::EnumChildWindows([IntPtr]$WindowHandle,$capacityVisitor,[IntPtr]::Zero)
$report=[PSCustomObject]@{ReadOnly=$true;RootHandle=$WindowHandle;ProcessId=$CapacityProcessId;Controls=@($capacityFound.ToArray())}
$report|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $Destination -Encoding UTF8
$report.Controls|Where-Object {$_.Name -or $_.Class -eq 'SysTabControl32'}|Select-Object -First 75 Id,Class,Name,Handle|ConvertTo-Json -Compress
