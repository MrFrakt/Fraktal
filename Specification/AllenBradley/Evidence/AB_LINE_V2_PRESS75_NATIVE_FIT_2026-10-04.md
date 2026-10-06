# Press75 completed download, memory and initial native checks

Client date: 2026-10-04, America/Bogota. Source commit `1528eab`. The owner
supplies a Studio screenshot titled `FraktalPhase0 in press75.ACD`, showing
successful final download, zero errors/warnings, 15.059 seconds at connection
size 1500. The screenshot initially shows Rem Prog; the owner then confirms
"plc was in program mode, it is on run mode now, build 75". No agent download
or mode change is performed. The login timeout image supplied between these
messages does not establish a credential failure while the task was stopped.

The successful fit baseline advances to `C:/work/press75.L5X`, SHA-256
`82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5`.
This is a fit/read-only result, not full regression or Line acceptance.
The earlier [failed-build/preparation record](AB_LINE_V2_ALARM_MEMORY_FIX_2026-10-04.md)
is unchanged; press70's [159-row proof](AB_PHASE6_PRESS70_NATIVE_ACCEPTANCE_2026-10-04.md)
remains scoped to that older artifact.

## Capacity visible in the owner screenshot

| Area | Total bytes | Used | Maximum used | Available | Largest free block |
| --- | ---: | ---: | ---: | ---: | ---: |
| I/O | 1,048,576 | 2,976 | 3,184 | 1,045,600 | 1,045,392 |
| Data/logic | 786,432 | 758,568 | 758,568 | 27,864 | 27,376 |

Data/logic headroom is about 3.54%, so future controller-storage stages remain
budgeted against this exact native baseline. This is owner-visible Capacity
data; the L24ER does not gain a CPU/free-memory GSV source. The earlier 799,428
value is an offline estimate for failed-workflow press73. Its difference from
this online used value is not claimed as a directly measured compiled saving.

## Read-only native proof in Run

Exact serial 7036B510 is guarded before reading. Full manifest comparison is
coherent/equal, logical hash 94E302F650BA1DB5 / revision 9757442, with all actual
capacities matching the current declaration. ScanCount advances 25 in 250 ms.
All captured records, active ordinal 1 and all four model codes/banks (M-100,
M-200, M-050, M-101) equal the pre-download commissioned image.

Read-only S3 passes 6/6. Maximum observed task scan is 7,679 us against 10,000 us;
there is no task overlap or major/minor fault. Time is unsynchronized and is
reported as such. The PLC publishes admin level 4 with LoginBusy/LoginFailed 0.
Line V2 is initialized at unscheduled index 0, with an empty/default calendar
and no history; that is not a weekly-boundary or calendar-write proof. All three
gateway health routes answer 200 with plcReady true at this initial check.

## First verification attempt and restoration

The invoked Phase 6 handover workflow authorizes the fixed verification tag
writes after owner download confirmation. The shelving run passes every one of
its 15 assertion rows, but its original-session cleanup times out waiting for
its own login-result sequence. It is recorded as an overall failure, not 15/15
native acceptance. Exact identity guards check all 131 writes and block none.
Independent outer cleanup/readback restores session, policy/classes, timeout,
mode/style, fixture inputs, station data, all model banks/catalog and Line calendar.
The task remains below period without faults or overlap (max 7,865 us).

A diagnostic request is consumed as sequence 109 but observes result sequence
105 with no busy/failure; no authoritative result for that request is proved.
A subsequent instrumented request and 20 further requests each settle with
their own sequence. Existing admin/session is left restored. Concurrent HMI
queries sharing the same native mailbox are a hypothesis; the original trace
does not prove a cause. A fresh retry will isolate HMI tabs and check for an
already-consumed sequence immediately before commit, rather than accepting a
stale ACK. Failed files remain retained. No credential hash/PIN is disclosed.

The idle gateway health later reports degraded after the failed fixture; this
is retained and is not silently turned into a ready claim. Final readiness
requires a fresh complete read. No freshness limit is relaxed or gateway restarted.

## Remaining gate

Fit is accepted. Full restored regressions, native Line calendar transactions,
boundaries/history, Chrome controls and physical retention remain pending.
HMI tabs must be isolated for the direct native apparatus; the production HMI
normally shares the gateway's one serialized writer. Stop growth into Part
storage until these gates establish the next accepted behavioral baseline.

The [machine record](AB_LINE_V2_PRESS75_NATIVE_FIT_2026-10-04.json) binds owner
observations, native reads, failed assertion/cleanup scope, guarded restoration,
trace files/hashes and pending gates. No previous evidence or failed result is
rewritten to match this download.
