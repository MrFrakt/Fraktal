# Fraktal/AB — Implementation Plan
*How to start the Allen-Bradley port from where the documents now stand*

**Status:** working plan — **R0 complete; R1–R6 open** — derived from `ALLEN_BRADLEY_PORT_PLAN.md` (the *why* and
the phase structure) and `Fraktal_AB_Part_III.md` (the *binding* and its readiness
gates). Those two are authoritative; where this plan disagrees with them, they win
and this file is wrong.

---

## 1. Where the port actually stands

No production runtime exists in `FraktalCore/PLC/Allen-Bradley/`. Nothing has
been compiled, downloaded or run. The authority-only R0 phase is complete:

- Part III records **R0 PASS** and remains **spike-ready, not
  implementation-ready**. Runtime and library code **shall not** begin until all
  R0–R6 gates record PASS. Only disposable Phase 0 fixtures are permitted before then.
- The spike list grew from S1–S10 to **S1–S15**. The new ones are not
  refinements; two of them invalidate design decisions the previous draft had
  already made.
- The blocker set is now explicit: **S1, S2, S4, S7, S8, S9, S11, S12, S15**
  decide whether this is a conforming base port at all.

**The next executable step is R1 platform acquisition/baselining, not runtime
code.** The completed Core amendments and TC3 compatibility audit are recorded in
[`AB_R0_CORE_AUTHORITY_EVIDENCE.md`](AB_R0_CORE_AUTHORITY_EVIDENCE.md).

### 1.1 Two design corrections worth reading before anything else

The documentation review corrected two things the earlier drafts got wrong.
Both change what gets built, so they are not editorial:

**Native SFC is supported, but not inside an AOI.** Studio 5000 supports SFC as
a main or JSR-called program routine. The real call-boundary restriction is that
an AOI cannot `JSR` a project Routine and its primary logic cannot be SFC. Part
III therefore defines two forms: a reusable generated ST/LD sequence AOI, and a
program-owned native-SFC Unit/EM chain with one stateful routine/tag set per
deployed owner, called by a generated JSR/SFR wrapper. The SFC writes sequence
intent only; the root/module AOIs still execute unconditionally once and consume
that intent on the next scan. **S4** must prove
the chart's L5X round trip, and **S11** must prove ordering, the intentional
one-scan command/result loop, reset/re-entry, prescan/restart and branch parity.
Until both pass, SFC is provisional; failure disables the SFC form, not the
ST/LD reference form.

**Safety Tag Mapping was the wrong mechanism.** The old draft called it a
"one-way safety → standard" publication path and praised it as a closer fit to
Core §9 than TwinCAT's convention. It is the opposite direction: Tag Mapping maps
*standard* tags into *safety* tags for safety logic. The correct path is a
generated standard-task adapter that **reads controller-scoped safety tags
directly** — Logix permits standard logic to read but not write them. A binding
that shipped on the old sentence would have been describing a mechanism that does
not exist.

Both corrections are the spike programme working as intended, before code rather
than after.

---

## 2. What can start now, and what cannot

| Work | Blocked by | Needs Rockwell? |
|---|---|---|
| **Phase 1 Core amendments** (R0) | **complete** | no |
| Manifest / mailbox / HostEvents **logical** schemas | unblocked; Phase 2 work | no |
| Gateway protocol negotiation design (AB §11.3) | unblocked; Phase 2 work | no |
| Everything else | R1–R6 | **yes** |

This host has **no Rockwell tooling installed** — no Studio 5000, no Logix
Designer SDK, no FactoryTalk Logix Echo. Verified: none of the four standard
install roots exist. Every spike from S1 onward needs a named controller,
firmware, Studio 5000 edition, and (for the CI gate) SDK licences. **Do not
attempt to fake a spike with a hand-written L5X file** — S4 exists precisely
because L5X round-trip fidelity is unproven, and a file this repo generates
without an import/export cycle proves nothing.

---

## 3. The plan

