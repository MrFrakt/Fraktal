# Fraktal/TIA operations and GRAPH continuation (2026-10-16)

Continuation of [line sets and bound mirrors](TIA_LINE_SETS_MIRROR_2026-10-16.md).
Generator0.22 remains a draft reference-1500 implementation. The original
`Fraktal` runtime is preserved; new software runs only on reserved, unmapped
CPU1516 test instances. The physical1214C and its output commissioning gates
are unchanged.

## Implemented scope

- **P2/P3/P4:** V3 weekly calendar, target latching, shift history and atomic
  close/reset; machine-state priority; OEE factors/trend/reset; per-model ideal
  cycle/work baseline and work-only degradation. The frame owns cyclic work.
  Shared line edits, sets/imports and mirror admission validate the whole calendar
  before commit. Empty calendars, overnight/week boundaries, off-time, overlap,
  invalid masks/durations and clock discontinuity are explicit cases.
- **P5:** composition nameplates, build-constant engineering gates and native
  system health. The gate register is static self-description generated from
  the same declaration as standing LOW/SYSTEM AUTO_RESET events. Inactive gates
  are absent. Native `RT_INFO` measures task execution; `RD_SYS_T` establishes
  availability. CPU/memory/IPC/PN metrics and synchronization stay unavailable or
  unqualified, never fabricated healthy. The health expression method is derived
  from the Core implementation.
- **P6 subset:** per-mode continuous/single-step/hold-to-run, named pacing waits,
  shared alarm shelving/monotonic expiry, and Core-derived signal tower/lamp test.
  Single-step grants one ready transition. GRAPH preserves its previous-scan
  transition result while a released hold suppresses pending progression.
  Shelving changes annunciation and never removes a blocking latch. Registered
  reason metadata, including module/TCP bands, comes from the one rationalization
  registry; safety/unknown/commissioning reasons fail closed for shelving.
- **P7 subset:** teach capture binds a registered scalar to the owning module's
  published OutImm/OutCmd field of matching storage type. It reads the machine,
  ignores client text, and uses the ordinary authority, revision, range, staging,
  persistence and audit path. Invalid schema/revision/value returns
  `RECIPE_INVALID`; access/readiness refusals retain their actual explanation.
  Class policy and runtime model creation remain open.
- **P10:** wired GRAPH CHANGEOVER and shared LoadPosition join AUTO/HOME.
  CHANGEOVER offers a real alternative jump880→810. ST/LD twins remain unwired.
  Sequence-owned decision helpers retain an answer behind pacing and do not ask
  again until that step is rearmed. Private sequence owners publish progress
  through the shared view. Hardware lives under `00_System/Hardware`; Main stays
  a calling routine. Native GRAPH uses separate parameter-instance DBs.
- **P11 subset:** fixed Core host-event records, per-deployed-Unit bounded rings,
  sequence/cursor/count/capacity and explicit overwrite indicator. Part, mode and
  changeover lifecycle edges emit centrally. Public views refresh on events;
  clients do not accumulate history. The optional durable FIFO/MES adapter is
  not implemented by this ring. Time synchronization remains unqualified.
- **P13 subset:** native assertion/result records, source-bound image fingerprint,
  non-vacuous JUnit harvesting and a fresh-project gate. The gate verifies native
  source/interfaces before its isolated download and always releases its test CPU.
  This extends the candidate contract gate; it does not close R3/R4/R5/R6.

The press's model config schema is3 and station config schema2: ideal/baseline
milliseconds and degradation percentage are explicit registered values. Ideal
and baseline default to0, meaning unconfigured, because no physical timing
baseline has been qualified. Older configuration images require migration or a
visible restore-loss refusal; the saved original image was not upgraded.

## Measured verification

