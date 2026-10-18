# Fresh-chat handover prompt — remaining Fraktal/AB features

Copy the following prompt into a fresh chat working in `C:\Projects\Fraktal`.
It describes `main` at the commit that adds this file (2026-10-06); the work
that had accumulated uncommitted in the working tree is part of that commit.

---

Implement the remaining Allen-Bradley (Fraktal/AB) features in this repository,
measured against Fraktal Core and the TwinCAT binding as behavioral oracle. Keep
one committed declaration as the source of every generated artifact, keep the
controller within its memory budget, and carry each feature through offline
gates and the owner's native acceptance. No controller-changing operation is
authorized by this handover.

Start by reading `AGENTS.md` (especially §3a), `Specification/README.md`, the
relevant clauses of `Fraktal_Core_Part_I.md`, `Fraktal_AB_Part_III.md` and
`Fraktal_TC3_Part_II.md` (TC3 §3.8b and §7.7 for the newest TwinCAT behavior),
`FraktalCore/PLC/Allen-Bradley/README.md`, `Specification/HMI_CONTRACT.md`, and:

- `Specification/Guides/AB_NEW_PROJECT_GUIDE.md` (sections 3, 5 and 7)
- `Specification/AllenBradley/AB_PORT_COMPLETION_PLAN_2026-10-04.md` (stage order)
- `Specification/AllenBradley/AB_PHASE6_RETENTION_CHECK_PLAN_2026-10-04.md`
- `Specification/AllenBradley/AB_TO_TC3_HANDOVER_PROMPT_2026-10-04.md`
- `Specification/Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md` (history)
- the press75 fit/acceptance, press76 offline, press77 link-failure and press78
  memory-reduction records under `Specification/AllenBradley/Evidence/`
- `FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md` §159–§163 and
  `Specification/Evidence/2026-10-06_TC3_MissingFeatures.md` /
  `2026-10-06_TC3_PersistMedium.md` - what TwinCAT gained most recently, and the
  retention defect only a real restart exposed

Inspect current source before treating an old report or TODO as an absent
feature, and use primary Rockwell documentation for every GSV class, attribute,
instruction and type; do not invent names, layouts, fault codes or healthy samples.

## Baseline and limits to preserve

Reference bench: 1769-L24ER-QB1B, firmware 33.014, 192.168.100.89, serial
7036B510, 10 ms task. The last **owner-measured** memory baseline is press75
(`C:/work/press75.L5X`, SHA-256
`82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5`): online data/logic 758,568 /
786,432 bytes, 27,864 available, largest free block 27,376. Press76 (calendar V3,
+2,756 declared bytes) is prepared but unaccepted; press77 failed global linking
(offline estimate 13,428 bytes over); press78 removes 12,373 ST source bytes from
ConfigWrite/ConfigSets with zero declared-data growth, and the owner reported "its
good now" **without** an exact-artifact download transcript or new Capacity
figures. First establish, read-only and serial-guarded, which artifact is loaded
(manifest identity/revision), and obtain the owner's Studio Capacity Estimate of
the exact current artifact before any controller growth. Record declared-data and
ST deltas for every change; they are trends, not compiled memory.

Ask, and record in the station binding record, before starting any new station:
read-only or write-enabled gateway, and which controller family/firmware. The
press68 deployment's write-enabled S9 result is qualified for that deployment only.
Studio import, Verify, Capacity Estimate, download and write-enabled gateway
restarts are owner steps on the licensed desktop. Guard the exact serial and build
immediately before every authorized native stage. Hand-authored L5X is forbidden;
regenerate from the declaration. Never move RETURN/RTN/EXIT across extracted
routine or loop boundaries, and keep emitted formatting in `fraktal_ab_st_format.py`.

## Gap census - TwinCAT has it, AB does not (yet)

| Capability (Core clause) | TwinCAT now | AB now | Work |
| --- | --- | --- | --- |
| Retained data on a project-chosen medium (§3.8b) | `I_PersistMedium` (files / retentive pool); live station, line and model documents restored at start through the staged set path; sets and users on the same medium (§163) | controller tags are the retained class and a download resets them; sets are gateway files (`fraktal_ab_sets.FileStore`, JSON-lines); commissioned values cross a download only by seeding a fresh capture (`fraktal_ab_initial_config.py`); power-cycle/download/upgrade matrix unverified (Part III AB §2.8/§3.8 PROVISIONAL) | see item 1 |
| Durable local users (§7.7(c)) | runtime registration, image on a confidential medium | up to four declared registrations in private tags (`ExternalAccess=None`); no online PIN set by design | physical retention proof only; keep the no-online-PIN design unless the owner asks |
| Controller/platform health (§8.12) | IPC metrics and EtherCAT master state/counters (§161) | faults and time quality from GSV (S3 settled); CPU/free memory have no GSV source on this family and stay unavailable; module connection state PROVISIONAL S3 | item 3 |
| Time quality (§2.7) | observed OS clock, freshness, PLC/OS skew reported unsynchronized (§159, §162) | TimeSynchronize read; S1 offset is a commissioning script (`fraktal_ab_time_probe.py`); CIP Sync not commissioned | item 6 |
| Part traceability (§3.16) | local BY_POSITION carrier and canonical events | absent | item 4 (completion-plan stage 1) |
| Host events (§11.6) | fixed bounded projection | contract frozen, projection absent | item 5 (stage 4) |
| Signal tower / LAMP_TEST (§8.13) | reusable mapper | absent; no bench hardware | item 7 (stage 3) |
| Line mirror/shared root (§3.8e) | owner/mirror roles | owner only; Chrome Line controls and physical Line retention unaccepted | item 8 |
| Running-model set load (§3.8b) | refused | refused | item 9 (stage 6), shared with TC3 |

