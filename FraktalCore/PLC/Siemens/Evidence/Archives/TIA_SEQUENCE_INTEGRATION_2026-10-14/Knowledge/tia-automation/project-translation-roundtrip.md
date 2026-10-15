# Project translation & bulk-text round-trip (PLC + WinCC Unified) — verified 2026-10-09

Demonstrated end-to-end on PL8051 (S7-1500 `ST051-A620` + WinCC Unified `HMI_RT_2`
in device `ST051-A610`, 202 blocks / 85 types / 33 tag tables / 86 screens / 816
alarms / 7,320 HMI tags): a **full zh-CN → en-US project translation** delivered as
a valid `.zap20` with PLC compile 0 errors and 0 residual CJK strings in the
displayed language. Evidence: `..\project-pl8051` facts used as glossary context;
pipeline + logs in `C:\Projects\SiemensAgent\pl8051-translate\`; deliverable +
`TRANSLATION_REPORT.md` in `C:\Users\Siemens\Downloads\output\`.

## Capability matrix (all **[measured]** unless marked)

| Surface | Mechanism that works | Limit |
|---|---|---|
| PLC blocks / types / tag tables content | `Export(FileInfo, ExportOptions.WithDefaults)` → patch XML text → `composition.Import(fi, ImportOptions.Override)` | Matches by name; blocks with Chinese names would need delete+import (none here) |
| **WinCC Unified screens / alarms / text lists** | NO Openness XML export exists (`HmiScreen` has no `Export`; composition has none). Use `ProjectBase.ExportProjectTexts` xlsx round-trip | xlsx only; identity-based (see semantics) |
| Unified tags / scripts | Per-table WinCC-ML YAML: `tagTable.Tags.Export/Import(DirectoryInfo)`; `HmiScriptModule.Export(DirectoryInfo)` | — |
| Free texts of every kind (comments, titles, alarms, texts lists, screen item texts, system CPU messages) | `ProjectBase.ExportProjectTexts(file, CultureInfo src, CultureInfo dst)` / `ImportProjectTexts(file, bool updateSourceLanguage)` | see semantics below |
| Identifier renames (tags, UDT/DB members, GRAPH step names, alarms, screens, tags, hardware items) | `SetAttribute("Name", …)` via reflection; references follow (system constants regenerated after hardware-item renames) | refuses on: block/type/tag-table **user folders**, graphics library entries, watch tables, script modules, system tags — `'set_Name' is not supported` **[measured]** |
| Project languages | `ProjectBase.LanguageSettings` → `Languages` (all cultures), `ReferenceLanguage`, `EditingLanguage` (settable objects), `ActiveLanguages` (association) | setting Reference/Editing via `SetAttribute("ReferenceLanguage", lang)` works **[measured]** |
| Compile check | PLC: `plcSoftware.GetService<ICompilable>().Compile()` | WinCC Unified `HmiSoftware` has **no** `ICompilable`/`CompileProvider` service **[measured]** |
| Introspection | reflection walk: properties typed `*Composition` / `*Folder` are collections, `*Group` are single child objects; `GetAttributeInfos`/`GetAttributes`; software via `DeviceItem.GetService<SoftwareContainer>().Software` | name the walk filter right or the PLC tree stays invisible (`PlcSoftware.BlockGroup` etc. are `*Group` single objects) |

## Project-texts import/export semantics (**[measured]** — the part that costs days if guessed)

1. The export workbook has sheets *User Texts* + *System Texts*; columns `Category, ViewPath, Internal ID, Substitutions, <srcLang>*, <dstLang>`, then `ref="0..15"` arg columns.
2. **The source-language column is an identification KEY, not an updatable field.** `updateSourceLanguage:true` did not rewrite it (V20). Translations land ONLY in the target-language column. Consequently: after import, the project still *displays* whatever the **reference language** holds — to make translations visible you must import into the culture that is (or will be) the reference, or switch `LanguageSettings.ReferenceLanguage` to the target culture.
3. Import is keyed by `Internal ID`. Any object **recreated** between export and import (e.g. by an XML `Override` reimport of its block) invalidates its rows → those rows fail with a row-level warning (log written next to the project, `Logs\<file>.xml`). Order the pipeline: **XML imports first, then texts import, then (optionally) re-export + second texts pass** to catch the recreated rows by their new IDs.
4. `ExportProjectTexts` refuses to overwrite an existing xlsx — delete the target first.
5. Row counts: PL8051 exported 13,418 user rows (12,610 CJK, 3,807 unique strings) + 162 system rows. Pass 1 imported ~5.4 k (target column only); round 2 on the fresh export covered the rest. Verified end state by re-export + CJK scan of the en-US column: **0 rows**.
6. System-texts rows import through the same call (sheet 2).

## Pipeline that worked (per TIA session, one command each; ~1–3 min + flaky starts)

```
copy project → open headless → probe/survey (introspection) → export XML
→ extract CJK corpus (unique strings + context) → translate (glossary + rules;
   fan-out subagents verified per index range) → patch XML (delimited
   whole-value replacement, then per-line, never substring) → fill xlsx (surgical
   zip edit: repoint cells to new shared strings) → import XML (Override)
