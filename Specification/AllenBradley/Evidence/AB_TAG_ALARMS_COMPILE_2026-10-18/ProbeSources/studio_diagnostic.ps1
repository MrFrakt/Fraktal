param([Parameter(Mandatory=$true)][string]$Project)
$ErrorActionPreference='Stop'
if (Get-Process -Name LogixDesigner -ErrorAction SilentlyContinue) { throw 'Existing Studio instance; refusing.' }
$path=(Resolve-Path -LiteralPath $Project).Path
if (-not $path.StartsWith('C:\work\fraktal-ab-tag-alarm-20261018\') -or [IO.Path]::GetExtension($path) -ine '.L5X') { throw 'Disposable L5X only.' }
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public class AlarmImportDiagnostic {
 public delegate bool EnumProc(IntPtr h,IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p,IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,EnumProc p,IntPtr l);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
 [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h,StringBuilder b,int n);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h,uint m,IntPtr w,StringBuilder l);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h,uint m,IntPtr w,IntPtr l);
 public static IntPtr FindMain(int pid) { IntPtr result=IntPtr.Zero; EnumWindows((h,l)=> { uint p; GetWindowThreadProcessId(h,out p); var b=new StringBuilder(1024); GetWindowText(h,b,b.Capacity); if(p==pid && b.ToString().StartsWith("Logix Designer -")) result=h; return true; },IntPtr.Zero); return result; }
 public static string Read(IntPtr main) { string result=""; EnumChildWindows(main,(h,l)=> { if(GetDlgCtrlID(h)==33652) { var b=new StringBuilder(65536); SendMessage(h,13,(IntPtr)b.Capacity,b); result=b.ToString(); } return true; },IntPtr.Zero); return result; }
}
'@
$exe='C:/Program Files (x86)/Rockwell Software/Studio 5000/Logix Designer/ENU/v38/Bin/LogixDesigner.Exe'
$hash=(Get-FileHash -LiteralPath $path).Hash
$owned=Start-Process -FilePath $exe -ArgumentList ('"{0}"' -f $path) -WindowStyle Hidden -PassThru
$deadline=(Get-Date).AddSeconds(120)
$main=[IntPtr]::Zero
do { Start-Sleep -Milliseconds 500; $main=[AlarmImportDiagnostic]::FindMain($owned.Id); $summary=if($main -ne [IntPtr]::Zero){[AlarmImportDiagnostic]::Read($main)} else {''} } until($summary -match 'Complete - \d+ error\(s\)' -or (Get-Date) -gt $deadline)
if($summary -notmatch 'Complete - \d+ error\(s\)') { throw "Import not completed; owned PID $($owned.Id) remains open." }
[IO.File]::WriteAllText($path+'.studio.txt',$summary)
$summary
[void][AlarmImportDiagnostic]::PostMessage($main,16,[IntPtr]::Zero,[IntPtr]::Zero)
if(-not $owned.WaitForExit(10000)){ throw "Close blocked; owned PID $($owned.Id) remains open." }
if($hash -ne (Get-FileHash -LiteralPath $path).Hash){throw 'Source changed.'}