| Gate | Result |
|---|---|
| Current operations primitive native13 | 0 errors, 0 warnings;280 canonical sources,82 FB/type interfaces,20 global DB interfaces match |
| Operations native assertion runner | **93 assertions,0 failures**; exact image fingerprint checked |
| Earlier two-root calendar/production fixture | **73 checks,0 failures** |
| Frame04 native source/interface read-back | 0 errors,0 warnings;513/126/87 match |
| Frame04 live features, attempt2 | **46 checks,0 failures**, including actual capture access/revision/range refusals and verified persistence |
| Wired press12 native compilation | **0 errors,0 warnings at both stages**;557/152/62 source/interface checks match |
| Press12 deterministic source replay | **254 sources match** |
| Native GRAPH read-back | LoadPosition4, AUTO19, HOME4, CHANGEOVER6 steps; actions/transitions/alternative/parallel structure match |
| Native optional LD read-back | Five examples;198 networks/192 calls match |
| Press11 live protocol/sequence regression | **53 checks,0 failures**: HOME pacing, retained decisions, CHANGEOVER jump/repeat/completion, private owners and lifecycle host event |
| Final press12 live regression | **63 checks,0 failures**, adding the read-only static engineering register and single-download offline web preparation |
| Fresh-project native gate | pass: fresh project, software0/0, native read-back, exact image fingerprint,93 assertions and cleanup |
| Siemens tool suite | **248 tests pass** |
| Lint, consistency and candidate contracts | clean; frozen V1 subset remains unchanged |

The fresh-project gate and expanded press-register replay have separate
completion logs in the evidence payload. Earlier failed attempts are retained
with their causes; a later pass does not rewrite them.

Hardware compilation of the isolated press copy has0 errors and two known
development-project protection warnings: no configured PLC protection level
and no CPU display password. They are explicitly recorded for the reserved
unmapped test CPU; every other warning fails preparation. They are not a
production protection qualification. Software compilation has0 errors/warnings.

## Corrections exposed by the gates

Native read-back caught facts that a clean compile did not prove: TIA strips
external-access flags from VAR_IN_OUT parameters, omits empty interface sections,
and serializes global DB initializers separately. The generator now emits those
native forms; DBs are separate sources and their instance DB imports follow the
owning FB. The canonical verifier was not relaxed. InOut parameters are references,
and the enclosing private owner is inaccessible through the Web API.

The native compiler rejected a prefixed formal parameter in the derived health
method, an unsupported RT_INFO OB constant spelling, and empty SCL branches in
the Core tower translation. Token-aware expression translation and native SCL
statement forms corrected them before qualification.

The first capture-range probe found a readiness refusal instead: its nested
synthetic Units had never received their independent finish stimuli. Attempt2
finishes all three cycles, proves READY, then obtains the actual `RECIPE_INVALID`
range refusal. The first press probe referenced a nonexistent count field;
the corrected probe reads the standard gate event and static register.

Simulator SDK enumeration of a large test FB caused excessive allocation. A tiny
separate result DB prevents it. Two consecutive full downloads during first press
web provisioning also grew the disposable simulator allocation to about7.6GB and
left about120MB on C:. Closing that test instance recovered over6GB without
deleting any file. The successful press run used one download and stayed near2.7GB
private allocation. Web preparation now occurs offline before hosting. Preserve
one extra test CPU at a time and wait for the host process to exit.

## Scope still open

The normal generator continues refusing an incomplete Line profile: shifts are
implemented, while classes and full press line integration remain. P6 manual-held
device commands, P7 class policy/model creation, P8 generic topology/PN health/
forcing, P9 module expansion and two-hand Start from READY, P11 durable host
delivery, P12 OUC TCP replication, full P13 contract/suite closure, P14 deployment
and reusable P15 connectors remain. The owner selected OUC TCP for P12 and deferred
device-specific robot/vision/axis ports. Physical reference timing, synchronized
clock qualification, loss/endurance and signed deployment remain separate gates.

Raw logs, generated/native payloads and source hashes belong in
[`TIA_OPERATIONS_GRAPH_2026-10-16`](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_OPERATIONS_GRAPH_2026-10-16/).
Credential initializers/exports, engineering projects, simulator storage,
certificates and private SQLite backups are excluded. Hash witnesses identify
private omissions; prior sealed archives remain unchanged.

Seal:5,470 payloads plus `SHA256SUMS.txt`,107,781,438 bytes including the checksum
file. SHA-256 of `SHA256SUMS.txt`:
`6f14b54fc229e574376948e0fb73ca1124e0e67cd4466961f808e1adde893b3e`.
Two combined fixture sources are public derivatives with only the credential
initializer removed; four original private-source/export omissions have hash
witnesses. The native counts above identify the complete private verification.
The public frame derivative is independently compared against the corresponding
public native exports. SiemensAgent's derived index contains41 curated/report
documents, preserves project/general table counts and passes SQLite integrity.
