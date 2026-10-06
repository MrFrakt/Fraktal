# Fraktal/AB — the command mailbox on the bench

**Result:** **The press demo carrying a Core §3.10/§14 command mailbox is on the
bench controller, and the mailbox reads back idle and uncommanded.** This
download is machine-verifiable, which the previous one was not: the manifest
content changed with the build, so reading `ContentHash` off the controller
proves which build is loaded rather than resting on the operator's word.

**Date:** 2026-09-22

**Repository revision:** `4191305`

**Scope:** one authorized manual download, and read-only verification. **No
write of any kind was issued** — no tag write, mode change, fault clear, clock
set, firmware, controller-network, safety or SD-card operation. The gateway was
not started with `--write-token`, so no write path existed while this was done.

## 1. The target, checked immediately before the download

```
product   1769-L24ER-QB1B/A LOGIX5324ER
revision  33.014
serial    7036B510            serial_matches: true
state     3 (Run)             192.168.100.89:44818, median 16.4 ms
USB       Rockwell Automation USB CIP Device — OK
```

## 2. The artifact

```
source L5X   press17.L5X        539,218 bytes
             D2411F080718D4691B462706A1B46229B79E67CCE03975A33CA65327B85F384D
ACD          press_cmd.ACD    2,425,122 bytes
             9F905C08DF0F692A8386AA491317F809E58E10243D87B67CC6F39DBFCE7225CA
SDK import   Warnings 0, Errors 0
Studio v33   0 errors, 0 warnings, "0 of 13 Messages"
```

Downloaded manually by the authorized operator over USB. Automated download is
recorded unavailable on this bench (3/3 failures across two mechanisms), so the
manual step is the documented path and the S5 CI-path narrowing. Studio rewrites
a project file when it opens or downloads it, so the ACD on disk will no longer
hash to the value above; that hash is the one imported and verified.

## 3. Which build is loaded — proved, not asserted

[`AB_MODE_ORDINAL_DOWNLOAD_2026-09-21.md`](AB_MODE_ORDINAL_DOWNLOAD_2026-09-21.md)
§4 had to record that its download could not be machine-verified: the manifest
was byte-identical across both builds, so nothing readable separated them.

That is not true here. The mailbox changed the manifest, and the controller
returns the new content:

| | generated | read off the controller |
|---|---|---|
| `ContentHash` | `86F37D3289C043E4` | `86F37D3289C043E4` |
| `ConfigRevision` | `8844157` | `8844157` |

The previous build published `42334AD69FD1A3AB` / `4338506`. So the loaded build
is this one, and because it was generated from the corrected declaration, this
also settles the mode-ordinal question the earlier record had to leave on the
operator's confirmation: **`Mode 0` is AUTO on the controller now, by
measurement.**

## 4. Read-side verification

```
manifest   passed, coherent, 10 requests, 23,904 bytes, 107.0 ms, no findings
           Valid 1, Truncated 0
projection 4 modules, 35 nodes, not truncated
```

The mailbox surfaces and is idle:

```
Press/HmiRequest/Sequence       0
Press/HmiResponse/AckSequence   0
Press/HmiResponse/Accepted      False
Press/HmiResponse/Diagnostic    ''
```

A freshly downloaded controller has not been commanded and does not look as
though it has: `Kind 0`, `Sequence 0`, and an empty diagnostic rather than a
stale one.

## 5. What is now reachable, and what that costs

This build gives the controller its **first writable surface**:
`FRK_Press_HmiRequest`, `Read/Write` over CIP. The gateway keeps it behind the
Core §14 bearer token and `permits_write`, and no writer exists at all without
`--write-token`.

But the deferred §11.2.1 gap is now live rather than theoretical. The contract
structures and the routed request tags are still externally `Read/Write`, so a
CIP client can write `FRK_Press_Unit` or `FRK_Press_RunRequest` directly and
never meet the bearer gate. The mailbox's arrival does not close that; it raises
the stakes, because there is now a gated path worth going around. The decision
and its blocker are recorded in
[`AB_COMMAND_MAILBOX_HANDOVER_PROMPT.md`](../AB_COMMAND_MAILBOX_HANDOVER_PROMPT.md).

## 6. Still owed

No command has been issued through the mailbox. The handshake, the refusals, the
ack ordering and the §14 negatives are all unproved on hardware, and so is
`pylogix` writing `LEN`/`DATA` to a `StringFamily` member — reasoned, not
measured, and the same class of assumption that string-literal assignment turned
out to violate. That is the next session's work.
