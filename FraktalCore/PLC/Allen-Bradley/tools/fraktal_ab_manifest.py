#!/usr/bin/env python3
"""Emit the controller-resident ``FRK_Manifest`` from the application declaration.

Core §3.10 and AB §3.10 make the manifest the runtime source of truth: a
generated L5X on disk is an engineering artifact, and a client that cannot read
the manifest does not proceed on assumption. Nothing published it until now,
which is why the gateway had nothing to discover.

**It is generated, never hand-edited.** The manifest necessarily restates what
the AOIs and the contract UDTs already encode - a bounded, deliberate exception
to Core §1.1 O9, admissible *only* because one declaration produces all of them.
That is exactly why it is emitted here from the same `Application` the AOIs come
from, and why a mismatch is a generator bug rather than a maintenance task.

**It describes the declared graph once, rendition-agnostic.** A chain carried in
several languages has one graph; each rendition is an emission of it. What the
manifest publishes is the *chart surface* that graph is observed through - the
step cursor, the active step, the per-step visited and duration marks, the stall
reason (Core §3.13) - and it says nothing about which language rendered them,
and nothing that would let a client select one. This is the same way the TC3 HMI
sees one chart whichever rendition ran: it renders from the marks, not from a
static step list. The rendition selector and a rendition's implementation tags
are excluded by construction, through ``publishable_tags``.

Note what this does *not* do: the declared step and transition lists are not a
manifest table. The frozen v1 schema has eight tables and none of them is a
graph, so a client reconstructs the chart from the marks at runtime rather than
reading the topology up front. That is a limitation of the frozen schema, not an
omission here, and it is recorded rather than worked around.

The logical schema is the frozen v1 contract in ``AB_FROZEN_CONTRACTS_V1.json``
and the table shape S7 measured: eight tables behind ``FRK_MAX_*`` capacities,
with counts and a truncation flag in the header so a reader never has to guess
how much of a table is real.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import fraktal_ab_declaration as decl


SCHEMA = "fraktal.ab.manifest"
# Major 2: Fields.PathKey became RELATIVE to its ModuleId's canonical path.
# A reader built for major 1 would compose wrong paths, so it must refuse this
# manifest rather than misread it - which is what bumping the major buys.
# Major 3 appends CaptureSourceKey to the versioned WriteCapabilities row.
# A major-2 reader must refuse before interpreting the enlarged rows.
# Major 4 appends ClassKey and immutable per-value minima to WriteCapabilities.
MANIFEST_SCHEMA_MAJOR = 4
MANIFEST_SCHEMA_MINOR = 0
MANIFEST_MAGIC = 0x4652414B  # 'FRAK'

CORE_VERSION = 1
BINDING_VERSION = 2
FRAMEWORK_VERSION = 1

# The frozen contract sizes a string type "to the declared maximum", and that is
# meant literally. A fixed 32 truncated 27 of this application's 206 portable
# keys, and two of them truncated to the *same* text - a manifest that publishes
# two different paths under one name is worse than one that admits it is short.
# So the key string is sized to the longest key the declaration actually
# produces, rounded up for stability, and the resulting length is published in
# the header so a reader never has to compile the number in.
KEY_STRING_MINIMUM = 32
KEY_STRING_GRANULARITY = 8

# S7 ceilings remain 768; allocate what this declaration needs plus eight rows,
# rounded to eight-row blocks. Counts/capacities in the
# header remain authoritative. Unused discovery reserve is controller memory.
SURFACE_ROW_CEILING = 768
SURFACE_ROW_BLOCK = 8
SURFACE_ROW_HEADROOM = 8


def surface_capacity(count: int) -> int:
    rounded = -(-(count + SURFACE_ROW_HEADROOM) // SURFACE_ROW_BLOCK) * SURFACE_ROW_BLOCK
    return min(SURFACE_ROW_CEILING, rounded)


def bounded_capacity(count: int, ceiling: int, block: int = 4) -> int:
    """Static discovery needs one spare row, without allocating its ceiling."""
    return min(ceiling, -(-(count + 1) // block) * block)

# Logical value types, from the frozen contract's `logicalTypes`.
LOGICAL_INT32 = 3
LOGICAL_DURATION_MS = 9

# Core 3.10.2 client vocabulary, mirrored here because the manifest carries it.
# CfgKind: parCfg 0, stationCfg 1, lineCfg 2. CfgType: number 0, text 1,
# boolean 2, time 3 - where "time" is the oracle's DURATION, renamed because
# TIME is reserved in ST, and it travels as a millisecond count.
CFG_KIND_PAR = 0
CFG_KIND_STATION = 1
CFG_KIND_LINE = 2
CFG_TYPE_NUMBER = 0
CFG_TYPE_BOOLEAN = 2
CFG_TYPE_DURATION = 3
LOGICAL_ENUM = 11

# Access classes. The initial claim is read-only (AB §11.2.1): a client may read
# everything published and write only what is declared an operation.
ACCESS_READ = 0
ACCESS_WRITE = 1

# Read tiers, from the S9 reference-station declaration.
TIER_LIVE = 0
TIER_SLOW = 1
TIER_ON_DEMAND = 2

# Quality/timestamp source. PTP is disabled and unsynchronized on this bench, so
# every value carries the gateway's read time with TimeSynchronized false.
QUALITY_GATEWAY_READ_TIME = 1

# Operation kinds.
OP_COMMAND = 1
OP_MODE = 2
OP_DECISION = 3

TIER_ROOT = 0
TIER_MODULE = 1

# The root's command mailbox. One root, one mailbox, so the id is 1 -
# but it is published rather than assumed, because zero is how the
# manifest says a station cannot be commanded at all.
MAILBOX_ID = 1


@dataclass(frozen=True)
class Table:
    """One manifest table: a capacity symbol and the row type behind it."""

    name: str
    symbol: str
    row_type: str
    members: tuple[tuple[str, str], ...]
    capacity: int


KEY32 = "KEY32"


def reason_key(app, name: str) -> str:
    """A reason's text key: what happened. Its rationalization adds `.action`
    and `.consequence` to the same stem, so the three can never name different
    reasons. The alarm log's Description is this key. A registered reason's is
    TC3's `std.reason.<code>`, which the HMI catalogue already carries."""
    import fraktal_ab_reasons as reasons

    return reasons.of(app, name).stem


