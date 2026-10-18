# Phase 6 — proposed press68 configuration/set retention check

Prepared 2026-10-04 (America/Bogota). **Awaiting current owner authorization;
no controller change or power cycle has been performed.** This is a bench test
plan, not a normative contract or a claim of full Core §3.8b conformance.

Target: 192.168.100.89, slot 0, exact serial 7036B510, loaded press68. The existing
read-only preflight verified its identity/fingerprint at
2026-10-04T15:46:08.351862+00:00. AUTO/CONTINUOUS is 0/0; the press is stopped and
Error is false. ConfigPersist Pending, Failed and RestoreLost are all zero.

The proposed sole value change is **station.number: 1 → 2**, within its declared
1–99 range. Current registered station values to preserve and restore are:

| Write key | Current value |
|---|---|
| station.number | 1 |
| station.ramExtendLimitMs | 2000 |
| station.airPressureMinKpa | 451 |
| airPressure.conflictTime | 500 |
| press.requireTwoHandStart | 1 |

The source of these values is the exact-serial native readback, not L5X defaults.
No model-data value, credential, access policy, timeout, hardware input, force,
fixture tag or motion command is part of this test. The configuration/set
requests use the existing PLC-validated root mailbox and running gateway.

1. Recheck target identity and loaded contract, capture all station values,
   schemas, mode/run style and persistence state, and require the press stopped
   with no command in flight. If this baseline changed, stop and review the new
   scope before changing anything. Require a current permitted PLC session; the
   owner performs any needed login in the HMI.
2. Select MANUAL while stopped, then save the original Station configuration as
   `phase6-retention-20261004`. Refuse if that name already exists or the four-set
   store is full. Do not overwrite or delete an existing set. Read/export the
   resulting complete document and retain its digest plus original value table.
3. Write only station.number = 2 through WRITE_CONFIG with the live revision.
   Require an accepted acknowledgement and exact readback; compare every other
   station value with the baseline. Observe ConfigPersist through its 5-second
   window; Pending false is a preparation check, not proof of physical retention.
4. Leave the press stopped. Only after those checks pass, ask the owner to power
   the PLC off and back on. The owner performs the physical cycle. A gateway
   restart, if required, remains the owner's. No download, fault clear, clock
   write, firmware or network change is included.
5. Read identity/contract again; compare all station values, schemas and restore
   diagnostics before any corrective write. station.number must still be 2 and
   every other station value must match. List/export the saved set through the
   gateway and compare its full content/digest with the pre-cycle copy. This
   proves tag retention across this PLC power cycle and host-document survival
   while the host remains powered; it does not test host power loss.
6. With the owner logged in if required, select MANUAL while stopped and load the
   temporary original Station set. Verify every restored value, then delete only
   the test set after checking its identity/digest. Restore the original
   AUTO/CONTINUOUS and confirm the press remains stopped, with no pending request
   or persistence failure. No START, HOME, jog or fixture arming is issued.
7. Preserve failures and the first post-cycle observation before restoring. If a
   request outcome is unknown, read its acknowledgement and current values; do
   not replay it automatically. If preparation fails, restore any changed value
   and mode and clean up only the verified test set. Existing native write guards
   check exact serial immediately before every controller write.

The authorization requested covers steps 2–3 and the restoration/cleanup in step
6 on this exact target, plus the owner-performed cycle in step 4 after preparation
passes. It does not authorize other controller operations. The repository's
[AGENTS.md §3a](../../AGENTS.md) requires current explicit authorization before
controller-changing operations; the previous gateway restart and dialog
confirmation authorize read-only verification only.

Record pre-cycle, first post-cycle and final-restoration observations as new dated
evidence. A successful result closes only the tested station-configuration and
host-set power-cycle observations on this v33 bench. Download/upgrade retention,
the physical nonvolatile medium/durability window, other accounts, S1 clock and
TC3 segmented transport remain separate claims. No PLC source, generated image,
table capacity or user count changes are needed; PLC memory growth is zero.
