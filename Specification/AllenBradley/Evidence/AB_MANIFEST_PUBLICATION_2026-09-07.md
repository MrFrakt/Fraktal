# Fraktal/AB — publishing the manifest, and the two ways it lied first

**Spike:** S7 manifest — moving it from a measured shape to published content

**Result:** **The press demo project now carries a manifest emitted from the same
declaration as its AOIs, verified offline and proved to be stored rather than
merely accepted.** The first two builds published a manifest that was wrong in
two different ways, and neither way announced itself: one imported with warnings
and stored nothing at all, the other would have published two different paths
under one name. Both are fixed and both are pinned by tests.

**What is not claimed here.** The manifest has not been read from a running
controller. That needs a download, no download was authorized for this build,
and none was performed — so this record claims a correct manifest *in the
project*, and the discovery read stays owed.

**Date:** 2026-09-07

**Repository revision:** the series beginning `ce373c8`. The recorded gate run
is from a clean checkout at `bc95017`; every commit after it changes comments,
documentation or the size *estimate* only — the emitted L5X is byte-identical
(`F7A5D752…` from the standalone seed, before and after).

**Scope:** offline generation, SDK import, canonical round trip and Studio
Verify only. **No download was requested or performed for this build.** The
bench still holds the three-rendition press demo from the ladder-parity record.

## 1. Why this was the blocking item

Core §3.10 makes the manifest the runtime source of truth: a generated L5X on
disk is an engineering artifact, and a client that cannot read the manifest does
not proceed on assumption. Nothing published one, so the gateway had nothing to
discover — every earlier record described a manifest *shape* (S7 measured the
table capacities and the transport budget) and none contained manifest
*content*.

The manifest necessarily restates what the contract UDTs and AOIs already
encode. That is a bounded, deliberate exception to Core §1.1 O9, and it is
admissible only because one declaration produces all of them: the manifest is
emitted by `fraktal_ab_manifest.py` from the same `Application` the AOIs come
from, so a mismatch between them is a generator bug, not a maintenance task.

## 2. It describes the declared graph once, not the rendition that ran

The rendition selector is a harness input, not operator data. The published
contract describes the declared graph once and says nothing about which language
rendered it — the same way the TC3 HMI sees one chart whichever rendition ran.

This is enforced by construction rather than by discipline. `content()` derives
its field list from `fraktal_ab_generate.publishable_tags`, which subtracts
`harness_only_tags` — for the press demo:

```
FRK_Press_RenditionSelect   the selector itself
FRK_Press_LdAdvanced        exists only because ladder needs it
FRK_Press_LdScratch         exists only because ladder needs it
```

24 tags remain publishable and are the only ones the manifest may describe.

The test that matters is not the exclusion list but the equivalence:
declaring AUTO as `(ST,)` and as `(ST, SFC, LD)` produces **the identical
manifest, byte for byte, with the same ContentHash**. A manifest that changed
when a rendition was added would be describing an emission instead of a
declaration.

**What is published is the chart surface, not a step table.** The graph reaches
a client as the Core §3.13 marks — step cursor, active step, per-step visited
and duration, stall reason — which is how the TC3 HMI renders one chart whatever
rendition ran: from the marks, not from a static topology. The declared step and
transition lists are **not** a manifest table, because the frozen v1 schema has
eight tables and none of them is a graph. A client therefore reconstructs the
chart at runtime rather than reading the topology up front. That is a limitation
of the frozen schema; it is recorded here rather than worked around by inventing
a ninth table.

## 3. First defect: a manifest that imported and stored nothing

The first build (`press9.L5X`, generated
`4F195CBD9965374630670361B2342476A837D52FE75BCFE993172061E47F383E`) imported
with:

```
<Summary Warnings="2" Errors="0"/>
Mnemonic='XMLSrv_W_DD_SET_GENERAL_WARNING'
SecondaryMnemonic='RxE_COMM_INVALID' PropertyName='Value'
```

at lines 1188 and 4411 — the header's `ContentHash` and the first
`Localization` row. Two warnings, zero errors, and an ACD that opened fine.

Reading the project back is what exposed it:

| build | ASCII string members | non-empty after read-back |
|---|---|---|
| `press9` (bare text) | 227 | **0** |
| `press11` (quoted) | 227 | 208 |

```
press9  <DataValueMember Name="LEN" ... Value="0"/>   <![CDATA[]]>
press11 <DataValueMember Name="LEN" ... Value="16"/>  <![CDATA['42334AD69FD1A3AB']]>
```

Every published name in the first build was blank. The manifest existed, had the
right types, the right tables and the right counts, and carried not one name.

