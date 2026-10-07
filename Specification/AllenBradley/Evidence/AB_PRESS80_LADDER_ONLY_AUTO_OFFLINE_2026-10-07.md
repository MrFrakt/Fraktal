# AB press80 — AUTO in ladder only (offline)

Recorded 2026-10-07 after
[press79 ran out of controller memory while linking](AB_PRESS79_NATIVE_LINK_MEMORY_FAILURE_2026-10-07.md).
The owner's instruction: "remove unused code and sfc, leave only LD sequences and
permissives to save memory, you have successfully generated SFC and ST and your
skill to do it is proven, so that's good enough for now." Offline only: no
controller write, download or mode change was performed.

## What changed

- The press declares AUTO with one rendition, `decl.LD`. HOME and CHANGEOVER stay
  single-rendition ST inside the Unit AOI (one copy each). The permissives - start
  permits, module permits and the release report - are unchanged; they were never
  rendered per language. Live documents (press79) are unchanged.
- The generator now hosts any chain that is not a lone ST rendition in program
  routines (`Chain.program_hosted`) and emits the rendition selector only for a
  chain carried in more than one language. ST must come first only among several
  renditions; the rendition gate compares a single rendition with the declaration.
- Removed from the emitted program because only ST or SFC used them: routines
  `FRK_PressAutoSt`, `FRK_PressAutoSfc`, `FRK_PressAutoSfcRun` and
  `FRK_Press_SequenceMarkStep`; the controller tag `FRK_Press_RenditionSelect`; 57
  program tags (18 SFC steps, 18 actions, 21 transitions). The SFC execution
  settings are no longer forced; the seed's values stand. Every remaining routine
  is reachable from `FRK_PressMain`.
- The generator keeps all three renditions. The rendition, cycle and profiler tests
  now prove them on a press variant that carries AUTO in ST, SFC and LD; new tests
  pin what the shipped press emits.

## Generated artifact

`C:/work/press80.L5X`, SHA-256
`F293A34D65B2C508049FDD3E0D9235A7CB70C15CDA17950CEE064B7F359976B1`, generated twice
byte-identically from `seed_v33.L5X` and the same fresh capture as press79
(`press79_source_config_01.json`, `5D044C0A…C65D`), because no live document
exists before the first live-document download. Manifest
`E5F914E06055CD3B / 15071508`, equal to press79's and to the tags press79 left on
the controller: renditions are not part of the published contract.

| Generated measure | press80 | vs press78 | vs press79 |
| --- | ---: | ---: | ---: |
| ST source bytes | 295085 | −37343 | −40475 |
| ST statement terminators | 3502 | −558 | −586 |
| ST lines | 5596 | −864 | −918 |
| Declared data bytes (controller tags) | 110264 | −4 | −4 |
| RLL rungs | 20 | 0 | 0 |

The declared-data figure counts controller tags only; the 57 removed SFC program
tags are additional. Against press75, the last measured baseline, press80 has 589
fewer statements but 34,241 more ST source bytes and 2,752 more declared bytes
(calendar V3, live documents). These are generated trends, not compiled memory:
only the owner's Capacity Estimate measures fit.

## Validation

- Full AB suite: **1670 tests pass** (`press80_ab_tests_02.log`).
- 19 live-document mutants still each killed (`press80_mutations_01.json`).
- Rendition gate on press80: the ladder equals the declared graph.
- `check_ab_contracts.py` clean; `check_consistency.py --strict` 0/0 and its 33
  tests pass; `check_ab_spec.py` shows the same 3 pre-existing errors as `3d77e7a`.

## Owner gates

1. Capacity Estimate of press80 (both areas), then Verify.
2. Download press80. It is seeded, so it is not restored; start the write-enabled
   gateway from this commit afterwards and check `/healthz` `liveDocuments.state =
   kept`, then the press scans and the HMI reads it.
3. Record press80's online memory as the new baseline. Then the restore acceptance
   (an unseeded later download) and the power-cycle retention plan, as in the
   [press79 record](AB_PRESS79_LIVE_DOCUMENTS_OFFLINE_2026-10-07.md).

If press80 still does not fit, measure before cutting further. Remaining
candidates the generator can trim without touching the contract were not
identified here; the manifest's empty Nameplates table keeps an eight-row reserve,
but changing manifest capacities is a contract change.

Machine record: [AB_PRESS80_LADDER_ONLY_AUTO_OFFLINE_2026-10-07.json](AB_PRESS80_LADDER_ONLY_AUTO_OFFLINE_2026-10-07.json).
