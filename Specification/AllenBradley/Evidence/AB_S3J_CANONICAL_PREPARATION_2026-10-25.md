# S3j canonical fieldbus preparation - offline gates pass

Client date: 2026-10-25, America/Mexico_City. Work began on October 24 under
the owner's approved [D-1 to D-6 decisions](../AB_CANONICAL_PUBLICATION_S3J_CONTRACT_REVIEW_2026-10-24.md).
**The offline implementation and guarded native apparatus are prepared.
Native acceptance and scan measurement remain open.** No S3j download,
controller mode change or tag write occurred. Current authorization is false.
No commit or push. V2 remains inactive.

## What changed

The PLC now owns the separate Core fieldbus product. V6.5 adds DataProducts
bindings to the accepted V6.4 manifest. The generic reader obtains the source
Symbol, Core type description and canonical root from the PLC, then decodes
its Templates and type annotations. No station declaration, name pattern or
Core-type dispatcher enters the client. V6.0-V6.4 captures still decode.
The [wire draft](../AB_CANONICAL_PUBLICATION_S3J_WIRE_DRAFT_2026-10-24.md)
records the layout, read tiers, sampled-word HAL boundary and forcing scope.

The disposable genealogy catalog has three nodes and twenty channels:
Discrete_IO (parent, no channels), Discrete_IO.I (12), Discrete_IO.O (8).
It publishes **327 paths**: the reviewed 311 legacy paths plus sixteen new
word-node metadata fields. All 300 channel-path correspondences are enumerated
in Offline/implementation_inventory_01.json. Channel identity and address
values stay exact; the new nodes change their parent/index coordinates.
Counts and ParentIdx are INT, AnalogValue REAL, flags BOOL and enums DINT.
Core string widths and the 64/16 ceilings remain. Each node's live count hides
unused native array slots; the homogeneous channel stride is the largest
declared group, twelve here.

The PLC checks mapping counts, parents, directions, kinds, identity lengths
and duplicate Name/Path at activation. Invalid lengths are rejected before
byte access; matching identity hashes receive an exact byte comparison.
Identity bindings use a 64-bit fingerprint so an identity change invalidates
the on-demand cache. Missing sampled words fail closed. Per-direction quality
does not claim a complete module sample. The force capability stays absent:
this AB profile has no registered OUTPUT_FORCING gate, so idle MANUAL alone
cannot authorize a force, and the existing mailbox refusal path remains.

The fixture TypeId explicitly says "Fixture: sampled controller words".
It configures no physical I/O module, writes no physical I/O operand, and keeps
task output updates disabled. The production HAL's sampled-word record is an
explicit private boundary; hardware/electrical acceptance remains S7. The
previous S3i first-scan Line instrument is not emitted in this S3j image (R6).
The full 41-case apparatus and all inherited canonical surfaces are retained.

## Exact image

- Source L5X SHA-256:
  `2F0B2CE73C2ECB69B1DD7F32BB1AE1D66550811A0EF49C1D65E9AE2C7A753EEA`.
- Pristine prepared ACD SHA-256:
  `285BF972C5FD781C315F670CFEEED8AC01D566791DB84E4B17125CC9B8CC3212`.
- V6.5 ContentHash:
  `5CB700B26E0F3C48AE65FB06CB30E8BC62BDF536A0B710FBE898C9E8577C1231`.
- Legacy genealogy identity remains `6DEC4C1DC2F7F78A`.

## Gates

