# Fresh-chat handover prompt — AB canonical publication

Copy the prompt below into a fresh chat working in `C:\Users\SoftIndVM\Fraktal`.
It describes the repository and bench as of 2026-10-20 at `a1163c7c7` plus
uncommitted work listed in the plan.

---

You are continuing the Allen-Bradley (Fraktal/AB) **canonical publication**
work. Goal: AB reaches the HMI the way TwinCAT and TIA do. The PLC publishes
the canonical Core module tree itself, and one generic session client
discovers it through the controller's Symbol and Template objects plus the
manifest, with **no station declaration at runtime**. The owner decided this
on 2026-10-19 ("having a coherent architecture along all implementations is
important") and retired the 1769-L24ER as a reference target.

## Read first, in this order

1. `AGENTS.md`, especially §3a (AB rules and the two questions you must ask)
   and §5.
2. `Specification/AllenBradley/AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md`:
   the decisions D1–D9 and the measured facts.
3. `Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md`:
   the stages S0–S7, the exact state at hand-over, the invariants and the
   risks. **Follow it; correct it if the code says otherwise, and say so.**
4. `Specification/Fraktal_AB_Part_III.md` §3.8, §3.10 and §11.
5. `Specification/Fraktal_TIA_Part_IV.md` §1 and §3.10. TIA is the reference
   for this architecture: generic `WebApiSessionClient`, roots found by a
   top-level `Status` member.
6. `Specification/OPCUA_TRANSPORT.md` (Snapshot, mailbox ordering, the ADS and
   S7 Web API sections) and `Specification/HMI_CONTRACT.md`.
7. `Specification/AllenBradley/Evidence/AB_ECHO_REDOWNLOAD_2026-10-19.md`:
   the guarded download procedure that S0 reuses.

## Current continuation state (2026-10-20)

**Latest, 2026-10-21: S3b runtime exit passes at 304 paths.** Read
[runtime evidence](Evidence/AB_S3B_CANONICAL_RUNTIME_2026-10-21.md) and
[the S3b notes](AB_CANONICAL_PUBLICATION_S3B_NOTES_2026-10-21.md).
Candidate/baseline regressions pass 31/31 each; four decisions, ten held and
four Unit first-out fault pairs cover ST/SFC/LD with unchanged same-scan proof.
The first acquisition failure and subsequent missing-fault-coverage finding
are retained. The observer now opens a separate 4,000-byte read connection
(mailbox framing stays 500) and captures the Unit's adopted fault before the
existing stimulus clear. Do not weaken proof or move fault ownership back to
a child already cleared by Execute-drop. Accepted pairs need one or two tries.
Final 2,011 AB tests and 74 root tests pass. Native scan median/max observations
are 123/1,190 us with zero overlaps. Genealogy is restored, MANUAL/idle, logged
out, not restoring and five saved documents equal live. **S3c is next.**

S3b work folder:
`C:/work/fraktal-ab-s3b-20261021/prepare_17bd9babe817422b977d82139bae95cb/`.
The prepared `s3b_canonical.ACD` pin is
`634A3A86B88E666CFFCA9F530AC1D279709078BCF3E2C7EC2727B4B134394EEF`.
It has 304 explicit paths; both v38 native builds/read-backs pass. Exact
automatic Studio Capacity is 991,612 used / 2,154,116 available / 3,145,728
total blocks (31%). Do not request another screenshot on this qualified setup.
The completed session's authorization is historical. **Do not rerun S3b** or
repin its SDK-saved ACD (now `B308A9E4...2079835`). Runtime outputs:
`C:/work/fraktal-ab-s3b-20261021/runtime_117b9f6518b446aaab28d7845da5a488/`.
Future images need separate offline gates and current controller authorization.
Never overwrite preflight/evidence or open the immutable genealogy original.

**S3a runtime exit passes for its 94-path subset.** See
[runtime evidence](Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21.md).
The owner approved the exact F1D24CA8...A7EE79F session and supplied Capacity:
817,476 used / 2,328,252 available / 3,145,728 total blocks (25% displayed).
Candidate and restored-baseline regressions pass 31/31 each; all four active
decision pairs and idle equivalence pass with the unchanged same-scan proof.
The first candidate fixture's failed capture/18 completed rows are retained.
The read harness now copies metadata and decodes only after closing the scan
window. Native candidate median/max scan observations are 110/1,178 us,
zero overlaps; genealogy is restored, MANUAL/idle, logged out and five saved
documents equal live. **Do not rerun the completed S3a session.** Its SDK-saved
ACD has changed hash; retain the original pin. Current authorization is spent
on this completed session, not a future image.

The owner also requested an automatic Capacity algorithm. Run
[the calibrated forecast](AB_CAPACITY_FORECAST_METHOD_2026-10-21.md)
during future offline preparation. It predicted held-out S3a usage within
+1.0481%; forecasts remain advisory. The automatic Studio Capacity collector
now reproduces the owner's exact S3a values and supplies the measured S3b
gate from a source-hash-checked offline review copy. Its qualification is
limited to this L81E/v38 English setup. Native scan gates pass only at each
recorded stage's scope; each future stage measures again.
The pending S3a instructions below are historical and superseded by this
runtime record. No commit or push is authorized.

The first corrected S0 probe was downloaded and measured. Genealogy is restored
with 31/31 regressions and passing final checks: Run, not faulted, scanning,
MANUAL/idle, logged out, not restoring, saved documents equal live. See
[runtime evidence](Evidence/AB_S0_CANONICAL_TYPES_2026-10-20.md).

D6 selects DINT milliseconds; D7 selects native LDT nanoseconds. The
[V2 contract](AB_FROZEN_CONTRACTS_V2.json) and
[Part III amendment](AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md)
were approved as target drafts on 2026-10-20: “Approve drafts and proceed to
S1”. The S1 reference-oracle exit passes at its recorded scope. Shipping V1 remains active until implementation gates
pass. The supplementary S0 session completed on 2026-10-21 after current
owner authorization and exact-artifact Capacity fit. No commit or push was
requested.

**S1 implementation/evidence:** generic Python reader, equivalence tool and
isolated legacy replay are in `FraktalCore/PLC/Allen-Bradley/tools/`, with three
hash-bound compressed fixtures under `tools/fixtures/canonical/`. Final gates:
1,921 AB tests, 74 root tests, clean spec/contracts/strict consistency, both
unchanged S0 v38 offline build/read-backs. S0's 47 checks reproduce, including
the two original findings; genealogy replay is 50 reads / 4,437 values. See
[S1 evidence](Evidence/AB_S1_CANONICAL_READER_2026-10-20.md).

The reader uses a normalized PLC-manifest model; the physical V6 wire loader
and stable paired live acquisition remain S2 work with its first image. The
original legacy capture has no transport type metadata. No press projection
capture was found: record one on a gated image before full S3 acceptance;
do not relabel/synthesize recorded data or contact the retired L24ER.

**Next (updated 2026-10-21): S2.** Supplementary S0 passed; see
[runtime evidence](Evidence/AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md).
The 2 MiB UDT reads exactly at 500/4000-byte connection settings; the Press
root and precise LREAL initializer vectors pass. Owner Capacity: 69%,
2,189,916 / 3,145,728 blocks, 955,812 available. Native MaxScanTime: 10 us,
zero overlaps on the inert 10 ms probe. Genealogy and all five live documents
are restored, 31/31 regressions and final read-only checks pass. The immutable
genealogy ACD is unchanged.

Measured access rules: a Read Only parent blocks its writable child. Ancestors
of HmiRequest need Read/Write; other public branches are Read Only. None members
prevent whole-record reads, so private working storage stays outside canonical
whole-read records. Symbol attribute 10 reports top-level RO=2/RW=0 on this Echo;
the raw Template metadata does not distinguish member permissions. Publish
effective member access in V6 from the owning declaration; never guess it in
a client. The target drafts and plan have been corrected accordingly.

Session work folder:
`C:/work/fraktal-ab-s0-supplementary-20261020/prepare_da41a9b11aad4d10938044fdcdcb4005/`.
Runtime outputs:
`C:/work/fraktal-ab-s0-supplementary-20261021/runtime_44309c2828a4421d8d1320512f68f12a/`.
Do not rerun that completed session or repin its SDK-modified deployment ACD.
S2 needs a new prepared image/session and its own current download authorization.
A fault clear remains a separate question. Physical and security gates remain open.

**S2 runtime exit passed on 2026-10-21.** See
[runtime evidence](Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21.md),
[preparation evidence](Evidence/AB_S2_CANONICAL_PREPARATION_2026-10-21.md) and
[wire draft](AB_CANONICAL_PUBLICATION_S2_WIRE_DRAFT_2026-10-21.md).
Work folder:
`C:/work/fraktal-ab-s2-20261021/prepare_3701f795c13b4329891f4eca1346b3a5/`.
Prepared s2_canonical.ACD pin: 2B3F99D936FE742BAA32E888F7F6FF9244DF57B746FECA8B7C47148AAD200973.
The root exposes 46 S2 paths. Both v38 compiler/read-backs pass. Its separate
V6 loader discovers the header by shape/magic, and the fixture uses entire-scan
generation to prove paired state. All 46 paths and types match. Owner Capacity
and native scan deltas are recorded; candidate and restored-baseline
regressions pass 31/31 each. Genealogy is restored with passing final checks.
The interrupted backup and the empty-controller recovery are retained; no
cause for that earlier empty state was established. Runtime outputs:
`C:/work/fraktal-ab-s2-20261021/runtime_ff4a0406689d44478b85ee71f6f94799/`.
The SDK changed the opened candidate ACD after download; preserve its original
pin and do not redeploy or repin it. S3a offline preparation is next; a new
image/session needs its own gates and current authorization. Shipping V1 stays
active. No fault clear, commit or push is authorized.

**S3a is prepared offline.** The owner selected preservation of the oracle's
logical paths through PLC-published extents/live count references. See
[S3a preparation](Evidence/AB_S3A_CANONICAL_PREPARATION_2026-10-21.md) and
[V6.1 wire draft](AB_CANONICAL_PUBLICATION_S3A_WIRE_DRAFT_2026-10-21.md).
Work folder:
`C:/work/fraktal-ab-s3a-20261021/prepare_0d22cab49f6e4aeeb6fa005ef0f4f9be/`.
Prepared ACD pin: F1D24CA83A3A452E02402AD7604A373B592909A55AA4858F510111A54A7EE79F.
Source pin: 83443758841A5B5F8D334106079EB8B041F2FF3E3419DB99564108532E361095.
The 94-path candidate passes 1,960 AB tests, 74 root tests, both v38
compiler/read-backs and prepared/access gates. Current runtime approval and
the new capacity_review.ACD Studio counts are pending; the array-view answer
does not authorize controller changes. S2's sealed 745,244 used blocks are
the incremental baseline. RUNBOOK.md proposes 31 candidate rows with four
read-only active-decision pairs, idle equivalence/scan, then genealogy rollback
and 31 baseline rows. No new command/model-creation stimulus or fault clear.
No S3a download has run; the five live genealogy documents remain unchanged.

**The session commands below are historical. Do not rerun them:** their
preflight/backup/download outputs already exist, and the SDK saves changed
the opened probe ACD after deployment. Prepare a new, gated image/session for
any additional download; never replace the original pins or evidence files.

## Earlier preparation and original instructions (historical)

**2026-10-20 continuation:** the original prepared probe is superseded before
download: its LINT microsecond stimulus was assembled 2^32 too low. The
generator is corrected and a new probe/session is prepared; see
[the preparation evidence](Evidence/AB_S0_CANONICAL_PROBE_PREPARATION_2026-10-20.md)
for the artifact hashes, compiler/read-back results and retained failed checks.
The runtime type decisions D6/D7 remain pending. Use the run directory below;
do not deploy the earlier `C:/work/fraktal-ab-s0-20261019/s0_probe.ACD`.

- **Echo** (local FactoryTalk Logix Echo, 1756-L81E v38.011, serial
  `601FC87B`, `127.0.0.1` slot 0) last held the genealogy image (manifest
  `6DEC4C1DC2F7F78A`).
  - The host reboots and the **Echo service times out at boot**. Only an
    elevated Administrator can start it, so ask the owner to run
    `Start-Service "FactoryTalk Logix Echo Service"` elevated.
  - Before any guarded step, check the service, that the 44818 listener
    process is `EmulateControlLogix5580`, and the identity guard.
- **S0 is prepared but not downloaded.**
  - Tools (uncommitted): `FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s0_canonical_probe.py`,
    `fraktal_ab_s0_canonical_measure.py` and
    `test_fraktal_ab_s0_canonical_probe.py` (includes the timestamp-stimulus regression).
  - Work folder: the new `$S0_WORK` directory defined below. The combined probe is
    compiled for both v38 targets. The prepared ACD `s0_probe.ACD` has a hash
    in `probe.sha256` and an equivalent read-back.
- **The last download attempt stopped at the login guard.** An HMI session
  (`echo_admin`, level 4) was active, and the preflight refuses to download
  over an active session. Never weaken that guard; ask the owner to log out
  of the HMI.
- **Nothing from this line of work is committed.** Do not commit or push
  without the owner's instruction. Leave the owner's unrelated edits alone:
  `.gitignore`, `AGENTS.md`, and the Siemens archive `.dart_tool` files.

## Your first task: finish S0

Controller-changing operations need the owner's **current** authorization. A
download, mode change, tag write or fault clear authorized in an earlier
session is historical. Ask before step 3. If Echo comes up faulted, a fault
clear is a separate question.

Run these from the repository root. Every output must be a new file; never
overwrite earlier evidence.

```powershell
$S0_WORK = 'C:/work/fraktal-ab-s0-20261020/readiness_20edac489b6c46e2b6229c76d400e9e7'
```

1. **Read-only checks:**
   - service status;
   - the 44818 listener process;
   - `python "$S0_WORK/scripts/guard_echo.py"`;
   - `C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe inspect`
     (mode, `IsFaulted`, keyswitch);
   - the Unit is MANUAL and idle with `CurrentLevel` 0.
2. **Record the preflight once:**
   `python "$S0_WORK/scripts/preflight.py"`, which writes
   `preflight.json`. The session's later `--verify-only` calls compare
   against it.
3. **Back up and download the probe:**
   `& "$S0_WORK/session/bin/Debug/net8.0/win-x86/S0Session.exe" backup`,
   then the same with `deploy-probe`. Log each run to a new file and audit it
   with `fraktal_ab_sdk_log_gate.audit_log`. The SDK names the upload "Open
   Project From Controller", so audit `Save As` for the backup.
4. **Measure, read-only:**
   `python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s0_canonical_measure.py --expect-serial 601FC87B --generation "$S0_WORK/corrected_combined/combined.json" --output "$S0_WORK/measurement_01.json"`.
   - A mismatch on the `DT`/`LDT`/`TIME` members is a **finding**, not a tool
     failure. Rockwell documents `TIME32` and `TIME` in µs and `LTIME` in ns,
     and LINT is treated as `LDT` (ns) in conversion. Report what the bytes
     show.
   - Extend the probe for the S0 step-4 questions (structure-size limits and
     fragmented reads, a root tag named as the browse name, access bits in the
     Symbol and Template objects) if the owner agrees to a second probe
     download.
5. **Restore and verify:**
   - `S0Session.exe restore-genealogy`. It downloads a hash-checked *copy* of
     `C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD`. The original is
     bound by hash in the 10-19 evidence and must not be opened.
   - With `FRAKTAL_AB_DECLARATION=fraktal_ab_genealogy_demo`, run
     `fraktal_ab_genealogy_execute.py --execute-fixture --expect-serial 601FC87B --credential-file C:/work/fraktal_echo38_access_fixture.json --output <new>.json`.
     It restores the five live documents and runs 31 regressions. Ask the
     owner for that harness's tag writes.
   - Finish with the read-only final checks used on 10-19: Run, not faulted,
     scanning, MANUAL/idle, logged out, not restoring, saved documents equal
     to live.
6. **Record and decide:**
   - Write `Specification/AllenBradley/Evidence/AB_S0_CANONICAL_TYPES_<date>.md`
     plus a payload folder with hashes. Never archive credentials.
   - Settle D6 and D7 in the design note from the measurements.
   - Draft `AB_FROZEN_CONTRACTS_V2.json` and the Part III amendment (type map
     V2, §3.10 exposure, §11.1 desktop direct per D9, L24ER retirement) for
     the owner's approval.

Then continue with S1 onwards as the plan describes, one stage at a time,
each behind its gates.

## Rules that bite here

- **Generated L5X only.** Never hand-write L5X. Never name a member after a
  data type (`Time`, `DT`, `LDT` …). Use normalised time literals (`T#1s500ms`,
  not `T#1500ms`). ST has no `MOV`. Structured members read back with
  `Radix="NullType"`.
- **No station knowledge in a client.** If a client needs a fact, the PLC
  publishes it, in its templates or its manifest. That is the whole point of
  this work.
- **Value equivalence is the acceptance test.** Each stage's generic read must
  equal the Python projection, path by path and type by type. The only allowed
  differences are the five D2 array bounds, listed explicitly.
- **Gates for every change:**
  - the AB suite, by discovery from `FraktalCore/PLC/Allen-Bradley/tools`
    (1,890 tests passed on 2026-10-19);
  - `python tools/check_ab_spec.py`, `python tools/check_ab_contracts.py` and
    `python tools/check_consistency.py --strict` with its tests;
  - v38 build and read-back on both targets;
  - for HMI changes: Flutter `--enforce-lockfile`, analyze and the full suite.
    The `flutter` command may not be on PATH, and the pinned SDK path in
    AGENTS.md may not exist on this host. Record which SDK you used.
- **Memory and scan time are measured per stage** (owner Capacity Estimate).
  Never cut features or weaken validation to fit.
- **Report** what passed, failed and was skipped, with exact outputs. Evidence
  is append-only and keeps failed runs.
