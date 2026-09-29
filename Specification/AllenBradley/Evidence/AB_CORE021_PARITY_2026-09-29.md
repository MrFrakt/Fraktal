# Fraktal/AB — Core 0.21 parity audit

**Result:** the offline audit is complete and **three items conflict with the
read-only claim recorded on 2026-09-28**. They are not gaps to close; they are
capabilities already built, downloaded and exercised on the bench on 2026-09-27,
the day before the claim was recorded. Closing them means removing working
features, so this record stops at the classification and asks.

**Date:** 2026-09-29

**Repository revision:** `bed1ed7`. AB tool suite 695 tests, `check_consistency
--strict` 0 errors 0 warnings across all four checks.

**Target:** `1769-L24ER-QB1B/A LOGIX5324ER`, serial `7036B510`,
`192.168.100.89`. Controller traffic in this audit was **reads only** — the
manifest read, with the serial checked immediately before.

## 1. Two premises in the handover prompt are stale

The prompt states *"Fraktal/AB was not touched"* between 2026-09-24 and
2026-09-28. It was, substantially, on 2026-09-26 and 2026-09-27: the fieldbus
topology, §10.5.1 output forcing, §3.8 changeover with three models, published
step names, an access policy, operator decisions, and a stable path set. Those
commits are `b17610a` through `df324db` on `main`.

The prompt's **State at handover** also names the loaded build as `ContentHash
71448732E842290F` / `ConfigRevision 7423111`. The controller carries
`122F979D6C141EC8` / `1191831`, read back today. That is not drift: it is the
build downloaded on 2026-09-27 for the changeover work, and it **matches the
current declaration exactly**, so no regeneration or download is needed for
anything in this audit.

Neither correction changes what the prompt asks for. Both change what the
answers are, so they are recorded before the table rather than inside it.

## 2. Classification

| Item | Class | Proof |
|---|---|---|
| §145 Line profile (§3.8e, §8.5.2) | **NOT CLAIMED**, recorded | Projection publishes no line or shift leaf (383 keys, none matching line/shift). `tools/check_consistency.py` `AB_ABSENT` carries `ShiftStartedAt`, `ShiftHistory`, `ShiftHistoryCount` under a `_LINE_DATA` reason |
| §148 one published diagnostic | **BOUND** | Each module publishes `Status/Diagnostic/ReasonCode` and nothing else; no `OutImm` diagnostic exists in any generated UDT. The other `Diagnostic` keys are the fieldbus channel records and the mailbox answer, neither of which is a module `OutImm` |
| §3.8b set delete / §3.8d data classes | **NOT CLAIMED**, refused by name | `WRITE_CONFIG`, `QUERY_CONFIG`, `CAPTURE_CONFIG` → `no_config_manifest`; `SAVE_CONFIG_SET` → `no_config_sets` |
| §150 local PINs as salted hashes | **NOT CLAIMED**, nothing to store | `LOGIN` and `SET_ACCESS_LEVEL` refused → `access_not_enforced`. No user table exists on the controller, so there is no readable secret to hide. The §14 surface is the gateway bearer and the proxy credential, held outside the repository |
| §146 principles P2/P8/P9/P6/P4/P11 | **UNVERIFIED** | `fraktal_ab_press_parity.py` is a bench tool requiring the controller. Not run: it drives the press, and whether the declaration should change at all depends on §3 below |
| §149/§151 model data | **CONFLICT** | AB has changeover and three models (`M-100`, `M-200`, `M-050`) since `f602a29` |
| Access enforcement | **CONFLICT** | AB publishes `Access/CurrentLevel` = operator and a twelve-entry `Access/Policy/Required` since `966a165` |
| Writable mailbox kinds | **CONFLICT** | `SET_MODEL` and `FORCE_CHANNEL` are routed, not refused, since `f602a29` and `e29f09e` |

## 3. The conflict, stated exactly

The prompt's standing rules say: *"Do not add a write root, a writable mailbox
kind, or an access-policy path. If a task seems to need one, stop and ask."*
The audit's §9 records: *"AB stays **read-only** … they are not claimed and the
mailbox refuses both."*

Three of those already exist, and each was asked for explicitly:

* **`SET_MODEL`** routes §3.8 changeover. The press validates a model, drives
  the load-safe position, asks the operator to confirm, and commits declared
  values into `ParCfg`. It was exercised on the bench on 2026-09-27: `M-200`
  committed, `PressDwellMs` 300 → 600.
* **`FORCE_CHANNEL`** routes §10.5.1 output forcing, permitted only in idle
  MANUAL, withdrawn before it is applied so a force cannot outlive its
  permission.
* **`Access/*`** publishes that this station enforces **no** per-user levels —
  `none` for all twelve gated actions. It is a statement of fact, not a
  permission granted, and it exists because the HMI fails closed on a missing
  policy: with nothing published, every operational section stayed hidden and a
  changeover waiting for a model could not display the prompt saying so.

So the question is not whether to close a gap. It is which of two owner
decisions, made a day apart, governs:

| Reading | Consequence |
|---|---|
| The 09-28 read-only claim governs | Remove the two routed kinds and the access policy. Changeover and forcing stop working; the operational sections go dark again; the 09-27 evidence records describe capabilities the binding no longer has |
| The 09-27 capabilities govern | The claim is not read-only. Part III records a write-enabled binding, and Core §14 arms in full: authenticated principals, least-privilege roles, no anonymous write |

A third reading exists and may be what was meant: **read-only is a property of
the deployed gateway**, which is configured with no write root and refuses every
operator command before the controller sees it, while the controller-side
mailbox keeps routes that only a write-enabled deployment can reach. That is
defensible and it is how the binding behaves today — but it is not what
"the mailbox refuses both" says, and the difference decides whether the access
policy stays.

**Nothing has been changed pending the answer.** No declaration edit, no
regeneration, no download, no gateway reconfiguration.

## 4. What was not attempted, and why

* **The bench parity pass (§146).** `fraktal_ab_press_parity.py` drives the
  press through its modes. Running it before §3 is answered risks proving parity
  for a declaration that is about to lose two of its commands.
* **Tasks 2, 4, 5 of the prompt.** Closing gaps, the bench HMI pass and the
  Part III claim-table update all depend on which claim is being recorded.
* **No download was needed or requested.** The regenerated build would be
  byte-identical to the loaded one: the declaration hash and the controller's
  `ContentHash` are both `122F979D6C141EC8`.