| Gate | Result / exact output |
|---|---|
| Full AB discovery suite, final | **2,248 pass**; Offline/ab_suite_03.log |
| Root test suites | **74 pass**; Offline/root_tests_04.log |
| AB spec / contracts / strict consistency | Pass; Offline/*_04.log |
| Whitespace | Clean; Offline/whitespace_04.log |
| Executed-ST oracle | Operational, fault, inhibited, offline, per-direction partial samples, invalid validity flags, forty seeded signed-word vectors, corrupt mappings and duplicate identities match independent reference; invalid lengths fail without out-of-range reads |
| Generic V6.5 discovery | Arbitrary source/type/root names, unknown descriptive Core type, live count views, read-only loader and malformed/duplicate/missing binding refusal pass |
| v38 EchoController / PhysicalController | Both accepted, **0 warnings / 0 errors**; native_*_04 logs |
| Strict read-back | **Equivalent=true**, 60 bodies, 42,043 initial values; SFC 21 steps equivalent; readback_*_04.log |
| Effective access / SDK audit | Both pass; product Read Only, private work None, explicit fixture source Read/Write, existing mailbox surface retained; access_*_04 / sdk_*_04 |
| Prepared ACD read-back | Equivalent=true; Preparation/canonical_prepared_compare.json |
| Automatic Studio Capacity | **1,743,080 used / 1,402,648 available / 3,145,728 total Blocks**, 55% displayed; measured fit, source unchanged, review closed |
| Capacity delta | **+89,648 Blocks** versus accepted R1/R2 (1,653,432); 1,020,432 below accepted S3i |
| Accepted images | All ten S2-S3i images and the accepted combined R1/R2 source regenerate byte-identically |
| Old capture replay | **1,245 pass**, across V6.0-V6.4 and all ten earlier stages; exact old snapshots and type-annotation substitution agree apart from expected configuration identity |
| Current source regeneration | Byte-identical to the compiled source; Offline/regeneration_01.json |
| Helper build | Success, **0 warnings / 0 errors** |
| Offline download gate replica | All comparisons pass: baseline measurement hash/arithmetic, candidate Capacity pin, ACD pin and prepared read-back |
| Negative authorization | **4 / 4**: three SDK modes and the I/O actor refuse before controller/SDK access |
| Fixture mechanics | Nine vectors, exactly eighty allowed DINT writes including original-word restoration; partial-write failure stops and restores; independent captures only |
| Read-only live guard / baseline probe | Expected Echo identity/service/listener/Remote/Run, no fault; MANUAL/idle/logged out, five documents equal |
| Native S3j download / regression / scan | **Not run - current exact-image authorization pending** |
| HMI / physical / CIP Security | No HMI change; Flutter not applicable. Physical/security acceptance not claimed |

The preceding R1/R2 native cumulative maximum was 9,829 us against 10,000 us,
with zero overlaps. S3j has its own unmeasured native cost. Memory fit does not
close scan acceptance, and neither the task period nor validation is relaxed.
The migration frame now includes the topology and independent word source;
S4 still requires row/group coherence and on-demand identity reads.

## Proposed native session

Target: local Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0.
The guarded helper supports backup, deploy-canonical and restore-genealogy
only. No retained-cycle, fault-clear, power or clock operation is added.

1. Fresh current service/listener/identity/fault/keyswitch/no-driver/dump
   guards, MANUAL normalization if needed, fresh preflight and backup.
2. Guarded Program/download/Run of the exact 285B... ACD; SDK, strict
   read-back and effective-access audits.
3. Five-document restoration and **41 inherited candidate cases**, with
   read-only paired equivalence including the fieldbus product.
4. **Nine fixed simulated-word vectors**, exactly **80 DINT writes** including
   restoration, only under FRK_Press_SimIo. Cases: operational, channel fault,
   inhibited, offline, input-only, output-only, fault unknown, signed words,
   ineffective unregistered gate claim. The source is restored exactly.
5. Read-only all-path equivalence, generic discovery, native record sizes and
   twenty TASK samples; independent packet/reference replays.
6. Hash-checked genealogy rollback copy, five-document restore,
   **31 baseline regressions**, MANUAL cleanup, final state/preflight/scan.

Existing active-login and identity guards remain. Failed candidate stages
enter the inherited rollback path. Fault clears, clock changes, firmware or
network changes, power operations, hard kills and vendor-state edits remain
excluded. No production gateway write posture is changed by this fixture.

## Development history retained

The initial focused run used a REAL literal outside the integer interpreter's
subset; it now uses the established typed REAL model and the emitted assignment
the native compiler accepts. A second run caught an address spelling difference
(`Local:1:I.Data.0` versus the existing `Local:1:I.0`); the PLC initializer was
corrected and the exact oracle passes. Intermediate compiler/Capacity images
remain in Offline; the final source/ACD pins above alone govern this session.
The earlier draft native workspace was never armed or run. Later hardening
added the identity fingerprint length and safe invalid-length checks, followed
by fresh full tests, both compiler/read-back gates and exact-image Capacity.

Offline: `C:/work/fraktal-ab-s3j-20261024/s3j_01/`.
Session: `C:/work/fraktal-ab-s3j-20261024/prepare_fb6598e2234d43f99f5ae75e718f9860/`.
Append-only payload: [manifest](AB_S3J_CANONICAL_PREPARATION_2026-10-25/manifest.json).
No credential file or ACD binary is archived. Prior evidence and owner Siemens
archive edits remain untouched. Native S3j, S3k, press renditions and S4-S7 stay
open; current confirmation of this exact session is the next gate.
