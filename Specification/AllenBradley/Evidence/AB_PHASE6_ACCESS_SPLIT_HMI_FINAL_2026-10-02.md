# Fraktal/AB Phase 6 — final HMI result handling

**Date:** 2026-10-02, America/Bogota. Refines the prepared
[split-login correction](AB_PHASE6_ACCESS_SPLIT_FIX_2026-10-02.md).
No controller writes, download, gateway startup or running-client deployment
were performed. Studio Verify/download and runtime timing remain pending.

The repository now returns credential rejection only for explicit LoginFailed.
A completed result whose session is already gone waits for a usable result
and otherwise reports unavailable. This preserves the same rule with or
without optional result-sequence correlation. A new test covers the expired
session, alongside stale failure and delayed success. The pending dialog
remains clear of failure feedback and closes after success.

Final validation: **439 HMI tests passed, 6 skipped**, analysis clean, release
Web build exit 0, **9/9 HMI mutations killed** after a passing baseline. The
PLC's **1,417 tests**, **33 consistency tests**, clean consistency result and
**13/13 PLC mutations** are recorded by the preceding evidence. Final PLC
source regenerates press62 byte-identically; no new PLC artifact is required.
The SDK attempt remains blocked by **No valid license**.

Use **C:\work\press62_hmi_web_final** for the release client. This supersedes
the earlier prepared release folder in the preceding evidence. For the running
development HMI on port 5555, hot-restart/relaunch Flutter, then refresh Chrome.
Import/Verify/download **C:\work\press62.L5X** and restart the gateway first.
The owner's exact Chrome URL/version is still unconfirmed.
The [companion JSON](AB_PHASE6_ACCESS_SPLIT_HMI_FINAL_2026-10-02.json) records
the final client hashes and checks. Earlier evidence is unchanged.
