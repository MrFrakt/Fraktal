# Fraktal AB offline SDK probe

This non-production Phase 0 tool exercises the installed Logix Designer SDK
without connecting to a controller. It opens an existing ACD/L5K/L5X, reports
the saved communications path, optionally saves a new ACD or L5X, and proves
by SHA-256 that the input project did not change.

The executable intentionally exposes no upload, download, online, mode-change,
tag-write, fault-clear, or firmware operation. It refuses to overwrite an
existing export.

Prerequisites:

- .NET 10 SDK targeting the installed Rockwell client's 32-bit architecture;
- Logix Designer SDK 2.02 / C# client `2.2.1109` and its required activation; and
- the Rockwell C# NuGet package supplied with the SDK installation.

Restore with the installed Rockwell package directory plus NuGet.org, build the
required 32-bit target, then run:

```powershell
dotnet restore Fraktal.Ab.OfflineProbe.csproj -r win-x86 `
  --source 'C:\Users\Public\Documents\Studio 5000\Logix Designer SDK\dotnet' `
  --source 'https://api.nuget.org/v3/index.json'
dotnet build Fraktal.Ab.OfflineProbe.csproj -c Debug -r win-x86 --no-restore
bin\Debug\net10.0\win-x86\Fraktal.Ab.OfflineProbe.exe `
  C:\work\DisposableProject.ACD `
  --export C:\work\DisposableProject.L5X
```

The same isolated SDK path converts a complete generated controller L5X into
a new ACD for Studio Verify:

```powershell
bin\Debug\net10.0\win-x86\Fraktal.Ab.OfflineProbe.exe `
  C:\work\GeneratedProject.L5X `
  --export C:\work\GeneratedProject.ACD
```

Use only disposable copies when gathering readiness evidence. A successful
offline open/export proves SDK availability and source conversion capability;
it does not prove controller/project parity, online communications, S4
round-trip stability, S15 Build/Verify, or any runtime spike.