**Cause.** Logix does not accept bare characters as ASCII string data. Every
place Studio itself writes a string — an L5K initialiser, a `Data
Format="String"` block — it wraps the characters in single quotes and escapes
with `$`. No Studio export in the workspace happened to contain a *non-empty*
string inside a decorated structure, so there was no local sample to copy; the
quoting convention is uniform everywhere else Studio emits ASCII, and that is
what the fix follows.

**Fix.** `fraktal_ab_manifest.ascii_literal` quotes and escapes: `$` → `$$`,
`'` → `$'`, printable ASCII verbatim, anything else as `$XX`. `LEN` counts
characters, not escape sequences.

**Why the warning was not enough.** A two-warning, zero-error import is exactly
the shape of a benign import. The read-back is what made it a defect rather than
a note — the same rule the rendition gate already runs under: silence is not
parity, and acceptance is not publication.

## 4. Second defect: two paths under one name

With the key string fixed at 32 characters, 27 of the application's 206 portable
keys did not fit. Truncation was silent, and two pairs truncated to the same
text:

```
project.reason.two_hand_released.action      -> project.reason.two_hand_released
project.reason.two_hand_released.consequence -> project.reason.two_hand_released
project.reason.part_not_present.action       -> project.reason.part_not_present.
project.reason.part_not_present.consequence  -> project.reason.part_not_present.
```

A client resolving a reason by portable key would have conflated an operator
action with its consequence. This one never reached the controller — the tests
caught it — but it would have imported cleanly and read back cleanly, because
the truncated strings are perfectly valid strings.

**Fix.** The frozen contract sizes a string type "to the declared maximum", and
that is now taken literally:

* `key_string_length(app)` returns the longest declared key rounded up to a
  multiple of 8, floored at 32. For the press demo the longest key is 44
  characters, so the published type is `FRK_T_PressKey48`.
* The width is published in the header as `KeyLength`, so a client sizes its
  read from the manifest rather than from a constant it was compiled with.
* A key that does not fit is now a **build failure**, not a shorter string.

## 5. What the manifest contains

| table | rows | capacity |
|---|---|---|
| Roots | 1 | 4 |
| Modules | 4 | 16 |
| Nameplates | 0 | 16 |
| Fields | 142 | 192 |
| Operations | 5 | 32 |
| Localization | 206 | 224 |
| Rationalization | 12 | 32 |
| OptionalProfiles | 0 | 8 |

```
ContentHash     42334AD69FD1A3AB
ConfigRevision  4338506
KeyLength       48
EstimatedBytes  22112
Valid           1
Truncated       0
```

Against S7's measured budget, at the published `KeyLength` of 48:

| tag | row bytes | rows | bytes |
|---|---|---|---|
| `FRK_Press_MfHeader` | | | 208 |
| `FRK_Press_MfRoots` | 20 | 4 | 80 |
| `FRK_Press_MfModules` | 40 | 16 | 640 |
| `FRK_Press_MfNameplates` | 36 | 16 | 576 |
| `FRK_Press_MfFields` | 32 | 192 | 6,144 |
| `FRK_Press_MfOperations` | 32 | 32 | 1,024 |
| `FRK_Press_MfLocalization` | 56 | 224 | 12,544 |
| `FRK_Press_MfRationalization` | 24 | 32 | 768 |
| `FRK_Press_MfOptionalProfiles` | 16 | 8 | 128 |
| **total** | | | **22,112** |

That is half the 43,728-byte manifest S7 read completely and coherently in
293 ms at a 500-byte connection, so this manifest sits inside a budget already
measured on this target rather than one assumed for it. The largest single tag
is `MfLocalization` at 12,544 bytes, which needs fragmented reads at every
connection size S7 measured — the same read shape S7 already made normative.
**None of this is a runtime measurement:** it is arithmetic over the published
capacities, and the actual read stays owed until a download is authorized.

`Nameplates` and `OptionalProfiles` are empty because this application declares
none. They are published as zero rows rather than as zero-filled rows pretending
to be data, and the header says so — a reader never has to guess how much of a
table is real.

Two members name structures that do not exist yet: a module's `RegistryIndex`
and a root's `MailboxId`. They are published as zero, meaning "not published"
rather than "id 0", under the names the frozen contract requires. The
generator's scope fence forbids `Registry` and `Mailbox` constructs and now
exempts exactly those two names, by exact name — renaming them to slip past a
substring check would have put the manifest out of step with the frozen schema
in order to keep a fence quiet.

## 6. Two things a gateway must not assume

Both were written into this module as guarantees it does not actually keep, and
both are now stated in the code and pinned by tests — because the gateway is
about to be written against exactly these words.