def field_path(module_path: str, relative: str) -> str:
    """The published path of a field: its module's path, then its own.

    Fields.PathKey names a field RELATIVE to the canonical path of the module
    it belongs to (Fields.ModuleId). It used to be absolute, which interned the
    same 32 context member names once per module instance - three identical
    cylinders cost 96 Localization rows for 32 names, and four more modules
    would have taken the table past what S7 measured (audit §5, Q2). Every
    AB module shares one context shape, so relative keys make every module
    share the same 32.

    This is the only place the two halves are joined, so a reader and the
    tests that prove the paths did not move use the same rule. For every path
    the HMI reads, the result is byte-identical to the old absolute key.
    """
    return f"{module_path}.{relative}" if relative else module_path


def field_paths(content: dict) -> dict[str, dict]:
    """Every Fields row by its published path - the reader's half of the rule.

    Resolves each row's ModuleId to that module's canonical path through the
    Modules table, then joins it with the row's relative key. Given a manifest
    as a reader receives it, so a test that uses this proves what a reader
    would actually compute, not what the emitter happened to intern.
    """
    keys = {row["NumericKey"]: row["PortableKey"]
            for row in content["Localization"]}
    module_path = {row["ModuleId"]: keys[row["CanonicalPathKey"]]
                   for row in content["Modules"]}
    return {field_path(module_path[row["ModuleId"]], keys[row["PathKey"]]): row
            for row in content["Fields"]}


