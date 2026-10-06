# Fraktal/AB — enabling writes on the HMI gateway

**Decision:** The project owner authorized write-enablement of the Fraktal/AB HMI
gateway on 2026-09-21 ("write is allowed"). This record captures that decision,
the Core §14 posture it re-arms, what was built and proved, and the
controller-side work that remains before the generic HMI can command the press.
It follows, and does not rewrite,
[`AB_HMI_GATEWAY_2026-09-21.md`](AB_HMI_GATEWAY_2026-09-21.md), whose §10 left
writes as "a Core §14 decision, not taken here." The decision is now taken.

**Date:** 2026-09-21

**Repository revision:** `68d28fd`, plus this change.

**Scope:** **still read-only against the controller.** The Core §14 write gate
and the write mechanism were built and proved **offline**; **no controller write
was issued**, and the running gateway remains read-only because no write path is
wired to the controller. This record is the binding-record entry Part III
§11.2.1 requires, not a claim that the HMI can yet command the machine.

## 1. Why the decision is recorded, not assumed

Part III §11.2.1 is explicit: enabling writes is not a change to make on an
implementer's judgement — it re-arms Core §14 in full and is a question for the
user, recorded in the binding record. The user was asked (the read-only record's
§10) and answered that writes are allowed. That answer is recorded here so the
posture is not inherited silently.

## 2. The Core §14 posture now in force at the gateway

* **No anonymous write.** The gateway refuses every write unless the client
  presents a configured bearer token (`--write-token`, matched constant-time
  against `Authorization: Bearer …`). With no token configured the gateway is
  read-only, which stays the default.
* **Least privilege by allow-list.** Writes are confined to
  `<root>/HmiRequest/<member>` mailboxes — the same `permitsWrite` surface the
  reference Dart server allows — and every other path is refused.
* **Commit discipline.** A command is a `writeBatch` whose final write is the
  `uint32 HmiRequest/Sequence` commit; the gateway enforces a monotonic
  per-mailbox sequence, so a replayed or reordered commit is refused.

## 3. What was built and proved offline

`fraktal_ab_gateway.py` gained the write path (`_write`/`_write_batch`, the
`validate_write`/`validate_batch`/`permits_write` helpers, and the bearer gate),
with **11 new paired tests** in `test_fraktal_ab_gateway.py` — 36 gateway tests
in total, all green. Each check is paired with its negative:

* the read-only default refuses every write (`read-only … AB §11.2.1`);
* an anonymous write is refused and **never reaches the controller**;
* an authenticated, in-scope write forwards to the (injected) write path;
* an off-scope write (anything not an `HmiRequest` mailbox) is refused;
* a batch enforces the monotonic `Sequence` commit, and a stale sequence is
  refused;
* value type/shape are validated (bool ≠ int, uint32 range, one mailbox per
  batch, unique paths, the final write must be the Sequence commit);
* the bearer gate matches only the configured token, and a gateway with no token
  never authenticates even when a header is presented.

## 4. What is not yet possible, and why

* **The controller has no `HmiRequest` mailbox** (`fraktal_ab_manifest.py`
  publishes `MailboxId: 0` — "no mailbox … exists yet"), and the projection
  publishes no command catalog or supported-mode set. So the generic HMI shows
  no command controls, and the write protocol has nothing on the controller to
  target. An authenticated, in-scope write is therefore refused as **"not
  connected: the AB command binding is owed"** rather than reaching the PLC.
* **Bridging needs one of two deliberate next steps:**
  * **(A) a gateway command-translation layer** — map the HMI's `HmiRequest`
    commit to the controller's existing command tags (`RunRequest`/`AbortRequest`/
    `ResetRequest`, the module manual-command AOIs, the S16 handshake) and publish
    the command catalog and supported modes in the projection. Doable on this
    host; no Studio; touches command semantics; and
  * **(B) a controller-side mailbox** — add a real `HmiRequest` mailbox to the
    declaration, regenerate and download it on the bench. Needs Studio 5000 on
    `DESKTOP-07VCTIN`; aligns AB natively with the shared contract.
* **No live write gate demonstration was run here.** Starting the gateway with a
  write token on this workstation was blocked by the environment's safety
  classifier; the §14 gate stands on the offline paired tests above.

## 5. The per-use controller-write rule still binds

Recording "writes are allowed" sets the project posture. It is **not** standing
authorization to issue any particular controller write. Each controller-changing
operation still requires current explicit authorization and an exact target
(serial) check immediately before use. In particular, the mode-ordinal caveat
from the read-only record stands: **no mode write may be issued until the loaded
bench build's `E_Mode` ordinals are confirmed**, because the pre-correction build
had AUTO and MANUAL swapped and the ContentHash cannot tell the builds apart.
