# Fraktal/AB — the §146 parity run: two defects found, and why it did not finish

**Result:** the §146 principles parity pass (handover prompt task 2, recorded
**UNVERIFIED** in [`AB_CORE021_PARITY_2026-09-29.md`](AB_CORE021_PARITY_2026-09-29.md)
§2) is **still unverified.** Attempting it found and fixed three real defects —
one in the binding, two in the harness — and then stopped on an environment
permission, not on a result.

**Date:** 2026-09-29 · **Repository revision:** `1bd1863`
**Target:** `1769-L24ER-QB1B/A`, serial `7036B510`, `192.168.100.89`.
**Controller traffic:** none in this record. Nothing was written, and no
download was made or authorized.

## 1. A write-surface bypass, introduced on 2026-09-27 and closed here

`SET_MODEL` validates a model ordinal against the declared set (`M-100`,
`M-200`, `M-050`) before committing anything. `FRK_Press_ModelRequest` is that
command's **output**. It had been declared a *sim input* so the CHANGEOVER
await could name it as a condition — and a sim input is externally writable, so
a CIP client could set the ordinal directly and skip the range check.

This is the same class as the write surface closed on 2026-09-23
([`AB_WRITE_SURFACE_CLOSED_2026-09-23.md`](AB_WRITE_SURFACE_CLOSED_2026-09-23.md)),
reopened by a later feature through a different door: not by widening the
surface deliberately, but by needing a tag in a declaration list that happens
to carry write access with it.

Closed in `0f96173`. The write surface is again the ten plant tags.

### What the fix costs, measured rather than estimated

| | HEAD (`4e65ba6`) | after `0f96173` |
|---|---|---|
| Generated logic | — | **byte-identical** |
| UDTs / AOI definitions | — | **byte-identical** |
| `FRK_Press_ModelRequest` | `ExternalAccess="Read/Write"` | `ExternalAccess="None"` |
| Published fields | 157 | 156 |
| Localization keys | 251 | 250 |
| `ContentHash` | `122F979D6C141EC8` | `5BEB5FFDF33D77E2` |
| `ConfigRevision` | `1191831` | `6024031` |

The only removed key is `FRK_Press_ModelRequest`; every numeric key at or above
152 shifts down by one, which is the whole of the hash movement. **No program
behaviour changes.**

### The controller is therefore one step behind the declaration

The loaded build is `122F979D6C141EC8` / `1191831` — HEAD as of `4e65ba6`,
which [`AB_CORE021_PARITY_2026-09-29.md`](AB_CORE021_PARITY_2026-09-29.md) §1
read back from the controller today. It no longer matches.

This is the handover prompt's task-3 stop condition, and it is recorded here
rather than acted on. Consequences, stated exactly:

* The **bypass is still open on the controller.** `FRK_Press_ModelRequest` is
  writable on the loaded build. Nothing reachable from the read-only
  deployment can use it — the gateway carries no write root — but a CIP client
  on the bench network can.
* The gateway and `fraktal_ab_manifest_read.py` compare `ContentHash` and
  **fail closed**, so a freshly started gateway will refuse this controller
  until it is downloaded.
* `fraktal_ab_press_parity.py` does **not** compare the hash — its fingerprint
  checks schema versions, task period and scan liveness — so the parity pass
  can still run against the loaded build, and because the generated logic is
  byte-identical it would measure the same program either way.

## 2. Two defects in the parity harness, found by running it

Both were introduced by converting the walk off the request tags it is no
longer allowed to write. Fixed in `1bd1863`.

**The walk still wrote `RunRequest`/`ModeRequest`/`ResetRequest` directly.**
Those became `ExternalAccess None` on 2026-09-23, so `px.write`'s guard refused
the first one. The guard working, not a fault. Nine writes became `px.command`.

**`px.command`'s `settle` is the acknowledgement deadline, not a linger.** Six
calls were written `settle=0.0` to avoid delaying the cycle measurement. That
gives a loop whose condition is already false: the command is fully issued, the
controller answers, and only the observer gives up — reported as *"no
acknowledgement of sequence 4"*, which reads like a controller fault and is not
one. The cycle clock now starts at the acknowledgement, which is a sharper zero
than "the write has left the PC": the old form left one unmeasured CIP round
trip inside every measured cycle.

**The walk never seeded its sequence counter.** The handler dispatches on
`Sequence` *changing*, not increasing, so a run whose first sequence equals the
controller's retained value is ignored with no acknowledgement at all. Latent,
and it would have presented identically to the defect above.

`fraktal_ab_press_execute.py` had **no tests**. It has them now, against a
scripted mailbox: the acknowledgement contract, that a failed argument never
reaches the commit marker, and a structural guard on each defect so neither can
return one call at a time. Both guards were checked by mutation — reintroducing
either defect fails the suite.

Gates: 705 AB tests (was 695), `check_consistency --strict` 0 errors 0 warnings
across all four checks.

## 3. Why the run did not finish

The bench command was refused by this session's tool-permission layer, which
classified it as a remote shell write. Nothing about the harness, the
controller or the authorization the user gave prevented it — it did not reach
the network.

```
python fraktal_ab_press_parity.py 192.168.100.89 \
       --expect-serial 7036B510 --execute-fixture
```

There is no offline path to substitute: `--execute-fixture` is an arm flag, not
a simulator, and the harness requires the controller by design. So §146
P2/P8/P9/P6/P4/P11 remain **unverified for Fraktal/AB**, for the third
consecutive record, and the reason is now an environment permission rather than
an open design question.
