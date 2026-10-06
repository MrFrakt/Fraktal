# Fraktal/AB R4 — the regeneration gate, run from a clean checkout

**Gate:** R4 gates — automated L5X regeneration and lint plus controller
Verify/Build and import checks that run from a clean checkout

**Result:** **PASS. A fresh clone, with no build output and no leftover
artifacts, produces every Phase 0 fixture from a seed the SDK creates, imports
each with a gated clean summary, round-trips each canonically, passes a
generated-versus-exported construct census, and puts every one of them through
Studio v33 Verify Controller at 0 errors and 0 warnings. Every stage green, no
stage skipped.** The regeneration is also **canonically reproducible across
seeds**: a fixture regenerated from a different seed than the one used for its
own evidence session produced a byte-identical canonical export.

**Date:** 2026-09-06

**Repository revision under test:** `b74602c` (eight fixture legs), re-run at
`c63b5f4` with the R5 reference suite as a ninth leg

**Scope:** offline regeneration, import, round trip, census and Studio Verify.
**No controller-changing operation occurred for this record**, and the gate
contains no tool that can perform one.

## 1. What R4 asked for, and what was missing

R4 requires "automated L5X regeneration and lint plus controller Verify/Build
and import checks run from a clean checkout". Three things stood between the
repository and that sentence, and all three are now closed.

**The gate had no S16 leg.** It regenerated and round-tripped S1, S2, S11, S12,
the S4 matrix, S7 and S9 — every fixture except the one whose evidence was
newest. Nothing in the S16 record was reproducible by running the gate. S16 is
now a full leg: seed, generate, import, round trip, census and Verify, the same
as the rest.

**The gate could not run on the only machine that can run it.** The offline
probe must be built `win-x86` to match Rockwell's 32-bit client, so it can only
target a framework the workstation has an x86 runtime for. The project named
`net10.0` and client `2.2.1109`; the licensed v33 bench workstation carries an
x86 runtime of `8.0.7` and SDK `2.00` / client `2.0.861`, and that client ships
inside the SDK installation rather than on nuget.org. A `net10.0`/`win-x86`
build compiled and then failed to launch. Both the framework and the client
version are now MSBuild properties, defaulting to what the bench workstation
actually has, and the gate finds the built probe under whichever framework
produced it rather than hard-coding one.

**A clean checkout could not restore.** The Rockwell package directory contains
spaces, which `dotnet`'s source flag silently rewrites into a relative path — a
failure that reads as "package not found" and sends you looking in the wrong
place. A `NuGet.config` beside the project supplies that source. A fresh clone
now restores and builds with one command and no flags.

## 2. Method

A genuine fresh clone into a directory that did not exist, with no `bin`, no
`obj`, and no artifacts of any kind:

```powershell
git clone <repository> C:\work\cleanclone
cd C:\work\cleanclone\FraktalCore\PLC\Allen-Bradley\tools\Fraktal.Ab.OfflineProbe
dotnet build Fraktal.Ab.OfflineProbe.csproj -c Debug -r win-x86   # 0 warnings, 0 errors
cd C:\work\cleanclone
python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_phase0_gate.py `
    --workspace C:\work\gate_ws --verify --verify-timeout 300
