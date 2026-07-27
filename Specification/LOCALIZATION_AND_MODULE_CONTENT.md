# Localization and module-content profile

This profile is normative for the Fraktal generic HMI. It extends the data-driven
contract without adding station-specific screens. The PLC publishes stable keys and
structured values; the HMI owns human language, formatting, documents, and view policy.

## 1. Design boundary

Operator-facing prose **shall not be authored in PLC logic**. Every displayed PLC field
(diagnostic, alarm, release condition, interlock/permissive, command label, sequence
step, decision prompt/option, safety-device description, hardware description, and I/O
description) carries an immutable localization key:

- `std.<area>.<meaning>` is owned by the Fraktal standard and is translated in the
  standard catalog.
- `project.<area>.<meaning>` is owned by the machine/project and is translated in the
  project catalog.

Keys are contract identifiers, not English fallback sentences. Renaming a key is a
schema change. The HMI **shall** display the unresolved key conspicuously when no
fallback exists; silently displaying an empty string is forbidden.

The following remain untranslated machine data: OPC UA browse names and paths, module
instance names, model/order/serial identifiers, user names, raw device payloads,
addresses, protocol commands, filenames, and engineering units. The HMI localizes the
labels around those values and formats dates, times, and numbers using the active locale.
Device reply data that helps diagnosis is carried as a structured value alongside a
message key; it is never concatenated into translated prose in the PLC.

The `ReasonCode` remains the stable numeric diagnostic identity. `Description` is now a
localization key rather than fallback prose. Structured context (`SourcePath`, current
step, awaited module/condition, timestamps, and measured values) remains separately
published so translations never need to parse a PLC-built sentence.

## 2. Catalog composition and fallback

For an active locale, resolution order is:

1. the matching scope's override CSV;
2. that scope's shipped/source-language default;
3. the shipped English/source default;
4. the unresolved key.

Standard and project keys stay in their owning files so upgrades cannot silently
shadow each other. Runtime UI source strings are also routed through the catalog; new
code should use semantic keys rather than generated compatibility keys.

Catalog CSV files use UTF-8 and this exact header:

```csv
schemaVersion,scope,locale,key,value
```

`schemaVersion` is currently `1`; `scope` is `standard` or `project`; `locale` is a BCP
47 language code enabled by the HMI. RFC 4180 quoting is used for commas, quotes, and
newlines. Import **shall** validate schema, scope, locale, key prefix, duplicate keys,
and row shape before replacing the selected override. A failed import leaves the prior
catalog intact. Export produces one standard file and one project file per language.

## 3. First-run and administration

Before connection configuration, first run presents the supported languages. The
device language is enabled and selected when supported; English is the fallback. The
user may enable several languages and choose the initial language. This choice is
stored locally with connection settings. Operators can switch among enabled languages
without reconnecting.

An authenticated administrator can later import/export the two CSV scopes for any
enabled language. Catalog changes apply immediately. Adding or removing the set of
enabled languages is an administrative deployment setting; it does not alter PLC data.

## 4. Module information and documents

Every discovered module may publish a `DisplayNameKey` and `DescriptionKey`. The module
detail renders an Information section from those keys. Missing descriptions use the
standard `std.module.noDescription` key.

Any module may have zero or more PDF documents (manuals, wiring diagrams, setup guides,
maintenance procedures). An Engineer or Administrator may upload a PDF; an
Administrator may delete it. Each record contains module path, stable document ID,
filename, localizable title key and source-language title, uploader, UTC timestamp, and
PDF bytes/content reference. Upload validates the `%PDF-` signature and deployment size
limit before committing. PDF binaries never enter PLC memory or recipe data.

The shipped store is device-local (atomic JSON generation plus last-known-good backup
on native platforms, IndexedDB on Web) and is suitable for commissioning/single-HMI
use. An older Web `localStorage` record is migrated into IndexedDB on first load. A
production multi-HMI deployment
**should** replace the `ContentStore` adapter with an authenticated shared document
service/object store, keyed by stable asset/module identity and providing integrity
hashes, backup, malware scanning, retention, and audit. Browser quota makes large local
PDF storage inherently deployment-dependent.

## 5. Per-module section access

The standard sections are Information, Operations, Diagnostics, Configuration,
Documentation, and History. Each module path has an HMI policy giving the minimum
`AccessLevel` for each section. Defaults are:

