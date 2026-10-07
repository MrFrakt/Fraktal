# Native x32 XAE repair and full builds — 2026-10-05

Both Core 0.23.0.0 and Modules 0.11.0.0 were checked, saved and installed by
the **actual 32-bit XAE Shell, TcXaeShell.DTE.15.0**, from 32-bit PowerShell.
The earlier DTE18/x86-target acceptance was a different host; it remains dated
evidence and is not substituted for this run.

The installed Modules entry had reverted to the earlier blob without Core.
That blob's SHA-256 exactly matched the exported
`Framework/Release/x32/Fraktal_Modules.library` (FC061F77…09D0CD). Reinstalling
that stale export would reproduce the dependency failure. Both x32 exports and
the canonical `Release` exports now contain the freshly checked libraries and
match their installed repository blobs. Prior exports and installed entries are
backed up in `artifacts/press-x32-ide-repair`.

Added legacy `.sln` wrappers for each library, derived from the existing `.slnx`
project identities and pointing at the same single-library `.tsproj` files.
The x32 installer selects those wrappers for DTE15. Press retains fixed Core /
Modules resolutions and the owner's namespace/reference ordering. Source and
installed libraries were never loaded together in one solution.

Native Press object checks pass for **TwinCAT RT (x86)** and **TwinCAT RT (x64)**.
Full offline builds also pass for both, with LastBuildInfo=0 and the compiler's
`ready for download` message. Generated code/global data/allocated code+data:

| PLC target | Code bytes | Global data bytes | Allocated bytes |
|---|---:|---:|---:|
| x86 | 562,302 | 2,174,385 | 3,077,488 |
| x64 | 603,444 | 2,143,569 | 3,151,696 |

IDE bitness and PLC target architecture are separate choices. The existing
Press system wrapper declares a 64-bit target; no target architecture or net ID
was changed in the original project. These builds used isolated copies of its
current source/configuration. Neither a runtime configuration nor an application
was activated/downloaded; no physical I/O or runtime license acceptance is claimed.

Both builds still emit the two known TMC credential-persistence warnings for
hidden `_users`/`_n` (IMPLEMENTATION_NOTES §154). They are not library-resolution
or license errors and were not hidden by weakening credential symbol exclusion.
The x32 Output pane needed typed EnvDTE TextDocument/TextPoint/EditPoint dispatch;
the shared diagnostics helper now captures its actual compiler/code-generation
transcript. Initial startup RPC rejection attempts remain in local artifacts;
the successful x86 retry used the maintained OLE message filter.