def tables(app: decl.Application) -> tuple[Table, ...]:
    surface = content(app)
    p = app.name
    modules = bounded_capacity(len(surface['Modules']), 16)
    return (
        Table("Roots", "FRK_MAX_ROOTS", f"FRK_T_{p}MfRoot",
              (("RootId", "DINT"), ("ModuleIndex", "DINT"),
               ("RepositoryScope", "DINT"), ("MailboxId", "DINT"),
               ("HostEventId", "DINT")), bounded_capacity(len(surface['Roots']), 4, 1)),
        Table("Modules", "FRK_MAX_MODULES", f"FRK_T_{p}MfModule",
              (("ModuleId", "DINT"), ("ParentModuleId", "DINT"), ("RootId", "DINT"),
               ("RegistryIndex", "DINT"), ("Tier", "DINT"), ("TypeId", "DINT"),
               ("LocalNameKey", "DINT"), ("CanonicalPathKey", "DINT"),
               ("Capabilities", "DINT"), ("ContractAddress", "DINT")), modules),
        Table("Nameplates", "FRK_MAX_MODULES", f"FRK_T_{p}MfNameplate",
              (("ModuleId", "DINT"), ("ManufacturerKey", "DINT"),
               ("ProductKey", "DINT"), ("ModelKey", "DINT"), ("SerialKey", "DINT"),
               ("HardwareRevision", "DINT"), ("SoftwareRevision", "DINT"),
               ("AssetKey", "DINT"), ("LocationKey", "DINT")), modules),
        Table("Fields", "FRK_MAX_FIELDS", f"FRK_T_{p}MfField",
              (("ModuleId", "DINT"), ("PathKey", "DINT"), ("LogicalType", "DINT"),
               ("Dimensions", "DINT"), ("ReadTier", "DINT"), ("AccessClass", "DINT"),
               ("QualitySource", "DINT"),
               # Keep the Phase 6 ceiling, but size reserve to this declaration.
               ("WriteCapabilityIndex", "DINT")), surface_capacity(len(surface['Fields']))),
        Table("Operations", "FRK_MAX_OPERATIONS", f"FRK_T_{p}MfOperation",
              (("OperationId", "DINT"), ("TargetScope", "DINT"),
               ("ParameterType", "DINT"), ("ResultType", "DINT"),
               ("GatedAction", "DINT"), ("Minimum", "DINT"), ("Maximum", "DINT"),
               ("OperationKind", "DINT")), bounded_capacity(len(surface['Operations']), 32)),
        Table("Localization", "FRK_MAX_LOCALIZATION_KEYS", f"FRK_T_{p}MfLocale",
              # Raised from 224 when the mailbox's refusal keys took the count to
              # 225 and the truncation flag caught it, then from 256 when
              # editable configuration (§3.10.2) added five label keys and three
              # refusal keys and took it to 257 — the truncation flag catching
              # it a second time.
              #
              # Then LOWERED to 320, because the pressure that drove the raises
              # is gone: field keys became relative to their module (audit Q2),
              # so every module shares one set of 32 member names instead of
              # interning its own. 268 rows became 205. Sized to Phases 1-3:
              # ~12 for the four missing modules, ~20 for the alarm log's
              # reasons and sources, so ~240 against 320. The space released is
              # what lets Fields grow inside the manifest's measured total.
              #
              # Raised to 352 for the release reports (Phase 4b), which took it
              # past 320. 32 more rows at the current 48-byte keys are 1,792
              # bytes; the manifest stays inside S7's measured 43,728.
              #
              # Raised to 448 ahead of Phases 5-6 (332 used after run styles;
              # about 80-90 keys to come), inside MANIFEST_BUDGET_BYTES.
              #
              # Raised to 512 for §8.12 and Phase 6: the S3 probe took it to
              # 434, and every registered reason brings its action and
              # consequence keys. 64 more 64-byte rows are 4,096 bytes.
              #
              # Unused rows consume controller memory even between discoveries.
              (("NumericKey", "DINT"), ("PortableKey", KEY32)), surface_capacity(len(surface['Localization']))),
        Table("Rationalization", "FRK_MAX_REASONS", f"FRK_T_{p}MfReason",
              (("ReasonCode", "DINT"), ("Priority", "DINT"), ("Category", "DINT"),
               ("ActionKey", "DINT"), ("ConsequenceKey", "DINT"),
               ("Shelvable", "DINT")), bounded_capacity(len(surface['Rationalization']), 32)),
        Table("OptionalProfiles", "FRK_MAX_OPTIONAL_PROFILES",
              f"FRK_T_{p}MfProfile",
              (("ProfileId", "DINT"), ("ProfileVersion", "DINT"),
               ("CapabilityMask", "DINT"), ("ProjectionMask", "DINT")), bounded_capacity(len(surface['OptionalProfiles']), 8, 2)),
        # Core 3.10.2 - what a client may CHANGE, and within what bounds.
        #
        # It lives on the controller rather than in the gateway's copy of the
        # declaration because the binding's claim is that a client discovers
        # the station FROM THE CONTROLLER. A gateway that answered from its own
        # copy would be right only for as long as the two agreed, and the one
        # case that matters is the one where they do not.
        #
        # Every string is a Localization index, not a string: v33 cannot assign
        # a string literal in ST, so anything an operator reads is interned at
        # emission and referenced by number - the same way every other table
        # here names things.
        Table("WriteCapabilities", "FRK_MAX_WRITE_CAPABILITIES",
              f"FRK_T_{p}MfWriteCapV4",
              (("CapabilityIndex", "DINT"), ("PathKey", "DINT"),
               ("WriteKeyKey", "DINT"), ("LabelKey", "DINT"),
               ("ConfigKind", "DINT"), ("ValueType", "DINT"),
               ("Minimum", "DINT"), ("Maximum", "DINT"),
               ("RequiresReady", "DINT"), ("UnitCode", "DINT"),
               ("CaptureSourceKey", "DINT"), ("ClassKey", "DINT"),
               ("MinReadLevel", "DINT"), ("MinWriteLevel", "DINT")), bounded_capacity(len(surface['WriteCapabilities']), 64)),
    )


# --- the localization catalogue ---------------------------------------------

class Keys:
    """Numeric key to portable string key, assigned in first-encounter order.

    Numeric keys are what the manifest tables carry; the portable key is what an
    HMI resolves against its own string catalogue. Assigning them here, from the
    declaration, is what keeps the two in step.

    **A numeric key is meaningful only within one manifest revision.** Adding a
    module renumbers everything discovered after it, so a client resolves names
    through the Localization table it read *with* the tables it is reading, and
    never caches a numeric key across a `ConfigRevision` change. The portable
    string is the stable identity; the number is a per-revision index into it.
    """

    def __init__(self) -> None:
        self._by_text: dict[str, int] = {}
        self._order: list[str] = []

    def key(self, portable: str) -> int:
        if portable not in self._by_text:
            self._by_text[portable] = len(self._order) + 1
            self._order.append(portable)
        return self._by_text[portable]

    @property
    def rows(self) -> list[tuple[int, str]]:
        return [(self._by_text[text], text) for text in self._order]


