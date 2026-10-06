# Line extension link-memory correction — prepared press73

Client date: 2026-10-04, America/Bogota. Parent: `0268cbe`. Target:
192.168.100.89, serial 7036B510, 1769-L24ER-QB1B firmware 33.014.
Press70 remains the last owner-confirmed completed-download fit baseline.
This is offline preparation, not acceptance of press73. Earlier
[Line preparation](AB_LINE_V2_PREPARED_2026-10-04.md),
[ownership checks](AB_LINE_V2_OWNERSHIP_CHECK_2026-10-04.md) and
[validator correction](AB_LINE_V2_VALIDATE_MEMORY_FIX_2026-10-04.md) remain unchanged.

## Owner log and correction scope

The owner supplied a complete Studio download log after the press72 request.
It does not name the L5X file. Every routine verifies and compiles, all tags and
routines download, then linking fails at `FRK_Press_LineValidate`, cancels the
download and reports one out-of-memory error. This establishes the failing
stage; it does not establish a completed download. Shrinking that validator
alone did not resolve the combined image budget.

Press73 reduces both discovery data and repeated native code:

- Fields/Localization reserve eight rows rounded to eight-row blocks, within
  the existing 768 ceilings. Other discovery tables reserve one row rounded to
  small blocks within their frozen ceilings; Modules/Nameplates share a bound.
  All declared rows still fit. Overflow and the whole-byte budget still refuse
  generation, and readers check capacities independently of the logical hash.
- Each program ST/SFC step calls one generated owner-local `SequenceMarkStep`
  routine at its original entry point. It maintains the cursor, visits/entry
  count, clock, epoch/discovery rows and warning reset. AOI-inline steps keep
  the same common body; AOIs do not call project routines. Native LD is unchanged.

All three renditions, PLC chart history, four users, Line rows/history,
permissions and calendar validation remain. No released UDT layout, AOI,
task or I/O module changes from press72. XML comparison finds only AUTO ST/SFC
changed and one routine added; only the manifest header and its nine array
initializers/dimensions change among controller tags. Other tag initializers
compare equal. There is no new private tag or client accumulation.

## Exact image and size trends

File: **`C:/work/press73.L5X`**, SHA-256
`96CF4319E8438D5045EE5FDBAE339D39A9AA75606212DF2542810B3D598DC55E`.
Generation and an independent verification output are byte-identical.
Manifest remains `94E302F650BA1DB5` / revision 9757442, major 4 / binding 2,
now 65,552 bytes; Fields 616/624, Localization 652/664, valid/untruncated.
Capacity changes preserve logical identity; the exact artifact/full-download
confirmation is still required. An old allocation with that hash is refused.

| Generation trend | Accepted press70 | Failed-workflow press72 | Prepared press73 |
| --- | ---: | ---: | ---: |
| Declared supported data bytes | 109,324 | 112,480 | 107,512 |
| ST source bytes | 291,816 | 304,595 | 280,707 |
| ST terminators | 4,538 | 4,783 | 4,331 |
| ST lines | 5,569 | 5,887 | 5,401 |
| RLL rungs | 20 | 20 | 20 |

Press73 frees 4,968 declared data bytes and 452 ST terminators from press72.
It is also 1,812 data bytes, 11,109 source bytes and 207 terminators below
accepted press70. **These trends are not compiled memory or proof of fit.**
The current template manifest similarly falls to 46,080 bytes; this is offline
allocation evidence, not native acceptance of another station.

Two fresh, independent exact-serial read-only captures agree, with the same
native header before/after. They preserve current records/Line configuration,
ordinal 1 and all four model codes/banks: M-100, M-200, M-050, M-101. Image SHA:
`4BD511A1CDF82C8ECEFDFCA5219B0EED162C228561668B15B3C532467F528076`.
No credentials/session/class policy or runtime history are captured, and no
provider upgrade-retention claim is made. Native tags from a cancelled download
are not evidence of operative compiled code.

## Checks and next gate

**1,597 AB tests pass**, including full ST/SFC/LD cycles and PLC chart behavior.
The expanded final capacity checks also pass for every emitted table, refusing
overflow and old capacity mismatches despite matching logical hashes. The
offline ST instrument now executes supplied native zero-parameter JSR bodies
in caller storage/order and refuses missing bodies or unsupported parameters.
No test substitutes a separate Python implementation for the shared service.

Seven distinct step-entry mutants fail assertions without interpreter errors:
lost visits, repeated entry, lost clock origin, repeated row discovery, stale
warnings, lost active step and lost elapsed time. The existing 12 Line mutants
are rerun and killed; all 2,020 calendars still agree with the independent
interval oracle. Root tool tests pass 33/33 and consistency is 0 errors/0 warnings.
HMI source remains identical to the tested/deployed Line release (495 passes,
seven expected environment skips, clean analyzer/release build); no redeployment
is needed for this controller correction.

The exact press73 SDK attempt refuses `No valid license` before conversion
(exit 3762504530), creates no ACD, contacts no controller and leaves its input
hash unchanged. Owner Studio Verify **and completed full download** remain the
fit gate. After success, restart the existing gateway and hard-refresh Chrome;
then establish restored native Line/sequence/task-timing results and browser/
retention evidence before adding another controller-storage feature.

The agent made no PLC writes, downloads, mode/fault/clock changes or gateway
restart. The [JSON record](AB_LINE_V2_LINK_MEMORY_FIX_2026-10-04.json) binds the
owner log, capture, exact artifact, size comparisons, source/log hashes,
checks/mutants and pending native gates.
