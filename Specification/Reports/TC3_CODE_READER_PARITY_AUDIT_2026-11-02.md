# Code reader and vision CM parity audit (TC3), 2026-11-02

**Status:** paper audit, no code changed (L8 of
[the remaining-library plan](TC3_GENERIC_CM_LIBRARY_PLAN_2026-10-29.md)). It compares the
TCP/ASCII device categories with four things a station commonly needs from a code reader:
bounded read retries, a quality grade, configuration download and multi-code reads. It
says, for each gap, which type should own the fix. **Implementation waits for a station
that needs it (plan decision D3).** Nothing here is normative; Part I §3.15.1a stays the
authority.

Sources audited (paths relative to `FraktalCore/PLC/TwinCAT/Framework/`):

| Type | Role | File |
|---|---|---|
| `FB_AsciiDeviceCM` | ASCII request/response base: framing, one outstanding request, response timeout ⇒ `DEV_RESP_TIMEOUT` (10402), bounded reconnect | `Fraktal_Core/BaseClasses/FB_AsciiDeviceCM.TcPOU` |
| `FB_TcpCodeReaderCM` | category: trigger, no-read token, optional match code | `Fraktal_Core/DeviceCMs/FB_TcpCodeReaderCM.TcPOU` |
| `FB_TcpVisionCM` | category: trigger, OK/NG prefixes, result payload | `Fraktal_Core/DeviceCMs/FB_TcpVisionCM.TcPOU` |
| `FB_Matrix220CM` | model preset of the code reader (strings only) | `Fraktal_Modules/FB_Matrix220CM.TcPOU` |
| `FB_Iv3VisionCM` | model preset of the vision CM (strings only) | `Fraktal_Modules/FB_Iv3VisionCM.TcPOU` |

Tests today: `FB_TcpDev_Tests` — `Vision_configured_parses`, `Reader_code_and_match`,
`Timeout_faults_10402`, `Model_presets_apply_configuration`.

## 1. What the categories do today

- **Code reader.** `TRIGGER` (§7.6.1 catalog value 1) sends `ParCfg.TriggerCmd` and waits
  for one terminated reply. A reply equal to `ParCfg.NoReadText` sets `OutCmd.NoRead`;
  anything else is the decoded symbol in `OutCmd.Code` (one `STRING(255)`). With
  `ParCmd.MatchCode` set, `OutCmd.MatchOk` compares the whole reply with it. A no-read
  completes the command (Done, not Error): the owner decides what a no-read means.
- **Vision.** `TRIGGER` sends `ParCfg.TriggerCmd`; a reply starting with `OkPrefix` or
  `NgPrefix` sets `OutCmd.JudgeOk`, the rest after `ResultSep` goes to `OutCmd.ResultData`
  verbatim; any other reply faults `DEV_PROTOCOL` (10403).
- **Both.** Silence beyond `RespTimeout` faults 10402; a down channel faults or refuses
  (10401/10404); reconnect is bounded with doubling backoff. Protocol strings are `ParCfg`
  (§3.8-able), verified against the device manual, never hard-coded beyond the presets.

## 2. Gaps

| # | Need | Today | Gap | Owner | Shape (when built) |
|---|---|---|---|---|---|
| 1 | **Read retries, bounded** | one trigger, one reply; a no-read completes | an owner wanting "try three times" writes a retry loop in its sequence, per station | `FB_TcpCodeReaderCM` | `ParCfg.ReadRetries : INT` (0 = today's behaviour, bounded e.g. 0..5, `PrepareRecipe` refuses outside); re-trigger on no-read inside the command; `OutCmd.Attempts`. A no-read after the last attempt stays a **result** (`NoRead`), not a fault — the owner decides, as it does today |
| 2 | **Quality grade, value and text** | none: the reply is the code or the no-read token | readers that append a grade (e.g. an ISO/IEC 15415/15416 overall grade) have it folded into `Code`, so `MatchOk` fails and traceability stores the grade as part of the symbol | category: `FB_TcpCodeReaderCM`; format: the model preset | category fields `OutCmd.Grade : INT` (0 = not reported) and `OutCmd.GradeText : STRING(8)`, split by a configured `ParCfg.GradeSep` (empty = no grade, today's behaviour). A device whose grade format differs overrides `_M_OnResponse` in its preset — the documented extension point. An optional `ParCfg.MinGrade` turning a low grade into `MatchOk := FALSE` belongs to the category |
| 3 | **Configuration download** (select a job/program on changeover) | none, in either category | changeover cannot select the device job that belongs to the model; stations do it by hand or by a project command | `FB_AsciiDeviceCM` (shared by both categories, written once, §1.1 O9) | a second catalog command `SELECT_JOB` sending `ParCfg.JobCmd` with the job id from the model's `ParCfg.JobId`, acknowledged by a configured token, faulting `DEV_PROTOCOL` otherwise. It is a **command the changeover sequence issues after `CommitRecipe`**, never work done inside `CommitRecipe` (Part I §3.8 atomic changeover: commit performs no validation or I/O) |
| 4 | **Multi-code reads** (several symbols per trigger) | one `STRING(255)` | a reader returning several codes in one reply delivers them concatenated; match and traceability cannot tell them apart | `FB_TcpCodeReaderCM` | `ParCfg.CodeSep` (empty = single code, today's behaviour) and `OutCmd.Codes : ARRAY[1..N] OF STRING(n)` with `CodeCount`, N a `PL_` constant sized by the first consumer; `MatchOk` then means "every expected code present". Parsing must copy bytes, not chain `CONCAT`/`FIND` (lint C9: the string functions stop at 255 characters) |
| 5 | Vision: program/job switch | none | same as #3 | `FB_AsciiDeviceCM` | covered by #3 |
| 6 | Vision: structured result | `ResultData` verbatim | a station parses the payload itself | stays project/preset | **no change proposed**: result payloads are device- and job-specific; the preset's `_M_OnResponse` is the place, and the category stays generic |

## 3. What should not change

- **No new type.** Every gap is a configurable extension of an existing category
  (plan decision D3: extend, do not add). A model preset stays strings plus, at most, a
  `_M_OnResponse` override.
- **A no-read is a result, not a fault.** The category reports; the owner decides
  (fault, rework, retry the part). Retries (#1) narrow when that decision is needed;
  they do not move it into the reader.
- **Every new member defaults to today's behaviour**, so a station that sets none of them
  sees no change; each is a `ParCfg` schema step (stored records refused until saved again,
  migrate-or-fault §3.8), stated in the version step that ships it.
- **Reasons.** The device band 10401–10499 has room; a code a gap needs (for example
  "job selection not acknowledged") is registered there by the change that raises it, not
  in advance.

## 4. Tests a change would add

`FB_TcpDev_Tests` over `FB_SimByteChannel` (no socket, no hardware): a no-read retried
then read (#1, attempts counted, bound respected, no fault on final no-read); a graded
reply split into code and grade, and a below-minimum grade failing the match (#2); a job
selection acknowledged and one refused with 10403 (#3); a multi-code reply split, counted
and matched, including one longer than 255 characters (#4).