Not gaps - deliberate or platform exclusions; keep them visibly unclaimed:
control power and certified safety; Integrated Motion and PartFeed on the L24ER;
CPU/free-memory metrics on this family; MANUAL_HELD without a real hold-to-run
target; any firmware, clock or network change without authorization.

## Implement in this order

Respect the completion plan's stage order unless the owner reorders it; items 1
and 2 need no controller growth and may run alongside.

1. **Retention and the medium.**
   a. Run the retention check plan with the owner for values, accounts, sets,
      models and the line calendar across power cycle and download; record each
      value's outcome separately - one surviving value proves only itself.
   b. Put the gateway set store behind a store interface - the file store
      unchanged as its first implementation, so the project picks the medium the
      way TC3's `MAIN` does. Add a database medium only when the owner names a
      server, schema and credentials owner.
   c. Ask whether live configuration should also be kept as gateway documents and
      re-applied after a download instead of seeding each image. If yes: the PLC
      stays the only validator (staged, all-or-nothing load; model banks only
      through the provider/Changeover route, since direct model-set load is
      refused); Start and configuration writes wait until the restore answered; a
      medium that cannot answer is retried and announced, never replaced by
      defaults written over the documents; a loss is announced under the
      document's key. Accept it across real power cycles and downloads with the
      newest copy in each slot if copies alternate - the TwinCAT medium passed 234
      unit tests and still lost intact documents on its second real restart.
2. **Deployment acceptance without growth.** Exercise the packaged AB gateway/Web
   HMI installer path per `Specification/Guides/WEB_HMI_GATEWAY_DEPLOYMENT.md`;
   complete the owner's Chrome acceptance of the Line controls; establish press76
   (or its successor) fit only through the owner's Capacity/Verify/download.
3. **Module connection state and description** (stage 5): per claimed module,
   the GSV Module object's named attributes on the actual family into the
   existing topology/health owners; audit Nameplate/IDTA; version any frozen
   contract extension. Unknown codes stay visible as raw codes.
4. **Part traceability** (stage 1): opt-in carrier declaration, bounded native
   Part context, framework-owned canonical events requested by the chains' normal
   services, ST/SFC/LD outcome parity, fail-closed carrier errors - only once the
   memory headroom is measured.
5. **Host event projection** (stage 4): fed by the controller's event authority,
   delivered by the gateway, with ordering, gap/overflow and reconnect evidence.
6. **Time** - commission CIP Sync only where cross-controller ordering is needed
   and the owner authorizes it; otherwise record the S1 host offset at
   commissioning. A read-only gateway observation of the controller-to-host
   offset, mirroring TwinCAT §162, is optional and never writes the clock.
7. **Signal tower** (stage 3) only for real, owner-named hardware with verified
   electrical mapping; otherwise unclaimed.
8. **Line composition**: mirror/shared-root transport and physical retention.
9. **Running-model set load** (stage 6): design once for both bindings through
   prepare/readiness/commit, never a live ParCfg overwrite.

## Engineering and completion gates

O9/O4 apply: one source per fact, behavior generated once, additive and versioned
released layouts (DINT contracts on v33), minimum runtime and discovery surface.
Never weaken permissions, freshness, input validation or condition reports to
obtain fit; optimize the owning implementation first.

Offline, every change runs the AB tool suite by discovery from
`FraktalCore/PLC/Allen-Bradley/tools`, `python tools/check_ab_spec.py`,
`python tools/check_ab_contracts.py`, `python tools/check_consistency.py --strict`
with its tests, the generated-size comparison against the last completed download
and the rendition gate for all three sequence forms. For shared HMI changes use
Flutter 3.47.5 (`artifacts/flutter-3.47.5`) in the isolated build checkout with the
committed lock, analyzer and full tests; the owner's working copy may carry a
local-SDK `pubspec.lock` change that must not be committed.

Native work follows the established loop: offline implementation and mutations,
generated artifact and size record, commit, owner Verify and completed download,
serial-guarded hardware evidence with restoration, browser acceptance. Evidence
is append-only under `Specification/AllenBradley/Evidence/`; keep failed and
interrupted runs. Update Part III, the AB README, the new-station guide and the
completion plan around the final behavior. Report completed features, exact
validation, what stays owner-gated, and do not push or deploy without the
owner's instruction.
