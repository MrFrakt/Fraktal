# Line extension alarm-memory correction — prepared press75

Client date: 2026-10-04, America/Bogota. Parent: `70b4120`. Target:
192.168.100.89, serial 7036B510, 1769-L24ER-QB1B firmware 33.014.
Press70 remains the last owner-confirmed completed-download fit baseline.
This record prepares press75; it does not establish native fit or Line acceptance.
The earlier [allocation/step-entry correction](AB_LINE_V2_LINK_MEMORY_FIX_2026-10-04.md)
and [validator correction](AB_LINE_V2_VALIDATE_MEMORY_FIX_2026-10-04.md) remain unchanged.

## Failure and owner estimate

The new owner log contains verification, compilation, tag/routine transfer and
all named routine linking lines, including SequenceMarkStep, then a final
generic out-of-memory error and cancelled download (one error, zero warnings).
It does not name the imported file. The workflow requested press73; no completed
download is confirmed. The owner subsequently reports Capacity Estimate for
the requested offline build 73:

| Area | Total bytes | Estimated maximum used | Estimated remaining |
| --- | ---: | ---: | ---: |
| I/O | 1,048,576 | 2,640 | 1,045,936 |
| Data and logic | 786,432 | 799,428 | -12,996 |

The estimate identifies the data/logic deficit; it is an owner report, not an
agent Studio read or a press75 estimate. Spare I/O capacity does not resolve it.
Native tags following cancelled downloads cannot prove operative compiled code.

## Correction scope

Press75 keeps all requested features and reduces repeated native code:

- One generated program-local AlarmOpen body searches the bounded active list,
  initializes clock/shelving/counts using existing private AlmI/AlmSlot scratch,
  and returns the selected slot. A full list marks Truncated and overwrites
  nothing. Callers still supply reason, source, reset class, priority and roles.
- One AlarmClose body copies the selected event into the bounded ring, wraps
  the head and releases the slot. Existing callers retain gone-time/reset-class
  rules, including closing active manual events and WAIT_RESET on operator reset.
- CASE labels with equal rationalized priority share their assignment; every
  registered reason retains its priority and unknown reasons still default HIGH.
- Never-written and rejected startup records share one default installation;
  only rejected nonzero versions raise loss. Intact images and later scans keep
  their commissioned values and acknowledgement policy.

XML comparison with press73 finds only Main changed and AlarmOpen/AlarmClose
added. All other routines, native UDT layouts, tags/initializers, AOIs, tasks and
I/O modules compare equal. No new data tag, schema or write surface is introduced.
All ST/SFC/LD renditions, four users, model banks, Line history, permissions,
freshness and controller-owned chart history remain. Service call timing still
needs native S3 proof; offline equivalence is not a task-time measurement.

## Exact artifact and trends

File: **`C:/work/press75.L5X`**, SHA-256
`82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5`. Independent generation is byte-identical.
Manifest remains `94E302F650BA1DB5` / revision 9757442, major 4 / binding 2,
65,552 bytes; Fields 616/624 and Localization 652/664, valid/untruncated.
The contract hash cannot distinguish these code-only builds.

| Generation trend | Accepted press70 | Failed-workflow press73 | Prepared press75 |
| --- | ---: | ---: | ---: |
| Declared supported data bytes | 109,324 | 107,512 | 107,512 |
| ST source bytes | 291,816 | 280,707 | 260,844 |
| ST terminators | 4,538 | 4,331 | 4,091 |
| ST lines | 5,569 | 5,401 | 5,156 |
| RLL rungs | 20 | 20 | 20 |

Press75 removes 19,863 source bytes, 240 terminators and 245 lines from press73.
It adds no declared data. **These trends do not predict compiled savings or
prove fit against the 12,996-byte deficit.** Obtain a new Studio Capacity Estimate
after exact-artifact import/Verify, before another full download. Record both
areas and remaining headroom; do not grow another controller-storage feature
until completed linking and restored native results establish the next baseline.

Two fresh independent exact-serial read-only captures agree with the native
header checked before/after each. All four models/banks (M-100, M-200, M-050,
M-101), ordinal 1 and current Line/config records are preserved. Capture SHA:
`4BD511A1CDF82C8ECEFDFCA5219B0EED162C228561668B15B3C532467F528076`.
No credential/session/class-provider or runtime history is captured; generated
configuration seeding does not establish provider upgrade retention.

## Checks and next gate

**1,599 AB tests pass** in 216.800 seconds, including the full
three-rendition cycles, alarm behavior, schema restore and independent calendar
oracle. New simultaneous-fault/health/reset/reuse assertions preserve event
identity and counts. Fixtures execute the actual emitted zero-parameter JSR
bodies in caller storage/order; they do not replace the service with Python logic.

An independent comparison uses the prior committed generator and confirms its
alarm body is the exact text emitted in press73. Across 384 mixed alarm scans,
published active/ring/Unit/shelf state is equal. Across 512 startup images
(zero/current/unknown/negative schemas, first and later scans), station/model
values and loss/acknowledgement state are equal. Private AlmSlot may differ after
reset; it has no published value and does not change caller loop state.
Eight distinct service mutants fail assertions with no interpreter errors:
overwrite an open event, omit full indication, lose the active count, retain a
stale shelf, lose a ring reason, fail to release a slot, copy the wrong event,
and fail to wrap the ring. The earlier failed private mutation attempt is
retained; the final wrap mutant keeps indexes valid and is killed by an assertion.

Root tests pass 33/33; consistency is 0 errors/0 warnings. Shared HMI/gateway
source remains unchanged from the tested/deployed Line client; this controller
correction needs no client redeployment.

The exact press75 SDK attempt refuses `No valid license` before conversion
(exit 3762504530), creates no ACD, contacts no controller and leaves the input
hash unchanged. The owner must perform Studio Verify/Capacity Estimate and,
after the budget is resolved, completed full download. Then restart the existing
gateway/hard-refresh Chrome and establish restored native regressions, timing,
Line boundaries/history/retention and browser acceptance before the next stage.

The agent made no PLC writes/downloads, mode/fault/clock changes or gateway
restart. The [JSON record](AB_LINE_V2_ALARM_MEMORY_FIX_2026-10-04.json), SHA-256
`2BA121E568872963DB410716FCDBE5D49A2F50F182791082ADEB97E8206231F4`, binds owner evidence, estimate, captures, exact artifact,
source/check/log hashes and pending gates. The AB new-project guide and TC3
handoff now carry this correction and its native acceptance boundary.

## Appended restore-coverage check

The first comparison matrix used schema values 0, 4, 99 and -1 for every
record. Model schema 4 was covered, but StationCfg current schema is 3. A
fresh comparison uses each record's own current version, including StationCfg
3, and again passes all 512 startup images plus 384 mixed alarm scans. It also
asserts that the previous restore body exactly matches press73 Main. This
extends coverage without changing generator/artifact bytes or the earlier
record. The [recheck JSON](AB_LINE_V2_ALARM_RESTORE_RECHECK_2026-10-04.json), SHA-256
`EF2716A129FF9A212628BCA6CB90B13E577CB4D8B0ECDE6AF2FB29A5909877BF`, records the corrected matrix.
