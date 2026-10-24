# Echo startup after Windows reboot — 2026-10-24

**The host reboot completed; the virtual controller still fails during startup.**
This continuation performed read-only checks and exported selected logs and crash
metadata. It made no controller-changing operation. The already approved S3h
diagnostic session has not begun, and its approval remains recorded and unused.

| Check | Observed result |
|---|---|
| Windows last boot | 2026-10-24 06:25:37.500 UTC (00:25:37.500 America/Mexico_City) |
| Echo service | Running, version 4.0.1437; personalized license active |
| Automatic controller startup | 06:26:38 UTC; emulator exits with code 1 at 06:26:46 UTC |
| Target | GUID 91dec7d6-8ac3-45c9-ab2e-0d039c7006fd, serial 601FC87B, 127.0.0.1, slot 0, v38.011 |
| SDK post-state | Enabled, ClosedExternally, RemoteProgram, Remote, not faulted |
| Native emulator / TCP 44818 listener | Absent / absent |
| Native exception | 0xC0000005, libComms.dll +0x50C2A4, parameters [0, 0] |
| S3h diagnostic upload/download/tag writes | Not started / not started / zero |
| Agent power changes / mode commands / fault clears / clock changes | 0 / 0 / 0 / 0 |

The fresh native dump has a new timestamp (06:26:46.869812 UTC), fault thread
21232 and size 1,035,743,890 bytes. Its exception code/module offset and seven
libComms frame offsets match the preceding authorized restart failure:
50C2A4, 53068B, 5306B4, 36BC94, 465761, 23DF2E and AB024. This is an x86
EBP-chain observation without private vendor symbols. It confirms recurrence,
not the underlying cause. Neither ASLR nor retained-state corruption is proved.

Controller SDK project/path strings are empty while no emulator is available;
they do not establish that the retained PLC image is empty. Controller definitions
and state files remain in the original vendor locations. The dump, power-down
image and credential files are not copied into the payload. Only bounded
exception/module metadata and frame-chain control addresses are exported.
State files have hashes/lengths/timestamps only. The initial metadata probe
looked in Root/FaultDump.dmp, which was absent; the existing reader correctly
finds the dump under sd/RockwellAutomation/601FC87B/Faults.

The installed local FactoryTalk Diagnostics SQLite buffer was opened with
mode=ro and query_only enabled. It contains zero rows. This does not establish
whether other Diagnostics Viewer destinations hold messages. The vendor's
full Data Collector was not run: its documented output includes controller
memory, while this report deliberately keeps the project and credentials out
of evidence payloads.

Rockwell's [Echo 4.00 release notes](https://compatibility.rockwellautomation.com/GeneratedReleaseNote.aspx?v1=66077)
recommend contacting technical support when an initialization problem persists
after host reboot. The [Getting Results Guide, chapter 4](https://literature.rockwellautomation.com/idc/groups/literature/documents/gr/9310-gr001_-en-p.pdf)
describes Diagnostics Viewer and support data collection. These sources do not
identify this particular libComms failure. The selected startup logs, version,
controller identity and repeated crash offsets are ready for vendor diagnosis.
No state reset, controller recreation or firmware/network/security setting
change was attempted or inferred from the earlier restart approval.

Verification and acceptance boundary:

- All 159 project source bindings and both diagnostic wrapper bindings match.
  The unused prepared ACD remains C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC.
- Existing exact-source 2,149 AB tests, two-target v38 builds/read-backs and 79%
  Capacity evidence are reused; no production code or PLC image changed.
- The spec, contracts and strict consistency gates, 74 root tests and whitespace
  check pass in the attached new logs. Flutter is not applicable; no HMI change.
- All 37 predecessor records / 8,576 artifacts are re-hashed by the payload seal.
- The original diagnostic approval call_b76d12f2f038411386f83c339fcd94e0:0 remains
  unused. Its original baseline guards stop execution before backup/download.
  The prior one-shot restart approval is already consumed and was not repeated.
- S3h's 41 candidate checks, native timing and current final baseline checks
  were not run. The previous 39 comparisons and 31 baseline checks remain
  historical evidence at their recorded scope. S3h is incomplete; V2 inactive.

Work folder: `C:/work/fraktal-ab-s3h-20261024/post_reboot_b6d021864c91435f80c99ff20c55ab2b`. New append-only
[payload manifest](AB_S3H_CANONICAL_ECHO_POST_REBOOT_2026-10-24/manifest.json). No commit or push.
