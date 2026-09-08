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
MANIFEST_SCHEMA_MAJOR = 1
MANIFEST_SCHEMA_MINOR = 0
MANIFEST_MAGIC = 0x4652414B  # 'FRAK'

CORE_VERSION = 1
BINDING_VERSION = 1
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

# Logical value types, from the frozen contract's `logicalTypes`.
LOGICAL_INT32 = 3
LOGICAL_DURATION_MS = 9
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


@dataclass(frozen=True)
class Table:
    """One manifest table: a capacity symbol and the row type behind it."""

    name: str
    symbol: str
    row_type: str
    members: tuple[tuple[str, str], ...]
    capacity: int


KEY32 = "KEY32"


def tables(app: decl.Application) -> tuple[Table, ...]:
    p = app.name
    return (
        Table("Roots", "FRK_MAX_ROOTS", f"FRK_T_{p}MfRoot",
              (("RootId", "DINT"), ("ModuleIndex", "DINT"),
               ("RepositoryScope", "DINT"), ("MailboxId", "DINT"),
               ("HostEventId", "DINT")), 4),
        Table("Modules", "FRK_MAX_MODULES", f"FRK_T_{p}MfModule",
              (("ModuleId", "DINT"), ("ParentModuleId", "DINT"), ("RootId", "DINT"),
               ("RegistryIndex", "DINT"), ("Tier", "DINT"), ("TypeId", "DINT"),
               ("LocalNameKey", "DINT"), ("CanonicalPathKey", "DINT"),
               ("Capabilities", "DINT"), ("ContractAddress", "DINT")), 16),
        Table("Nameplates", "FRK_MAX_MODULES", f"FRK_T_{p}MfNameplate",
              (("ModuleId", "DINT"), ("ManufacturerKey", "DINT"),
               ("ProductKey", "DINT"), ("ModelKey", "DINT"), ("SerialKey", "DINT"),
               ("HardwareRevision", "DINT"), ("SoftwareRevision", "DINT"),
               ("AssetKey", "DINT"), ("LocationKey", "DINT")), 16),
        Table("Fields", "FRK_MAX_FIELDS", f"FRK_T_{p}MfField",
              (("ModuleId", "DINT"), ("PathKey", "DINT"), ("LogicalType", "DINT"),
               ("Dimensions", "DINT"), ("ReadTier", "DINT"), ("AccessClass", "DINT"),
               ("QualitySource", "DINT"),
               ("WriteCapabilityIndex", "DINT")), 192),
        Table("Operations", "FRK_MAX_OPERATIONS", f"FRK_T_{p}MfOperation",
              (("OperationId", "DINT"), ("TargetScope", "DINT"),
               ("ParameterType", "DINT"), ("ResultType", "DINT"),
               ("GatedAction", "DINT"), ("Minimum", "DINT"), ("Maximum", "DINT"),
               ("OperationKind", "DINT")), 32),
        Table("Localization", "FRK_MAX_LOCALIZATION_KEYS", f"FRK_T_{p}MfLocale",
              (("NumericKey", "DINT"), ("PortableKey", KEY32)), 224),
        Table("Rationalization", "FRK_MAX_REASONS", f"FRK_T_{p}MfReason",
              (("ReasonCode", "DINT"), ("Priority", "DINT"), ("Category", "DINT"),
               ("ActionKey", "DINT"), ("ConsequenceKey", "DINT"),
               ("Shelvable", "DINT")), 32),
        Table("OptionalProfiles", "FRK_MAX_OPTIONAL_PROFILES",
              f"FRK_T_{p}MfProfile",
              (("ProfileId", "DINT"), ("ProfileVersion", "DINT"),
               ("CapabilityMask", "DINT"), ("ProjectionMask", "DINT")), 8),
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
        # No mailbox and no host-event ring exist yet; the initial claim is
        # read-only, and a zero here says "not published" rather than "id 0".
        "MailboxId": 0,
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

    def add_fields(module_id: int, prefix: str, members, tier: int,
                   access: int = ACCESS_READ) -> None:
        for member in members:
            fields.append({
                "ModuleId": module_id,
                "PathKey": keys.key(f"{prefix}.{member.name}"),
                "LogicalType": (LOGICAL_DURATION_MS
                                if member.kind == "duration_ms" else LOGICAL_INT32),
                "Dimensions": member.dimension,
                "ReadTier": tier,
                "AccessClass": access,
                "QualitySource": QUALITY_GATEWAY_READ_TIME,
                "WriteCapabilityIndex": 0,
            })

    unit_id = ids[app.name]
    add_fields(unit_id, f"{app.name}.Unit", gen.unit_context_members(app), TIER_LIVE)
    add_fields(unit_id, f"{app.name}.Chart", gen.chart_members(app), TIER_LIVE)
    for record in app.records:
        add_fields(unit_id, f"{app.name}.{record.name}", record.members, TIER_SLOW)
    for module in app.modules:
        add_fields(ids[module.name], f"{app.name}.{module.name}",
                   gen.module_context_members(), TIER_LIVE)

    # Simulated plant and operator inputs are published as writable fields rather
    # than as operations: they stand in for signals a real machine would take
    # from I/O, not for something a client asks the machine to do.
    for tag in app.sim_inputs:
        if tag not in publishable:
            continue
        fields.append({
            "ModuleId": unit_id, "PathKey": keys.key(tag),
            "LogicalType": LOGICAL_INT32, "Dimensions": 0,
            "ReadTier": TIER_LIVE, "AccessClass": ACCESS_WRITE,
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
                  max(c.mode_ordinal for c in app.chains))
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

    rationalization = []
    for name, code in sorted(app.reasons.items(), key=lambda item: item[1]):
        held = name in ("HELD_PERMISSIVE", "TWO_HAND_RELEASED")
        waiting = name.startswith("WAIT_")
        rationalization.append({
            "ReasonCode": code,
            # A held or waiting condition is designed behaviour, not a fault:
            # low priority, and shelvable, because it is the machine asking
            # rather than the machine broken.
            "Priority": 0 if (held or waiting) else 2,
            "Category": 1 if (held or waiting) else 2,
            "ActionKey": keys.key(f"project.reason.{name.lower()}.action"),
            "ConsequenceKey": keys.key(f"project.reason.{name.lower()}.consequence"),
            "Shelvable": 1 if (held or waiting) else 0,
        })

    return {
        "Roots": roots,
        "Modules": modules,
        "Nameplates": nameplates,
        "Fields": fields,
        "Operations": operations,
        "Localization": [{"NumericKey": k, "PortableKey": text}
                         for k, text in keys.rows],
        "Rationalization": rationalization,
        "OptionalProfiles": [],
    }


def content_hash(app: decl.Application) -> str:
    """A stable hash of the published content, for a reader to compare against."""
    import json

    rows = content(app)
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
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


def estimated_bytes(app: decl.Application) -> int:
    """Every byte a client reads to take the manifest, at declared capacity."""
    width = key_string_length(app)
    total = len(HEADER_SCALARS) * 4 + 2 * (width + 4) + 2 * 4 * len(tables(app))
    for table in tables(app):
        total += table.capacity * sum(
            (width + 4) if dt == KEY32 else 4 for _, dt in table.members)
    return total