→ import texts xlsx → identifier renames (attr writes; iterate passes until
   fixpoint for nested items) → patch Script/ScreenName/ContainedType reference
   strings → set Reference/Editing language → Save() → re-export + CJK scan
   → compile → zip folder as .zap20 (project folder at zip root)
```

- Whole-string (delimited `>v<` / `"v"`) replacement is safe where substring
  replace is not (`维护门1` inside `维护门1插销气缸`).
- Keep `@…@`/`%s`/`%v`/`%t` placeholders, device IDs, and banner punctuation
  byte-identical; bilingual `English//中文` strings collapse to the English half.
- Verify EVERYTHING by re-export and scanning, not by trusting import return
  codes: `ImportProjectTexts` returns *Warning* state for row misses and rc 0.
- User-visible text conventions found in PL8051 worth copying for similar lines:
  alarm formulas (`X去工作位超时报警` → `X to work position timeout alarm`),
  axis name table A710–A717, `是否X` → `X?` / `Check whether X`.

## Gotchas hit (all **[measured]**)

- **Close without `Project.Save()` discards everything.** Each mutating Openness
  session must save; a full rename pass evaporated once before this was added.
- `EngineeringSecurityException "The operation has timed out"` at portal start is
  **transient** on this VM (lingering previous portal): retry 2–3× with 90–120 s
  sleeps; kill zombie `Siemens.Automation.Portal` processes between runs. Portal
  can also die mid-session (`EngineeringObjectDisposedException`) — project
  unaffected until Save.
- Watch tables on inconsistent blocks: export fails ("table is inconsistent");
  import fails on `DisplayFormat` ("assigned block is inconsistent"). Pre-existing
  project breakage, not a translation artifact.
- System blocks (`G7_*`, `R_TRIG`, `MOVE_BLK_VARIANT`) export but **cannot be
  reimported** — exclude them from import manifests (their import failure is a no-op).
- Incremental compile hides broken blocks: a stale block referencing deleted DB
  members (`ChangeOver_FC` → `StationData_DB`.中文 members) still "compiles"
  0-error because it is never rebuilt; an Override reimport marks it dirty and
  exposes the breakage. Check `IsConsistent`/member existence before touching
  such bodies; leave them byte-identical if pre-broken.
- Graph step/transition display names used by HMI live in `SYSTEM_StepNames*`
  text lists — they travel with the texts route, not with block XML.
- Renaming a parent hardware item invalidates child specs that name it
  (`…PROFINET 接口_1|DeviceItems:端口_1`): re-dump names and re-apply renames
  until the CJK-name count converges.

## Tooling

`C:\Projects\SiemensAgent\pl8051-translate\TiaTranslate\` — net48 reflection-driven
Openness driver built for this (csproj pattern as `Fraktal.Tia.Cli`; loads
`Siemens.Engineering.dll` from the installed Portal; **new headless portal needs
no firewall whitelist**, only the `Siemens TIA Openness` group). Commands:
`probe, survey, export, import, delete, set-attr, attrs, services, langs, set-lang,
dump-names, apply-jsonl (rename/setattr/script ops), apply-scripts, texts-export,
texts-import, compile, save`; most accept `--save` (persists after rc 5 = partial
failures). Pipeline scripts + translation maps (`map_texts.json` 3,807 entries,
`map_names.json` 295, `map_xmlonly.json` ~900) live beside it; `TRANSLATION_RULES.md`
holds the bilingual glossary and formatting rules used for the corpus.
