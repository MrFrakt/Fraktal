param(
 [Parameter(Mandatory=$true)][string]$AcdPath,
 [Parameter(Mandatory=$true)][string]$ExpectedSha256,
 [Parameter(Mandatory=$true)][string]$OutputPath,
 [string]$StudioPath='C:/Program Files (x86)/Rockwell Software/Studio 5000/Logix Designer/ENU/v38/Bin/LogixDesigner.Exe'
)
# Offline GUI measurement. Opens only a verified disposable copy. The only UI
# commands are Properties, the Capacity page, Cancel and closing our process.
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputPath){throw 'New evidence output required'}
$source=(Resolve-Path -LiteralPath $AcdPath).Path
if([IO.Path]::GetExtension($source) -ine '.ACD' -or $ExpectedSha256 -notmatch '^[A-Fa-f0-9]{64}$'){throw 'Pinned ACD required'}
$sourceHash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
if($sourceHash -ine $ExpectedSha256){throw 'Source ACD hash differs'}
$directory=[IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($OutputPath))
$review=Join-Path $directory ('Capacity_'+[Guid]::NewGuid().ToString('N')+'.ACD')
[IO.File]::Copy($source,$review,$false)
if((Get-FileHash -LiteralPath $review -Algorithm SHA256).Hash -ine $sourceHash){throw 'Review copy differs'}
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;using System.Text;using System.Collections.Generic;using System.Runtime.InteropServices;
public static class FraktalCapacityUi {
 public class Node {public long Handle,Parent;public int Id;public string Name,Class;public bool Visible,PasswordSkipped;}
 public delegate bool Visitor(IntPtr window,IntPtr parameter);
 public delegate void EventProc(IntPtr hook,uint eventId,IntPtr window,int objectId,int childId,uint thread,uint time);
 public static EventProc Keeper=HideShownTop;
 [DllImport("user32.dll")] static extern bool EnumWindows(Visitor callback,IntPtr parameter);
 [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr root,Visitor callback,IntPtr parameter);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window,out uint process);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr window,StringBuilder text,int count);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr window,StringBuilder text,int count);
 [DllImport("user32.dll")] static extern int GetDlgCtrlID(IntPtr window);
 [DllImport("user32.dll")] static extern int GetWindowLong(IntPtr window,int index);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr window);
 [DllImport("user32.dll")] static extern IntPtr GetParent(IntPtr window);
 [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr window,int command);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr window,uint message,IntPtr wparam,IntPtr lparam);
 [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr window,uint message,IntPtr wparam,IntPtr lparam);
 [DllImport("user32.dll")] public static extern IntPtr SetWinEventHook(uint first,uint last,IntPtr module,EventProc callback,uint process,uint thread,uint flags);
 [DllImport("user32.dll")] public static extern bool UnhookWinEvent(IntPtr hook);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern IntPtr LoadLibraryEx(string path,IntPtr file,uint flags);
 [DllImport("kernel32.dll")] static extern bool FreeLibrary(IntPtr module);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern IntPtr LoadMenu(IntPtr module,IntPtr name);
 [DllImport("user32.dll")] static extern bool DestroyMenu(IntPtr menu);
 [DllImport("user32.dll")] static extern int GetMenuItemCount(IntPtr menu);
 [DllImport("user32.dll")] static extern IntPtr GetSubMenu(IntPtr menu,int position);
 [DllImport("user32.dll")] static extern uint GetMenuItemID(IntPtr menu,int position);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetMenuString(IntPtr menu,uint position,StringBuilder text,int count,uint flags);
 static void HideShownTop(IntPtr hook,uint eventId,IntPtr window,int objectId,int childId,uint thread,uint time) {
  if(window!=IntPtr.Zero && objectId==0 && (GetWindowLong(window,-16)&0x40000000)==0)ShowWindow(window,0);
 }
 static Node Read(IntPtr window) {
  var caption=new StringBuilder(2048);var kind=new StringBuilder(256);GetClassName(window,kind,256);
  bool password=kind.ToString().IndexOf("Edit",StringComparison.OrdinalIgnoreCase)>=0 && (GetWindowLong(window,-16)&0x20)!=0;
  if(!password)GetWindowText(window,caption,2048);
  return new Node {Handle=window.ToInt64(),Parent=GetParent(window).ToInt64(),Id=GetDlgCtrlID(window),Name=caption.ToString(),Class=kind.ToString(),Visible=IsWindowVisible(window),PasswordSkipped=password};
 }
 public static Node[] Windows(uint process) {
  var result=new List<Node>();Visitor callback=delegate(IntPtr window,IntPtr parameter){uint owner;GetWindowThreadProcessId(window,out owner);if(owner==process)result.Add(Read(window));return true;};
  EnumWindows(callback,IntPtr.Zero);return result.ToArray();
 }
 public static Node[] Controls(long root,uint process) {
  uint owner;GetWindowThreadProcessId(new IntPtr(root),out owner);if(owner!=process)throw new Exception("UI owner changed");
  var result=new List<Node>();Visitor callback=delegate(IntPtr window,IntPtr parameter){result.Add(Read(window));return true;};
  EnumChildWindows(new IntPtr(root),callback,IntPtr.Zero);return result.ToArray();
 }
 static void FindMenu(IntPtr menu,string path,List<uint> result) {
  for(int index=0;index<GetMenuItemCount(menu);index++) {
   var caption=new StringBuilder(1024);GetMenuString(menu,(uint)index,caption,1024,0x400);
   string next=path+"/"+caption.ToString().Replace("&","");
   if(next=="/Edit/Controller Properties")result.Add(GetMenuItemID(menu,index));
   IntPtr sub=GetSubMenu(menu,index);if(sub!=IntPtr.Zero)FindMenu(sub,next,result);
  }
 }
 public static uint PropertiesCommand(string resourceFile) {
  IntPtr module=LoadLibraryEx(resourceFile,IntPtr.Zero,0x22);if(module==IntPtr.Zero)throw new Exception("Resource load failed");
  try {IntPtr menu=LoadMenu(module,new IntPtr(101));if(menu==IntPtr.Zero)throw new Exception("Main menu resource missing");
   try {var result=new List<uint>();FindMenu(menu,"",result);if(result.Count!=1)throw new Exception("Unambiguous Properties command required");return result[0];}
   finally {DestroyMenu(menu);}
  } finally {FreeLibrary(module);}
 }
}
'@
function Pump-Capacity([int]$Milliseconds) {
 $until=[DateTime]::UtcNow.AddMilliseconds($Milliseconds)
 while([DateTime]::UtcNow -lt $until){[System.Windows.Forms.Application]::DoEvents();Start-Sleep -Milliseconds 10}
}
$resourceFile=Join-Path ([IO.Path]::GetDirectoryName($StudioPath)) 'LogixACENU.dll'
$command=[FraktalCapacityUi]::PropertiesCommand($resourceFile)
$started=[DateTime]::UtcNow.ToString('o')
$gui=$null;$hook=[IntPtr]::Zero;$frame=$null;$properties=$null;$snapshots=@();$failure=$null;$offline=$false
try {
 $gui=Start-Process -FilePath $StudioPath -ArgumentList @('"'+$review+'"') -WindowStyle Hidden -PassThru
 $hook=[FraktalCapacityUi]::SetWinEventHook(0x8002,0x8002,[IntPtr]::Zero,[FraktalCapacityUi]::Keeper,[uint32]$gui.Id,0,0)
 if($hook -eq [IntPtr]::Zero){throw 'Background UI visibility hook failed'}
 $deadline=[DateTime]::UtcNow.AddSeconds(30)
 do {
  Pump-Capacity 100
  $capacityMatches=@([FraktalCapacityUi]::Windows([uint32]$gui.Id)|Where-Object {
    $_.Name -match ('^Logix Designer - .* in '+[regex]::Escape([IO.Path]::GetFileName($review))+' \[1756-L81E 38\.') })
  if($capacityMatches.Count -gt 1){throw 'Ambiguous review window'}
  if($capacityMatches.Count -eq 1){$frame=$capacityMatches[0]}
 } while($null -eq $frame -and [DateTime]::UtcNow -lt $deadline -and -not $gui.HasExited)
 if($null -eq $frame){throw 'Pinned v38 L81E review window did not open in our process'}
 $frameControls=[FraktalCapacityUi]::Controls($frame.Handle,[uint32]$gui.Id)
 $offline=@($frameControls|Where-Object {$_.Class -eq 'Button' -and $_.Name -eq 'Offline' -and $_.Id -eq 1000}).Count -eq 1
 if(-not $offline){throw 'Review must be offline before Properties'}
 if(-not [FraktalCapacityUi]::PostMessage([IntPtr]$frame.Handle,0x111,[IntPtr]$command,[IntPtr]::Zero)){throw 'Properties command failed'}
 $deadline=[DateTime]::UtcNow.AddSeconds(10)
 do {
  Pump-Capacity 100
  $capacityMatches=@([FraktalCapacityUi]::Windows([uint32]$gui.Id)|Where-Object {$_.Class -eq '#32770' -and $_.Name -like 'Controller Properties - *'})
  if($capacityMatches.Count -gt 1){throw 'Ambiguous controller Properties dialog'}
  if($capacityMatches.Count -eq 1){$properties=$capacityMatches[0]}
 } while($null -eq $properties -and [DateTime]::UtcNow -lt $deadline)
 if($null -eq $properties){throw 'Controller Properties did not open'}
 $tabs=@([FraktalCapacityUi]::Controls($properties.Handle,[uint32]$gui.Id)|Where-Object {$_.Class -eq 'SysTabControl32' -and $_.Id -eq 12320})
 if($tabs.Count -ne 1 -or [FraktalCapacityUi]::SendMessage([IntPtr]$properties.Handle,0x465,[IntPtr]9,[IntPtr]::Zero).ToInt64() -ne 1){throw 'Qualified Capacity page selection failed'}
 Pump-Capacity 250
 for($sample=0;$sample -lt 2;$sample++) {
  $controls=[FraktalCapacityUi]::Controls($properties.Handle,[uint32]$gui.Id)
  $standard=@($controls|Where-Object {$_.Class -eq '#32770' -and $_.Name -eq 'MemCapacityDlg_Standard'})
  $page=@($controls|Where-Object {$_.Class -eq '#32770' -and $_.Name -eq 'Capacity'})
  if($standard.Count -ne 1 -or $page.Count -ne 1){throw 'Standard Capacity controls missing or ambiguous'}
  $snapshots += [PSCustomObject]@{CapturedUtc=[DateTime]::UtcNow.ToString('o');PageName=$page[0].Name;StandardParent=$standard[0].Handle;Controls=@($controls|Where-Object {$_.Parent -eq $standard[0].Handle})}
  Pump-Capacity 250
 }
} catch {$failure=$_.Exception.Message}
finally {
 if($null -ne $gui -and -not $gui.HasExited) {
  if($null -ne $properties){[void][FraktalCapacityUi]::PostMessage([IntPtr]$properties.Handle,0x111,[IntPtr]2,[IntPtr]::Zero);Pump-Capacity 200}
  if($null -ne $frame){[void][FraktalCapacityUi]::PostMessage([IntPtr]$frame.Handle,0x10,[IntPtr]::Zero,[IntPtr]::Zero)}
  $deadline=[DateTime]::UtcNow.AddSeconds(5)
  while(-not $gui.HasExited -and [DateTime]::UtcNow -lt $deadline){Pump-Capacity 100}
  if(-not $gui.HasExited){$failure=([string]$failure+'; our review process did not close normally').Trim('; ')}
 }
 if($hook -ne [IntPtr]::Zero){[void][FraktalCapacityUi]::UnhookWinEvent($hook)}
}
$sourceAfter=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
$report=[PSCustomObject]@{Schema='fraktal.ab.studio-capacity-capture';SchemaVersion=1;Offline=$offline;SourceAcd=$source;SourceSha256=$sourceHash;SourceSha256After=$sourceAfter;ReviewCopy=$review;ReviewInitialSha256=$sourceHash;StudioPath=$StudioPath;StudioSha256=(Get-FileHash -LiteralPath $StudioPath -Algorithm SHA256).Hash;MenuResource=$resourceFile;MenuResourceSha256=(Get-FileHash -LiteralPath $resourceFile -Algorithm SHA256).Hash;PropertiesCommand=$command;ProcessId=if($null -ne $gui){$gui.Id}else{0};ProcessClosed=($null -ne $gui -and $gui.HasExited);FrameTitle=if($null -ne $frame){$frame.Name}else{''};StartedUtc=$started;FinishedUtc=[DateTime]::UtcNow.ToString('o');Snapshots=$snapshots;Error=$failure}
$report|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $OutputPath -Encoding UTF8
$report|Select-Object Schema,Offline,SourceSha256,ProcessId,ProcessClosed,Error|ConvertTo-Json -Compress
if($failure -or $sourceAfter -ine $sourceHash){exit 1}