def _module_ids(app: decl.Application) -> dict[str, int]:
    """The unit is module 1; declared module types follow in declaration order."""
    ids = {app.name: 1}
    for index, module in enumerate(app.modules):
        ids[module.name] = index + 2
    return ids


def content(app: decl.Application) -> dict[str, object]:
    """Every manifest row, derived from the declaration.

    Rendition-agnostic by construction: the field list comes from
    ``publishable_tags``, which excludes the rendition selector and any tag that
    exists only because of how one rendition is implemented.
    """
    import fraktal_ab_generate as gen

    keys = Keys()
    ids = _module_ids(app)
    publishable = set(gen.publishable_tags(app))

    roots = [{
        "RootId": 1,
        "ModuleIndex": 0,
        "RepositoryScope": 1,
        # The root now has a Core 3.10/14 command mailbox, so this is its id
        # rather than the zero that meant "not published". A client reads a
        # non-zero MailboxId to learn the station can be commanded at all.
        "MailboxId": MAILBOX_ID,
        # No host-event ring exists yet; zero still says "not published" there,
        # and never "id 0".
        "HostEventId": 0,
    }]

    modules = [{
        "ModuleId": ids[app.name], "ParentModuleId": 0, "RootId": 1,
        "RegistryIndex": 0, "Tier": TIER_ROOT, "TypeId": 1,
        "LocalNameKey": keys.key(f"project.module.{app.name.lower()}"),
        "CanonicalPathKey": keys.key(f"{app.name}"),
        "Capabilities": 0, "ContractAddress": 0,
    }]
    for index, module in enumerate(app.modules):
        modules.append({
            "ModuleId": ids[module.name], "ParentModuleId": ids[app.name],
            "RootId": 1, "RegistryIndex": index + 1, "Tier": TIER_MODULE,
            "TypeId": index + 2,
            "LocalNameKey": keys.key(f"project.module.{module.name.lower()}"),
            "CanonicalPathKey": keys.key(f"{app.name}.{module.name}"),
            "Capabilities": len(module.commands),
            "ContractAddress": index + 1,
        })

    # Nameplates are declared per module and this application declares none, so
    # the table is empty rather than filled with zero rows pretending to be data.
    nameplates: list[dict[str, int]] = []

    fields: list[dict[str, int]] = []

    # Core 3.10.2: the wire ordinal of each editable value, so a field can
    # point at its own write capability. Built here rather than looked up per
    # field so the numbering has exactly one source - the same ordinal the
    # controller dispatches on.
    write_index = {
        (record.name, member.name): ordinal
        for ordinal, record, member in gen.editable_values(app)
    }

    def add_fields(module_id: int, prefix: str, members, tier: int,
                   access: int = ACCESS_READ, record_name: str = "") -> None:
        for member in members:
            if member.editable:
                # Interned so the label survives translation. A field an
                # operator can EDIT and cannot READ THE NAME OF is the one
                # case where a raw key on screen actually costs something.
                keys.key(member.label_key)
                keys.key(member.write_key)
            fields.append({
                "ModuleId": module_id,
                "PathKey": keys.key(
                    f"{prefix}.{member.name}" if prefix else member.name),
                "LogicalType": (LOGICAL_DURATION_MS
                                if member.kind == "duration_ms" else LOGICAL_INT32),
                "Dimensions": member.dimension,
                "ReadTier": tier,
                "AccessClass": access,
                "QualitySource": QUALITY_GATEWAY_READ_TIME,
                "WriteCapabilityIndex": write_index.get(
                    (record_name, member.name), 0),
            })

    unit_id = ids[app.name]
    # One authoritative root field list also validates capture sources.
    live = {"Unit", "Chart", "AlarmActive", "StateFlags"}
    record_names = {r.name for r in app.records}
    for prefix, members in gen.root_field_records(app):
        add_fields(unit_id, prefix, members, TIER_LIVE if prefix in live else TIER_SLOW,
                   record_name=prefix if prefix in record_names else "")
    for module in app.modules:
        # No prefix: the member IS the field, under this module's own path.
        # This is the line the whole change exists for - every module now
        # interns the same member names, however many there are.
        add_fields(ids[module.name], "", gen.module_members(module), TIER_LIVE)

    # Simulated plant inputs are published as writable fields rather than as
    # operations: they stand in for signals a real machine would take from I/O,
    # not for something a client asks the machine to do.
    #
    # A tag the mailbox routes into is excluded even when it is declared a
    # simulated input, because it is no longer externally writable: the jog a
    # MANUAL_COMMAND drives is reached through the mailbox, which validates and
    # acknowledges it. Publishing it as writable would advertise a surface the
    # controller now refuses.
    commanded = set(gen.command_inputs(app))
    for tag in app.sim_inputs:
        if tag not in publishable or tag in commanded:
            continue
        fields.append({
            "ModuleId": unit_id, "PathKey": keys.key(tag),
            "LogicalType": LOGICAL_INT32, "Dimensions": 0,
            "ReadTier": TIER_LIVE, "AccessClass": ACCESS_WRITE,
            "QualitySource": QUALITY_GATEWAY_READ_TIME,
            "WriteCapabilityIndex": 0,
        })

    # The mailbox members a client writes to command the station. They are
    # published as writable fields rather than left to be guessed: a client that
    # cannot discover where to put a request has no mailbox, only a tag someone
    # told it about out of band.
    import fraktal_ab_mailbox as mailbox

    for name, kind, _, _ in mailbox.REQUEST_MEMBERS:
        fields.append({
            "ModuleId": unit_id,
            "PathKey": keys.key(f"HmiRequest.{name}"),
            "LogicalType": LOGICAL_INT32,
            "Dimensions": 0,
            "ReadTier": TIER_ON_DEMAND,
            "AccessClass": ACCESS_WRITE,
            "QualitySource": QUALITY_GATEWAY_READ_TIME,
            "WriteCapabilityIndex": 0,
        })
    # TC3's HmiResponse.Report: the answer to a release query, and to START.
    for member in gen.release_report_members():
        fields.append({
            "ModuleId": unit_id,
            "PathKey": keys.key(f"HmiResponse.Report.{member.name}"),
            "LogicalType": LOGICAL_INT32,
            "Dimensions": member.dimension,
            "ReadTier": TIER_LIVE,
            "AccessClass": ACCESS_READ,
            "QualitySource": QUALITY_GATEWAY_READ_TIME,
            "WriteCapabilityIndex": 0,
        })
    for name, kind, _, _ in mailbox.RESPONSE_MEMBERS:
        fields.append({
            "ModuleId": unit_id,
            "PathKey": keys.key(f"HmiResponse.{name}"),
            "LogicalType": LOGICAL_INT32,
            "Dimensions": 0,
            # The answer is polled until AckSequence matches, so it is live.
            "ReadTier": TIER_LIVE,
            "AccessClass": ACCESS_READ,
            "QualitySource": QUALITY_GATEWAY_READ_TIME,
            "WriteCapabilityIndex": 0,
        })

    operations: list[dict[str, int]] = []

    def add_operation(portable: str, kind: int, minimum: int, maximum: int) -> None:
        operations.append({
            "OperationId": keys.key(portable), "TargetScope": unit_id,
            "ParameterType": LOGICAL_INT32, "ResultType": LOGICAL_INT32,
            "GatedAction": 0, "Minimum": minimum, "Maximum": maximum,
            "OperationKind": kind,
        })

    add_operation(f"{app.name}.RunRequest", OP_COMMAND, 0, 1)
    add_operation(f"{app.name}.AbortRequest", OP_COMMAND, 0, 1)
    add_operation(f"{app.name}.ResetRequest", OP_COMMAND, 0, 1)
    add_operation(f"{app.name}.ModeRequest", OP_MODE, 0,
                  max(decl.declared_modes(app)))
    decisions = {s.decision_id for c in app.chains for s in c.steps
                 if s.action == decl.DECISION}
    for decision in sorted(decisions):
        add_operation(f"{app.name}.Decision{decision}", OP_DECISION, 0, 2)

    # Every declared chain, step and named condition - once, whichever language
    # rendered it. Steps are localization entries so an HMI can name the cursor.
    for chain in app.chains:
        keys.key(f"project.chain.{chain.name.lower()}")
        for step in chain.steps:
            keys.key(f"project.step.{step.name}")

    import fraktal_ab_reasons as reasons

    rationalization = []
    for name, code in sorted(app.reasons.items(), key=lambda item: item[1]):
        # One rule with the alarm log's severity (fraktal_ab_reasons), so an
        # alarm and its rationalization row cannot disagree - and a registered
        # reason carries the registry's record, not one invented here.
        rationale = reasons.of(app, name)
        rationalization.append({
            "ReasonCode": code,
            "Priority": rationale.priority,
            "Category": rationale.category,
            "ActionKey": keys.key(f"{rationale.stem}.action"),
            "ConsequenceKey": keys.key(f"{rationale.stem}.consequence"),
            "Shelvable": 1 if rationale.shelvable else 0,
        })

    # The command mailbox answers a refusal with a numeric key rather than a
    # string, because Logix v33 ST cannot assign a string literal to a
    # StringFamily member. Registering those keys here is what makes the answer
    # resolvable: the controller publishes a number and this catalogue is where
    # a client turns it back into a name. Registered last and in sorted order so
    # the numbering is a function of the declaration, not of import order.
    import fraktal_ab_mailbox as mailbox

    for portable in mailbox.localization_keys():
        keys.key(portable)
    if app.line is not None:
        import fraktal_ab_line as line
        for portable in (line.INVALID_KEY, line.AUDIT_KEY, 'std.profile.line', app.line.line_id, app.line.owner_id):
            keys.key(portable)
    if app.access_users is not None:
        import fraktal_ab_access as access
        for portable in access.KEYS:
            keys.key(portable)
        for item in app.data_classes:
            keys.key(item.class_id)
            keys.key(item.label_key)

    # The release reports' own texts (Core §7.8).
    for portable in gen.release_keys(app):
        keys.key(portable)

    # The interlock a held module names (TC3's SetAreaSafe and
    # SetDirectionalPermits keys). The routine publishes the number of the
    # missing one, so the name has to be resolvable from this catalogue.
    for module in app.modules:
        if module.area_safe_key:
            keys.key(module.area_safe_key)
        for _command, permits in module.permits:
            for permit in permits:
                keys.key(permit.key)

    write_capabilities = [
        {
            "CapabilityIndex": ordinal,
            "PathKey": keys.key(f"{record.name}.{member.name}"),
            "WriteKeyKey": keys.key(member.write_key),
            "LabelKey": keys.key(member.label_key),
            "ConfigKind": (CFG_KIND_LINE if record.line_cfg else CFG_KIND_STATION if record.station_cfg
                           else CFG_KIND_PAR),
            "ValueType": (CFG_TYPE_DURATION if member.kind == "duration_ms"
                          else CFG_TYPE_BOOLEAN if member.kind == "boolean"
                          else CFG_TYPE_NUMBER),
            "Minimum": member.minimum,
            "Maximum": member.maximum,
            "RequiresReady": 1 if member.requires_ready else 0,
            "UnitCode": (30 if record.line_cfg and member.name.startswith('ProductionTarget')
                         else 3 if record.line_cfg and not member.name.startswith('ActiveDays') else 0),
            "CaptureSourceKey": keys.key(member.capture_source) if member.capture_source else 0,
            "ClassKey": keys.key(member.class_id) if member.class_id else 0,
            "MinReadLevel": member.min_read_level,
            "MinWriteLevel": member.min_write_level,
        }
        for ordinal, record, member in gen.editable_values(app)
    ]

    return {
        "Roots": roots,
        "Modules": modules,
        "Nameplates": nameplates,
        "Fields": fields,
        "Operations": operations,
        "Localization": [{"NumericKey": k, "PortableKey": text}
                         for k, text in keys.rows],
        "Rationalization": rationalization,
        "OptionalProfiles": ([] if app.line is None else [{
            'ProfileId': keys.key('std.profile.line'), 'ProfileVersion': line.CALENDAR_SCHEMA,
            'CapabilityMask': 3, 'ProjectionMask': 3}]),
        "WriteCapabilities": write_capabilities,
    }


