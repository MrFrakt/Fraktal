# Fraktal/AB — downloading the mode-ordinal correction to the bench

**Result:** **The mode-ordinal correction is on the bench controller.** The
press demo built after `E_Mode` was put back on the Core contract was downloaded
on 2026-09-21, and the controller reads healthy afterwards: the manifest comes
off whole and coherent, and the unit is idle with no fault.

**Date:** 2026-09-21

**Repository revision:** the build is `beda2ab` ("Put the AB mode ordinals back
on the Core contract"); this record is written at `52979af`.

**Scope:** one authorized manual download, and read-only verification. **No tag
write, mode change, fault clear, clock set, firmware, controller-network, safety
or SD-card operation was performed.**

**Why this record exists at all.** Two handover prompts on `main`
([`AB_HMI_GATEWAY_HANDOVER_PROMPT.md`](../AB_HMI_GATEWAY_HANDOVER_PROMPT.md),
[`AB_COMMAND_MAILBOX_HANDOVER_PROMPT.md`](../AB_COMMAND_MAILBOX_HANDOVER_PROMPT.md))
tell the next agent that the loaded build pre-dates the mode-ordinal correction,
and to look in this directory for a record of the download before trusting a
`Mode` value or issuing `SET_MODE`. This is that record. It is the file those
prompts point at.

## 1. What was wrong, and why it had to reach hardware

Core `E_Mode` is `AUTO := 0, MANUAL := 1, HOME := 2`, and the HMI's `UnitMode`
enum matches it. The AB press demo declared `MANUAL = 0, AUTO = 1`. Every `Mode`
and `ModeRequest` value the binding published was one place out from the
contract a client resolves against.

That stopped being theoretical on 2026-09-21, when the generic HMI began
rendering this controller through the gateway
([`AB_HMI_GATEWAY_2026-09-21.md`](AB_HMI_GATEWAY_2026-09-21.md)): an operator
screen was reading a live `Mode` and would have shown **MANUAL as AUTO**. The
correction was already committed and verified offline; it was the controller
that still held the old ordinals.

## 2. The target, checked immediately before the download

```
product   1769-L24ER-QB1B/A LOGIX5324ER
revision  33.014
serial    7036B510            serial_matches: true
state     3 (Run)             192.168.100.89:44818, median 16.7 ms
USB       Rockwell Automation USB CIP Device — OK
```

## 3. The artifact

```
source L5X   press14.L5X          510,630 bytes
             D3EB9E91FD6515608D944CDA163A9D0283737DD440E7D71629982B04D27741FB
ACD          press_modes.ACD    2,417,928 bytes  (as built and verified)
             E8FC0B77D1F390F56CD634ACFFAE2CF79558976FB8BA3DF32328BBF23943589C
SDK import   Warnings 0, Errors 0
Studio v33   0 errors, 0 warnings, "0 of 12 Messages"
```

The emitted project differs from its predecessor in **exactly ten lines**, all
of them mode dispatch: the MANUAL guard, the AUTO guard, and `ActiveChain` in
each of the three renditions. The manifest is byte-identical — it publishes
field paths and operation ranges, not mode values — which is why `ContentHash`
below is unchanged and why the manifest cannot be used to tell the builds apart.

**The ACD on disk no longer hashes to the value above.** After the download it
is 2,473,105 bytes, `F5E950EC04CF1137DDB899529F45F5A8D4C729DC10A2C437591AD8BE4B87FEC7`,
modified 16:30:36. Studio rewrites a project file when it opens or downloads it;
`press_manifest.ACD` changed the same way around its 2026-09-08 download. The
hash above is the one that was imported and verified, not the one on disk now.

## 4. How the download is recorded, and what is **not** claimed

The download was **performed manually by the authorized operator** and confirmed
in session ("it is downloaded"). Automated download is recorded unavailable on
this bench — 3/3 failures across two mechanisms — so the manual step is the
documented path and the S5 CI-path narrowing.

**This record does not claim the loaded build was machine-verified.** It could
not be, and the reason is worth keeping:

* The manifest is identical across both builds, so `ContentHash` cannot separate
  them.
* `Chart.ActiveChain` is assigned the *mode ordinal* of whichever chain is
  dispatched, so it equals `Mode` in both builds.
* A promising discriminator was checked and **rejected**: MANUAL step 0 is an
  `AWAIT` that holds with reason `6111`, while AUTO step 0 is a `MARK` that holds
  for nothing, so at `Mode = 0` the two builds should differ in `Held`. They do
  not, because the chain body is gated by `IF Ctx.Running <> 0 THEN` and the unit
  is idle. With `Running = 0` neither chain executes and `Held` is 0 either way.

Separating the builds by reading therefore requires `Running = 1`, which needs a
tag write. Writes are the project posture since 2026-09-21, but posture is not
per-use consent, and no per-use authorization was given for one here. So the
loaded build rests on the operator's confirmation, corroborated by the file
having been rewritten by Studio at 16:30 on the day of the download.

## 5. Read-only verification after the download

The manifest still comes off the controller whole, and agrees with the
declaration:

```
passed true   coherent true   10 requests   22,112 bytes   83.0 ms
ContentHash    42334AD69FD1A3AB      ConfigRevision 4338506
Valid 1        Truncated 0           findings: none
```

The unit is idle and unfaulted:

```
Mode 0   Step 0   PrevStep 0   Running 0   Held 0   HeldReason 0
Complete 0   Error 0   ErrorID 0   ActiveChain 0   StallReason 0
```

`Mode 0` now means **AUTO**, per Core `E_Mode`.

## 6. What this unblocks

Handover step 8 of
[`AB_COMMAND_MAILBOX_HANDOVER_PROMPT.md`](../AB_COMMAND_MAILBOX_HANDOVER_PROMPT.md)
required the loaded build to be confirmed before any `SET_MODE`. It is
confirmed, with the limitation in §4 stated rather than hidden. The mailbox work
may proceed, and the first live `SET_MODE` through it will be the first
*machine* evidence of the ordinal correction — because it will select the chain
the operator asked for, which the old build could not do.