**`ConfigRevision` is not ordered.** It is derived from the content hash, so a
later revision can be numerically smaller than an earlier one: adding one reason
to the press demo moves it from `4338506` to `12600`. This is sound for the
coherence protocol S7 made normative — read the revision, read every table, read
it again, accept only if it did not change — because that needs difference and
never ordering. It is *not* sound for a client that caches "the highest revision
seen", which would silently miss a change. Compare for inequality only.

**A numeric localization key is meaningful only within one revision.** Keys are
assigned in first-encounter order, so inserting or reordering a module renumbers
everything discovered after it. The portable string is the stable identity; the
number is a per-revision index into it. A client resolves names through the
Localization table it read *with* the tables it is reading, and never caches a
number across a revision change.

## 7. One typed exception, stated

The all-DINT contract rule has exactly one exception, and it is a shape Logix
dictates rather than a type anyone chose: a `StringFamily` UDT is `LEN` (DINT)
plus `DATA` (SINT array), and there is no DINT-based string to pick instead. The
test that enforces the rule now exempts that shape and a second test pins it —
members must be exactly `LEN`/`DATA`, exactly DINT/SINT, and exactly one such
type may exist in the project. **No BOOL member is introduced anywhere**; the
recorded S12 hole stays closed, and `BoolMembersInPublicUdt` is still 0.

## 8. Verification

| check | result |
|---|---|
| generated `press11.L5X` | `F7A5D752620F371821AE30168966FC6988438B8ECC7787F8F44E291AF0F4D61E`, 510,630 bytes |
| SDK import | `<Summary Warnings="0" Errors="0"/>` |
| read-back, non-empty strings | 208 of 208 expected (206 keys + ContentHash + ControllerIdentity) |
| read-back, longest key | `project.reason.two_hand_released.consequence` intact at 44 characters |
| read-back, string width | `DATA` `SINT` `Dimension="48"` |
| manifest tag access | every manifest tag `ExternalAccess="Read Only"` |
| test suite | 402 tests, up from 346 |
| full gate, clean checkout | 42 stages, 0 failures |

### The full gate, from a clean checkout

Cloned at `bc95017`, offline probe rebuilt from source, seed created by the
probe (`609B7F7A2F6C805E3E7DA83617F4D91804F34068658FA214F917B9B6D0F7FF08`):

**42 stages, 0 failures.** Ten fixtures generated, imported `0/0`, round-tripped
canonically, census-compared and Studio-verified:

| project | Verify |
|---|---|
| s1, s2, s11, s12, s4matrix | 0 errors, 0 warnings |
| s7manifest, s9coherence, s16, reference | 0 errors, 0 warnings |
| **pressdemo** (manifest-carrying) | **0 errors, 0 warnings**, 0 of 12 messages |

For the press demo specifically:

```
generated            53F8459439AA3FEEDFBCEE6E4D37C7BE381006869A02A5F1B8B576BCE7B89EDF
import               Warnings 0, Errors 0
canonical round trip true   (24ECD51B73422D51824242C44CC943C882A233188B018F615B84EF76098423CA)
construct census     true   14 DataTypes, 4 AOIs, 40 controller tags, 1 program, 1 task
chart comparison     true   FRK_PressProgram/FRK_PressAutoSfc
string read-back     208 emitted, 208 survived, none lost
```

The generated hash differs from `press11` above because the gate creates its own
seed; regenerating from the standalone seed still produces `F7A5D752…`.

**One stage failed on the first attempt and it was not a verification result.**
`s4matrix:verify` came back failed because the harness threw from `AppActivate`
— Studio's window was momentarily absent — and the exception aborted the stage.
Re-run alone, `s4matrix` verifies `0/0`. Rather than leave a flake that reports
itself as a Verify failure, the harness now retries activation, **sends no
keystrokes at all** when Studio will not come forward (keys aimed at whatever
window does hold focus are worse than a missed attempt), and raises "Verify was
not run", which is a different claim from "Verify produced no summary". The gate
run recorded above is the one taken after that fix, and it needed no re-runs.

### The read-back is a gate stage

The read-back is now a gate stage rather than a one-time check.
`fraktal_ab_phase0_gate.string_readback` counts the non-empty ASCII strings the
generator emitted and requires every one of them to be present in the exported
project, for **every** fixture — not only the press demo. Its own tests include
the recorded failure: emitted with content, read back blank, stage fails and
names what was lost.

## 9. Deferrals still standing

Publishing the manifest does not close what Phase 4 recorded as owed: the
registry, the event core, release/access enforcement and the provider seam. The
manifest describes them where the frozen contract requires a field and publishes
zero where they do not exist. Nameplates remain unpopulated because no module
declares one.
