# Echo re-download of the current source after host reboot — 2026-10-19

Append-only, non-normative evidence. The owner asked this session to "check if
the port is complete and then download it to the logix echo simulator", then
chose "Restore + 31 checks" for the post-download configuration restore and
acceptance. That authorization covers this session and this local Echo only;
it is historical afterwards. No fault clear, physical-controller operation,
clock, network or electrical output operation occurred.

Payload, hashes and logs: [`AB_ECHO_REDOWNLOAD_2026-10-19/manifest.json`](AB_ECHO_REDOWNLOAD_2026-10-19/manifest.json).
Source commit `a1163c7c7bec21988167bc971145b1366206e9ce`; the Allen-Bradley
tree was clean. No framework, generator or declaration code changed.

## Port status at this commit

The port is **not complete**; this run changes none of the open items in
[AB_PART_GENEALOGY_2026-10-19](AB_PART_GENEALOGY_2026-10-19.md) "Remaining
boundaries". Current source is healthy at its offline scope: 1,890 AB tool
tests, the AB specification and frozen-contract gates, strict cross-artifact
consistency (0 errors, 0 warnings), and 35 + 83 root tests all pass.

## Host state found

The host rebooted at 20:38. At 20:39 the FactoryTalk Logix Echo Service failed
to start: a 45 s service-control timeout (events 7009/7000). An unclean Echo
shutdown was also logged at 18:27. The service ACL grants start rights only to
SYSTEM and elevated Administrators, and the agent session was not elevated, so
the owner started the service. Echo had retained its program: manifest
`6DEC4C1DC2F7F78A`, advancing scan count, MANUAL/idle, logged out, and the Echo
API reported Run, not faulted, keyswitch Remote. No fault clear was required.

## Artifact

Declaration `fraktal_ab_genealogy_demo` regenerated from
`C:/work/echo38_5580_seed.L5X` (SHA-256 `FA96516C…C0C7`) to L5X SHA-256
`91BF67C9101EAE863CF29C1A9DF6413D7256AB056D985394587F0183AA525714`. This is
byte-identical to the image of the 10-19 02:00 download. Manifest major 5,
content hash `6DEC4C1DC2F7F78A`, configuration revision 7203916. The download
therefore replaced the image with the same build; it is not a new feature.

- v38 native build with read-back for EchoController and PhysicalController:
  clean logs; 42 executable bodies and 21,926 authored initial values equal.
- SDK-prepared ACD `966E931633AC70A0F9C01BFE6F12A3BD8B7E330A3C3A37F04E6FC28707ACEEDB`;
  its read-back is equivalent. ACDs embed save state, so this differs from
  earlier prepared ACDs of the same L5X.
- Pre-download upload backup ACD
  `89D0F23FA946F665EFB99823C8CA5759AE05F7AEB5FD492E2974219D242BC737`.

## Download

The same guarded shape as the 10-19 session was used: preflight (Unit
MANUAL/idle, no session, all five saved live documents equal to the
controller), backup, then CIP identity guard (`127.0.0.1`, slot 0, Emulate 5580,
product 288, firmware 38.11, serial `601FC87B`, listener owned by
`EmulateControlLogix5580`) before each mode change and before the download.
SDK 2.1.974: Program → Download → Run, all succeeded, zero SDK error events.
The post-download export equals the source: 42 bodies, 21,926 initial values,
21 SFC steps. The scan count restarted (1,905 → 1,930 in 250 ms). After the
download Save, the ACD is `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

## Restore and acceptance

The station reported `restoring` after the download, as Part III AB §3.8b
requires. `fraktal_ab_genealogy_execute.py` re-applied the five saved documents
through the controller's staged set path. `restoring` cleared and no document
was lost or rewritten. **31/31** tower/Part regressions passed across
ST/SFC/LD, 21 of them with genealogy checks. Inputs, mode, policy and login
were restored afterwards.

Final read-only checks pass. Echo is Run, not faulted, scanning, MANUAL/idle
and logged out, not restoring, and all five saved documents equal live.

## Not established

This run qualifies no new behavior. It does not establish why the Echo service
failed to start at boot, or restart tolerance after an unclean Echo shutdown.
It establishes no physical fit, retention or browser/gateway acceptance. The
Echo service start type and startup timeout were not changed.