def numeric_key(app: decl.Application, portable: str) -> int:
    """The published numeric key for a portable string, or 0 if unpublished.

    Zero is "no key", never key zero: the catalogue numbers from 1, so a caller
    that looks up something unregistered gets a value a client will not resolve
    rather than one that resolves to whatever happens to be first.
    """
    for row in content(app)["Localization"]:
        if row["PortableKey"] == portable:
            return row["NumericKey"]
    return 0


def content_hash(app: decl.Application) -> str:
    """A stable hash of the published content, for a reader to compare against."""
    import json

    rows = content(app)
    import fraktal_ab_mailbox_frame as frame
    identity = dict(tables=rows, nativeMailbox=frame.profile(app))
    if app.model_capacity:
        # A gateway must refuse an older image lacking the native catalog.
        identity['modelCatalog'] = dict(schema=1, capacity=app.model_capacity,
                                        createKind=37, exportCurrentKind=38)
    payload = json.dumps(identity,
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()


def config_revision(app: decl.Application) -> int:
    """Changes whenever the published content changes. **Not ordered.**

    It is derived from the content hash, so a later revision may be numerically
    smaller than an earlier one. Compare it for *inequality* only: the S7
    coherence protocol reads it, reads every table, reads it again and accepts
    the snapshot only if it did not change, which needs difference and never
    ordering. A client that caches "the highest revision seen" would silently
    miss a change, so do not write one.
    """
    return int(content_hash(app)[:6], 16)


# --- emission ---------------------------------------------------------------
#
# Capacities are sized to what this application declares, with headroom, and
# both the count and the capacity are published in the header - so a reader
# never has to guess how much of a table is real, and never has to hold a
# compiled-in constant. The frozen FRK_MAX_* values are the ceilings S7 owns and
# measured; an application may declare less as long as it says so, which is why
# Truncated exists and is computed rather than asserted.

HEADER_SCALARS = (
    "Magic", "SchemaMajor", "SchemaMinor", "CoreVersion", "BindingVersion",
    "FrameworkVersion", "ConfigRevision", "Valid", "Truncated", "KeyLength",
)


def key_string_length(app: decl.Application) -> int:
    """How wide the published key string has to be for this declaration."""
    longest = max(
        [len(row["PortableKey"]) for row in content(app)["Localization"]] + [0])
    rounded = -(-longest // KEY_STRING_GRANULARITY) * KEY_STRING_GRANULARITY
    return max(KEY_STRING_MINIMUM, rounded)


def key_string_type(app: decl.Application) -> str:
    return f"FRK_T_{app.name}Key{key_string_length(app)}"


def header_type(app: decl.Application) -> str:
    return f"FRK_T_{app.name}MfHeader"


def manifest_tag(app: decl.Application, table: Table) -> str:
    return f"FRK_{app.name}_Mf{table.name}"


def header_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_MfHeader"


def _member(name: str, data_type: str, key_type: str) -> str:
    radix = "NullType" if data_type == key_type else "Decimal"
    return (f'<Member Name="{name}" DataType="{data_type}" Dimension="0" '
            f'Radix="{radix}" Hidden="false" ExternalAccess="Read Only"/>')


def data_types(app: decl.Application) -> list[str]:
    """The manifest's UDTs: a portable-key string, one row type per table, header."""
    key = key_string_type(app)
    parts = [
        f'<DataType Name="{key}" Family="StringFamily" Class="User">\n<Members>\n'
        f'<Member Name="LEN" DataType="DINT" Dimension="0" Radix="Decimal" '
        f'Hidden="false" ExternalAccess="Read Only"/>\n'
        f'<Member Name="DATA" DataType="SINT" Dimension="{key_string_length(app)}" '
        f'Radix="ASCII" Hidden="false" ExternalAccess="Read Only"/>\n'
        f"</Members>\n</DataType>"
    ]
    for table in tables(app):
        body = "\n".join(
            _member(name, key if dt == KEY32 else dt, key)
            for name, dt in table.members)
        parts.append(f'<DataType Name="{table.row_type}" Family="NoFamily" '
                     f'Class="User">\n<Members>\n{body}\n</Members>\n</DataType>')
    members = [_member(name, "DINT", key) for name in HEADER_SCALARS]
    members.append(_member("ContentHash", key, key))
    members.append(_member("ControllerIdentity", key, key))
    for table in tables(app):
        members.append(_member(f"{table.name}Count", "DINT", key))
        members.append(_member(f"{table.name}Capacity", "DINT", key))
    body = "\n".join(members)
    parts.append(f'<DataType Name="{header_type(app)}" Family="NoFamily" '
                 f'Class="User">\n<Members>\n{body}\n</Members>\n</DataType>')
    return parts


def ascii_literal(text: str) -> str:
    """Render text the way Logix writes ASCII string data: quoted and escaped.

    Logix does not accept bare characters here. Everywhere Studio itself emits
    ASCII string data - an L5K initialiser, a Data Format="String" block - it
    wraps the characters in single quotes and escapes with a dollar sign. Bare
    text imports with a warning and the value is silently dropped, which is the
    difference between a manifest that carries its content and one that only
    claims to.
    """
    out = []
    for ch in text:
        if ch == "$":
            out.append("$$")
        elif ch == "'":
            out.append("$'")
        elif " " <= ch <= "~":
            out.append(ch)
        else:
            out.append("$%02X" % ord(ch) if ord(ch) < 256 else "$3F")
    return "'" + "".join(out) + "'"


def _string_member(name: str, key: str, text: str, length: int) -> str:
    # Silently cutting a key here is how the manifest would come to publish two
    # different paths under one name, so a key that does not fit is a build
    # failure rather than a shorter string.
    if len(text) > length:
        raise ValueError(
            f"{name} is {len(text)} characters and the published key string "
            f"holds {length}: {text!r}")
    return (f'<StructureMember Name="{name}" DataType="{key}">\n'
            f'<DataValueMember Name="LEN" DataType="DINT" Radix="Decimal" '
            f'Value="{len(text)}"/>\n'
            f'<DataValueMember Name="DATA" DataType="{key}" Radix="ASCII">\n'
            f"<![CDATA[{ascii_literal(text)}]]>\n"
            f"</DataValueMember>\n</StructureMember>")


def _row_structure(table: Table, key: str, row: dict, length: int) -> str:
    parts = []
    for name, dt in table.members:
        if dt == KEY32:
            parts.append(_string_member(name, key, str(row.get(name, "")), length))
        else:
            parts.append(f'<DataValueMember Name="{name}" DataType="DINT" '
                         f'Radix="Decimal" Value="{int(row.get(name, 0))}"/>')
    return (f'<Structure DataType="{table.row_type}">\n'
            + "\n".join(parts) + "\n</Structure>")


def tags(app: decl.Application, controller_identity: str) -> list[str]:
    """The manifest tags, carrying their content as initial values.

    The manifest is static configuration, so it lives in the project rather than
    being computed at scan time: a client reads the same bytes the gate verified.
    """
    key = key_string_type(app)
    width = key_string_length(app)
    rows = content(app)
    out: list[str] = []

    truncated = any(len(rows[t.name]) > t.capacity for t in tables(app))
    header_values = {
        "Magic": MANIFEST_MAGIC,
        "SchemaMajor": MANIFEST_SCHEMA_MAJOR,
        "SchemaMinor": MANIFEST_SCHEMA_MINOR,
        "CoreVersion": CORE_VERSION,
        "BindingVersion": BINDING_VERSION,
        "FrameworkVersion": FRAMEWORK_VERSION,
        "ConfigRevision": config_revision(app),
        "Valid": 0 if truncated else 1,
        "Truncated": 1 if truncated else 0,
        # Published so a client sizes its read from the manifest rather than
        # from a constant it was compiled with.
        "KeyLength": width,
    }
    members = [f'<DataValueMember Name="{n}" DataType="DINT" Radix="Decimal" '
               f'Value="{v}"/>' for n, v in header_values.items()]
    members.append(_string_member("ContentHash", key, content_hash(app), width))
    members.append(_string_member("ControllerIdentity", key,
                                  controller_identity, width))
    for table in tables(app):
        members.append(f'<DataValueMember Name="{table.name}Count" DataType="DINT" '
                       f'Radix="Decimal" Value="{len(rows[table.name])}"/>')
        members.append(f'<DataValueMember Name="{table.name}Capacity" '
                       f'DataType="DINT" Radix="Decimal" Value="{table.capacity}"/>')
    out.append(
        f'<Tag Name="{header_tag(app)}" TagType="Base" '
        f'DataType="{header_type(app)}" Constant="false" '
        f'ExternalAccess="Read Only">\n<Data Format="Decorated">\n'
        f'<Structure DataType="{header_type(app)}">\n'
        + "\n".join(members)
        + "\n</Structure>\n</Data>\n</Tag>")

    for table in tables(app):
        table_rows = rows[table.name][:table.capacity]
        elements = []
        for index in range(table.capacity):
            row = table_rows[index] if index < len(table_rows) else {}
            elements.append(f'<Element Index="[{index}]">\n'
                            + _row_structure(table, key, row, width)
                            + "\n</Element>")
        out.append(
            f'<Tag Name="{manifest_tag(app, table)}" TagType="Base" '
            f'DataType="{table.row_type}" Dimensions="{table.capacity}" '
            f'Constant="false" ExternalAccess="Read Only">\n'
            f'<Data Format="Decorated">\n'
            f'<Array DataType="{table.row_type}" Dimensions="{table.capacity}">\n'
            + "\n".join(elements)
            + "\n</Array>\n</Data>\n</Tag>")
    return out


def evidence(app: decl.Application) -> dict[str, object]:
    rows = content(app)
    return {
        "Schema": SCHEMA,
        "SchemaMajor": MANIFEST_SCHEMA_MAJOR,
        "SchemaMinor": MANIFEST_SCHEMA_MINOR,
        "ConfigRevision": config_revision(app),
        "ContentHash": content_hash(app),
        "KeyLength": key_string_length(app),
        "Tables": {t.name: {"rows": len(rows[t.name]), "capacity": t.capacity}
                   for t in tables(app)},
        "Truncated": any(len(rows[t.name]) > t.capacity for t in tables(app)),
        # The whole manifest a client would read, header included - the tables
        # alone would understate what it costs to discover the station.
        "EstimatedBytes": estimated_bytes(app),
    }


# S7's cost curve (AB_S7_MANIFEST_EVIDENCE.md): 43,728 bytes read in 292.9 ms
# at a 500-byte connection and 61.6 ms at 4000. Part III permits a capacity
# raise against that curve; discovery pays it on connect/revision change,
# while the live-tier header poll stays the same size.
#
# Phase 6 room raises Fields and Localization from 512 to 768. At the press's
# current key width the manifest grows from 55,160 to 79,736 bytes: ~534 ms
# and ~112 ms on S7's curve. The 96 KiB bound also accommodates keys growing
# to 80 characters (98,216 bytes), rather than spending the whole allowance
# on today's strings. The bound itself projects to ~658 ms and ~138 ms.
# These are estimates, not new measurements. Read the enlarged manifest back
# from the controller before building Phase 6 features on it.
# Item 1's CaptureSourceKey adds 256 bytes at capacity. 100 KiB keeps the tested
# 80-character key envelope (98,472 bytes) inside the generation bound.
# S7's curve projects about 686 ms at 500 bytes and 144 ms at 4000 bytes.
MANIFEST_BUDGET_BYTES = 102_400


def estimated_bytes(app: decl.Application) -> int:
    """Every byte a client reads to take the manifest, at declared capacity."""
    width = key_string_length(app)
    total = len(HEADER_SCALARS) * 4 + 2 * (width + 4) + 2 * 4 * len(tables(app))
    for table in tables(app):
        total += table.capacity * sum(
            (width + 4) if dt == KEY32 else 4 for _, dt in table.members)
    return total
