param([string]$Destination,[string]$ResourceFile)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $Destination){throw 'New evidence required'}
Add-Type @'
using System;using System.Text;using System.Runtime.InteropServices;
public static class CapacityResources {
 public delegate bool NameVisitor(IntPtr module,IntPtr type,IntPtr name,IntPtr parameter);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern IntPtr LoadLibraryEx(string path,IntPtr file,uint flags);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern bool EnumResourceNames(IntPtr module,IntPtr type,NameVisitor visitor,IntPtr parameter);
 [DllImport("kernel32.dll")] public static extern bool FreeLibrary(IntPtr module);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern IntPtr LoadMenu(IntPtr module,IntPtr name);
 [DllImport("user32.dll")] public static extern bool DestroyMenu(IntPtr menu);
 [DllImport("user32.dll")] public static extern int GetMenuItemCount(IntPtr menu);
 [DllImport("user32.dll")] public static extern IntPtr GetSubMenu(IntPtr menu,int position);
 [DllImport("user32.dll")] public static extern uint GetMenuItemID(IntPtr menu,int position);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetMenuString(IntPtr menu,uint position,StringBuilder text,int count,uint flags);
}
'@
$capacityMatches=[System.Collections.Generic.List[object]]::new()
function Read-ResourceMenu([IntPtr]$menu,[string]$prefix,[long]$resource) {
 for($index=0;$index -lt [CapacityResources]::GetMenuItemCount($menu);$index++) {
  $caption=[System.Text.StringBuilder]::new(1024)
  [void][CapacityResources]::GetMenuString($menu,[uint32]$index,$caption,1024,0x400)
  $path=$prefix+'/'+$caption.ToString()
  if($path -match 'Properties|Controller') {
   $capacityMatches.Add([PSCustomObject]@{Resource=$resource;Path=$path;Command=[CapacityResources]::GetMenuItemID($menu,$index)})
  }
  $sub=[CapacityResources]::GetSubMenu($menu,$index)
  if($sub -ne [IntPtr]::Zero){Read-ResourceMenu $sub $path $resource}
 }
}
$exe=$ResourceFile
$module=[CapacityResources]::LoadLibraryEx($exe,[IntPtr]::Zero,0x22)
if($module -eq [IntPtr]::Zero){throw 'Read-only resource load failed'}
$capacityNames=[System.Collections.Generic.List[long]]::new()
$capacityVisitor=[CapacityResources+NameVisitor]{param($instance,$type,$name,$parameter)
 if($name.ToInt64() -le 65535){$capacityNames.Add($name.ToInt64())};return $true
}
[void][CapacityResources]::EnumResourceNames($module,[IntPtr]4,$capacityVisitor,[IntPtr]::Zero)
foreach($resource in $capacityNames){
 $menu=[CapacityResources]::LoadMenu($module,[IntPtr]$resource)
 if($menu -ne [IntPtr]::Zero){Read-ResourceMenu $menu '' $resource;[void][CapacityResources]::DestroyMenu($menu)}
}
[void][CapacityResources]::FreeLibrary($module)
$report=[PSCustomObject]@{ReadOnly=$true;Resources=$capacityNames.Count;Matches=@($capacityMatches.ToArray());Executable=$exe}
$report|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $Destination -Encoding UTF8
$report|ConvertTo-Json -Depth 6 -Compress