### Step A — Phase 1 Core amendments — COMPLETE (R0)

The two authority amendments are complete. Their normative crosswalk, TC3 audit,
tooling audit and O1–O10 review are in `AB_R0_CORE_AUTHORITY_EVIDENCE.md`.

**A1. OOP-neutral lifecycle (Core §2.2 / §3.14 / §5.5) — complete.**
Core names the **obligation** — behavior is defined once and reused; a concrete
type supplies device logic only; the lifecycle runs in a fixed order — and Part II
binds it to inheritance while Part III binds it to generated composition.

The original surface included 9 occurrences of `EXTENDS`/`SUPER^` and an ST-only
framework rule. The amendment changed the owning semantics rather than merely
renaming tokens.

*Exit met:* Part I states required behavior without naming a platform mechanism;
Part II binds the TC3 mechanism; the TC3 conformance claim is re-audited and
unweakened.

**A2. Transport-neutral self-description (Core §3.10 / §4.8 / §7.7 / §11) — complete.**
Core defines the **Fraktal Self-Description Service** as a behavioral contract;
Part II binds TF6100/OPC UA, while Part III makes EtherNet/IP plus the Fraktal
gateway the default and OPC UA an alternative projection.

The original audit found **64** OPC UA mentions, including mandatory base-service
mechanics. The amendment retains OPC UA where it is a provider option or an
explicit binding-qualified profile and removes it as a base-service prerequisite.

*Exit met:* the TC3 mechanism remains bound in Part II; no base Core conformance
`shall` requires TF6100/OPC UA; the normative diff and O1–O10 impact are reviewed.

The R0 exit is recorded in Part III's readiness table. It authorizes spikes and
Phase 2 contract work, not production runtime/library implementation.

### Step B — Phase 2 documentation gates that need no hardware

Freeze the **logical** schemas: manifest tables, root mailbox request/response,
HostEvents ring, protocol negotiation. Part III already specifies all four in
useful detail — the work is turning prose into a versioned normative schema with
`FRK_MAX_*` capacity names left as named holes for S3/S7/S12 to fill.

Explicitly **not** now: physical UDT layout, capacities, poll budgets. Those are
spike outputs, and inventing them creates numbers that look authoritative and are
not.

### Step C — Phase 0 spikes (needs the platform)

Run in blocker order. The plan's own sequencing: **S1, S2/S11, S4/S15, S12**
first, then S7/S8/S9 before any gateway or runtime library work. The S4/S11
fixtures shall include one minimal ST/SFC parity chain generated from the same
graph declaration; do not start with a production-sized chart.

Prerequisite before any spike runs — R1: a named controller catalogue number,
firmware revision, Studio 5000 edition and version, communication module, and
gateway-host baseline. "A ControlLogix" is not a baseline.

### Step D — everything after

Phases 3–8 as written in the port plan. They do not need re-planning here; they
need R0–R6 to be PASS first.

---

## 4. What this plan does not decide

- **Whether the port should happen.** That is a go/no-go at the Phase 0 exit, and
  it is a real decision — S4 (L5X fidelity) and S15 (automatable Verify/Build)
  can each end the port as drafted.
- **Which controller family.** R1, and it constrains everything downstream.
- **Whether motion, connectors, or OPC UA projection are in scope.** S13/S14/S10
  gate only their own optional families; none blocks the base port.

---

## 5. Working rules for whoever picks this up

1. **Never cite a `[PROVISIONAL Sn]` clause as evidence.** Part III says this in
   AB §0 and it is the single easiest rule to break by accident.
2. **A failed gate changes the binding or stops the port.** It does not become an
   undocumented implementation exception.
3. **Do not write runtime or library code before R0–R6 are PASS.** Disposable
   Phase 0 fixtures are the only exception, and they are disposable — do not let
   one graduate into the base by being useful.
4. **The documents are the source of truth.** This plan summarises; it does not
   override. Read AB §0 and the port plan's §7 phase list directly.