```

The gate's own stages, per fixture: create the empty v33 seed **through the
SDK** and record its canonical hash; regenerate the fixture from that seed;
import it through the SDK requiring a clean import summary and no SDK error
event; export, re-import and re-export requiring canonical equality; compare the
generated declaration against the first export as a construct census; and, with
`--verify`, run Studio v33 **Verify Controller** against the imported ACD.

The canonical comparison is deliberately **export-against-export**, because the
SDK legitimately rewrites a generated declaration on first import. The census is
what closes the hole that leaves — a construct the import dropped would be
equally absent from both exports, and only the census would see it.

## 3. Result — every stage green

Seed canonical SHA-256:
`609B7F7A2F6C805E3E7DA83617F4D91804F34068658FA214F917B9B6D0F7FF08`

| Leg | Round trip | Census | Studio v33 Verify | Input unchanged |
|---|---|---|---|---|
| `s1` data path | identical | equivalent | **0 / 0** | yes |
| `s2` nested AOI | identical | equivalent | **0 / 0** | yes |
| `s11` sequence execution | identical | equivalent | **0 / 0** | yes |
| `s12` type map | identical | equivalent | **0 / 0** | yes |
| `s4matrix` construct matrix | identical | equivalent | **0 / 0** | yes |
| `s7manifest` manifest | identical | equivalent | **0 / 0** | yes |
| `s9coherence` coherence | identical | equivalent | **0 / 0** | yes |
| **`s16` command handshake** | identical | equivalent | **0 / 0** | yes |

`Passed: true`, `Failed: []`. Every Studio Verify additionally reported the
input ACD hash unchanged and Studio closed cleanly; the verify script refuses a
project inside the repository and performs no online operation.

The census counts are the structural claim each fixture's own record makes —
for S16, `DataTypes 1, AddOnInstructions 2, ControllerTags 11, Programs 1,
Tasks 1`, which is the "two AOIs, one UDT, one program, one task" its
declaration asserted, now reproduced from a clean checkout rather than asserted.

### The reproducibility result worth keeping

The S16 leg regenerated from a **different seed** than the one used in the S16
execution session — each `--create-seed` produces its own ACD, so the raw
generated L5X differed (`78F780FF…` here against `103DF28E…` in that session).
**The canonical export hash was identical:**
`427129CAA95C68338BC9D8823C186C8866B460EAFF4C88BD85BDE3751BCF9958`, the same
value recorded in
[`AB_S16_EXECUTION_EVIDENCE_2026-09-06.md`](AB_S16_EXECUTION_EVIDENCE_2026-09-06.md).

That is the property a regeneration gate exists to establish. The raw bytes of a
generated project are a function of the seed and carry timestamps; what must be
stable is the *project*, and it is — independently of which seed produced it,
and independently of the session that produced the original evidence. A fixture
whose canonical form drifted between regenerations would make every hash in
every prior record unverifiable.

## 4. What could not run unattended, stated exactly

**Studio Verify is opt-in, and that is a real limitation, not a formality.**
Verify is reachable only through UI Automation against a logged-in desktop
session: it needs a visible Studio window, keyboard-driven menu invocation and
UI Automation reads of the error and warning panes. A gate that always required
it could not run on an unattended agent at all.

The run recorded above **did** include Verify, on a logged-in console session
(session 1, active). So the semantic gate is proved, not skipped. What is not
proved is that Verify can run headless, and this record does not claim it.

Concretely, of the gate's stages:

| Stage | Unattended? |
|---|---|
| Seed creation through the SDK | yes |
| Fixture regeneration | yes |
| SDK import with log gate | yes |
| Export / re-import / re-export, canonical comparison | yes |
| Construct census | yes |
| **Studio v33 Verify Controller** | **no — requires a logged-in desktop session** |

Two further limits belong here rather than in a footnote:

1. **Downloading is not part of the gate and is not automated.** No tool in this
   toolchain can download. On this workstation, Studio v33 additionally crashes
   when its Download command is invoked programmatically — a null-pointer read
   at a fixed address inside the shared MFC runtime, reproduced twice, with the
   same faulting address both times. The diagnosis and the bounded workaround
   are recorded in the S16 execution record. Deployment is a human act under
   current explicit authorization; R4 does not need it and does not claim it.
2. **SDK `BuildAsync` is not a semantic gate** and is not used as one. Studio's
   Error List is the semantic authority, which is why `--verify` exists at all.

## 5. The nine-leg re-run

After the R5 reference suite was added, the gate was re-run the same way from a
second fresh clone at `c63b5f4`, with the reference suite registered as a ninth
leg so that R5's artifact is reproducible from a clean checkout on the same
terms as every spike fixture. That run is recorded in
[`AB_R5_REFERENCE_SUITE_EVIDENCE_2026-09-06.md`](AB_R5_REFERENCE_SUITE_EVIDENCE_2026-09-06.md).

## 6. What this settles, and what it does not

**S15 — "SDK can import, Verify/Build, export, download and capture diagnostics
unattended" — is settled in the part that R4 needs and narrowed in the part it
does not.** Import, export, canonical round trip, census and diagnostic capture
are automated and reproducible from a clean checkout. Verify is automated but
requires a logged-in desktop. Download is deliberately not automated. The spike
register records that split rather than a bare PASS.

Still owed, and not claimed here:

1. **Headless Verify.** Nothing here shows Studio Verify running without a
   desktop session. A CI runner would need one.
2. **The probe's package pin across workstations.** The defaults now match the
   bench; a workstation carrying SDK 2.02 / client `2.2.1109` builds by
   overriding two MSBuild properties. Neither pair is discovered automatically.
3. **The root cause of the Studio download crash.** Bounded and reproduced, not
   explained.

## 7. Status

| Item | State |
|---|---|
| Clean-checkout regeneration | **PASS** |
| SDK import, gated | **PASS** — clean summary, no SDK error event, every leg |
| Canonical round trip | **PASS** — every leg, and canonically stable across seeds |
| Construct census | **PASS** — every leg |
| Studio v33 Verify Controller | **PASS** — 0/0 every leg, on a logged-in desktop |
| Unattended operation | partial, and itemised in §4 |
| **R4** | **PASS** |

No conformance claim is made. No production Fraktal/AB runtime or
module-library code was written.