| Section | Minimum level |
|---|---|
| Information | Open (`NONE`) |
| Operations | Operator |
| Diagnostics | Operator |
| Configuration | Engineer |
| Documentation | Operator |
| History | Technician |

Only an Administrator edits these thresholds. Engineer and Administrator may upload
documents even when ordinary document viewing has a lower threshold. The policy is
local HMI presentation control and defense in depth; it is **not confidentiality**,
because published OPC UA data can be read by another client. If a section contains
sensitive data, the OPC UA server or gateway shall enforce read authorization. Every
write remains independently release-gated and rechecked by the PLC.

## 6. Tab layouts and guided content

Every module has Overview and Description tabs; category capabilities may add standard
Motion, Vision, Code Reader, or RFID tabs. An Administrator may change the minimum
view level of every tab and may add custom or Unit-guidance tabs. Custom controls use
the same catalog resolver as the built-in HMI: their source title, label, and text are
stored in the layout, and translated overrides remain in the standard/project catalog.
Identity, engineering units, paths, and raw device results remain untranslated per §1.
Custom/guidance tabs use a portable icon preset. The Overview layout may include an
embedded module image with aspect-ratio fit, alignment, and margin settings. Control
bindings are selected with autocomplete from compatible scalar OPC UA values owned by
the current module; charts may select up to eight numeric series.

Every bound tag retains OPC UA quality, runtime type, and timestamps. Bad/Uncertain
bindings remain in the layout but render unavailable, do not generate trend samples,
and cannot enable a configuration write. Controls use responsive quarter/third/half/
two-thirds/full width presets in a wrapping flow layout and may be drag-reordered in
edit mode.

Editing uses an HMI-local draft. Mutations and undo/redo never alter the published
operator layout. `Publish` validates the complete draft, stores the previous layout as
a revision with administrator/time/change-note metadata, then atomically makes the new
layout visible. The store retains at most 20 revisions per module. Restore is itself a
publish operation: it saves the layout being replaced before activating the selected
revision.

Guidance tabs bind to `CurrentStep.StepNo` and/or `CurrentStep.StepName`. `*` is reserved
for generic `WAIT_OPERATOR` guidance. The HMI displays guidance; the PLC sequence owns
the wait and the typed decision/condition that releases it. A local layout cannot make
an instruction into a safety acknowledgement or a PLC completion condition.

## 7. Portable customization profile

The HMI customization JSON is a complete portable backup of persistent
administrator-owned presentation state. It contains module documents, section and tab
access thresholds, tab/control definitions, tab icon choices, OPC UA binding lists,
embedded control/Overview images and layout, guidance triggers, and the
standard/project localization overrides, and bounded module-layout revision history.
Customization schema `4` adds revision history, action confirmation, and responsive
control widths while retaining schema 1â€“3 import compatibility. Import validates size, schema, duplicate IDs,
enum values, binding cardinality, chart bounds, document signatures, image payloads,
and catalog shape before merge. Imported IDs/keys update their matches; target-only tabs, documents,
policies, and localization overrides are preserved.

Project structure drift is not file corruption. Import reconciles an old module path
to the current live forest only when the match is deterministic: exact identity,
mapped-parent plus identical local name, or one unique longest dotted suffix. It never
guesses between duplicate local names. Unmatched/ambiguous profiles remain stored at
their source paths as deferred content instead of aborting the rest of the import or
being deleted. The completion report lists exact, remapped, and deferred paths so
commissioning can review every decision. A later import or the module's return can make
deferred content active.

Connection/bootstrap configuration is intentionally separate and is never exported:
endpoint, transport, `EverConnected`, selected Unit scope, credentials/session, enabled
languages, and active language remain local to the target HMI. This makes a profile
portable between Windows, Linux, Android, and Web deployments without accidentally
redirecting the target to the source PLC. Imported localized text applies immediately.

## 8. Plug-and-produce consequences

Adding a module type requires no HMI screen. It contributes stable standard/project
keys, optional description/document metadata, and the existing typed facets. Catalog
coverage is lintable: production PLC code may contain key literals, protocol data, and
identities, but no operator prose in displayed fields. A commissioning export supplies
the complete standard and project translation worklists before acceptance testing.
