# Press75 HMI configuration-page capacity repair — 2026-10-05

Configuration stayed hidden because hydration failed, rather than because the
PLC denied visibility. The exact-serial read-only inspection reports admin
level 4 and a single page with 22 entries: four Model, five Station and
thirteen Line fields. The client imposed TwinCAT's 16-slot page limit, so it
rejected that complete AB page and never populated the cards.

The shared repository now bounds EntryCount by rows in the freshly read,
discovered response. Every reported row must have Scope, Item and ValueText,
and resolve to a distinct slot. Missing rows cannot reuse a preceding row
through a legacy zero-based alias. Partial payloads remain unavailable.
No limit is guessed from the station name or enlarged in the PLC.

A second live check found the Boolean RequireTwoHandStart field was dropped:
the typed read carried bit text `1`, while the editor validates IEC text.
ConfigManifestEntry now canonicalizes typed Boolean read `0`/`1` to
`FALSE`/`TRUE` once for both field hydration and synthesized browse values.
Numeric/text capabilities are unchanged; invalid Boolean `2` still fails
closed and write validation still refuses numeric Boolean candidates.

## Evidence and validation

- [Machine record](AB_PRESS75_HMI_CONFIG_PAGE_CAPACITY_2026-10-05.json), SHA-256 `DA824D56819BCEDABE7870A283FDE8FC414D6D4F37C9110A84A92922765377C4`.
- Before repair, the new regression suite reports 10 passes and 8 expected
  failures. After repair, 54 focused tests pass. Flat AB and container TC3 page
  names are covered at 16, 22 and 35 entries, including selected-model reads,
  overcounts, middle-slot holes and missing values.
- Full HMI: 508 tests pass, seven deployment-gated tests skip. Analyzer is clean.
  JavaScript release build passes; optional Wasm dry-run incompatibilities are
  not a Wasm support claim. Root consistency reports zero errors/warnings.
- Production gateway/repository: all 22 fields load in 1707 ms;
  Configuration capability and all three ConfigEditor cards are present.
  M-101 returns four recipe values; the active model remains unchanged.
  For ten seconds after hydration, the configuration remains populated and
  there are no stale/down transitions. Transient startup freshness is recorded
  separately; this is not a zero-transient cold-start claim.
- Corrected HTTPS assets match the staged release byte-for-byte at
  `https://press.localhost/`. Main JavaScript SHA-256:
  `7B9967606C248AB9019470E0BD5EA24CFF253512A0FA8DC5C25FC08D8F812FB2`. Previous web root is retained at
  `C:/work/press75_config_window_web_backup_01`.

The failed live-probe compilation, absent listener, 21-field observation and
startup-inclusive stability assertion are retained in the machine record.
The owner restarted the existing gateway after the listener disappeared; the
agent neither started nor restarted a write-enabled gateway. Native inspection
blocked Write; live repository requests were complete inert QUERY_CONFIG only.
Anonymous post-ack NONE cleanup was refused as required by Core section 14.
No login, configuration mutation, mode change or download was issued.

Press75 remains the loaded artifact, SHA-256
`82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5`; manifest 94E302F650BA1DB5 / 9757442.
PLC code, memory and gateway source are unchanged. Browser visual acceptance
and physical Line retention remain separate; the owner should hard-refresh
Chrome and check Configuration → Model/Station/Line data. The AB project guide
and TC3 transfer prompt carry the binding-capacity and typed-read lessons.
