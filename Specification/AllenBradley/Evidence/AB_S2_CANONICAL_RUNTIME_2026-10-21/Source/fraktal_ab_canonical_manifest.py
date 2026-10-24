"""Physical canonical manifest V6. Shared wire rules; no station imports.

The V5 context manifest remains available to the migration oracle. A V6 reader
finds this record by its header shape and magic, never an application tag name.
Only a PLC-resident, hash-validated manifest can describe a live acquisition.
"""
from __future__ import annotations

import hashlib
import json
import re

MAGIC = 0x46524B36
MAJOR = 6
MINOR = 0
STAGE = 2
MAX_FIELDS = 100_000
PATH_WIDTH = 255
LOGICAL_TYPES = frozenset(("", "BOOL", "ENUM", "DURATION", "TIMESTAMP", "BITSTRING32"))
ACCESS = frozenset(("Read Only", "Read/Write"))
PATH = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\[\*\])?(?:/[A-Za-z_][A-Za-z0-9_]*(?:\[\*\])?)+\Z")
HEADER = frozenset(("Magic", "SchemaMajor", "SchemaMinor", "PublicationStage",
                    "Valid", "Truncated", "ContentHash", "ConfigRevision",
                    "LegacyContentHash", "FieldsCount", "FieldsCapacity", "Fields"))
FIELD = frozenset(("CanonicalPath", "LogicalType", "EffectiveAccess", "LowerBound", "ElementCount"))


def body(fields, legacy_hash, stage=STAGE):
    return dict(schemaMajor=MAJOR, schemaMinor=MINOR, publicationStage=stage,
                legacyContentHash=legacy_hash, fields=fields)


def content_hash(fields, legacy_hash, stage=STAGE):
    raw = json.dumps(body(fields, legacy_hash, stage), ensure_ascii=True,
                     separators=(",", ":"), sort_keys=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest().upper()


def revision(digest):
    return int(digest[:7], 16) or 1


def text(value):
    if not isinstance(value, dict) or value.get("string") is not True:
        raise ValueError("manifest text is not a decoded StringFamily")
    raw = bytes.fromhex(value["bytes"])
    if value["LEN"] != len(raw) or not 0 <= len(raw) <= value["width"]:
        raise ValueError("invalid manifest string extent")
    return raw.decode("utf-8", errors="strict")


def normalize(record):
    """Validate every row and its hash before exposing any annotation."""
    if set(record) != HEADER or record["Magic"] != MAGIC:
        raise ValueError("unrecognized canonical manifest header")
    if any(type(record[k]) is not int for k in ("Magic", "SchemaMajor", "SchemaMinor", "PublicationStage")) \
            or (record["SchemaMajor"], record["SchemaMinor"], record["PublicationStage"]) != (MAJOR, MINOR, STAGE):
        raise ValueError("unsupported canonical manifest version/stage")
    if record["Valid"] is not True or record["Truncated"] is not False:
        raise ValueError("canonical manifest is invalid or truncated")
    count, capacity, rows = record["FieldsCount"], record["FieldsCapacity"], record["Fields"]
    if type(count) is not int or type(capacity) is not int or not 0 < count <= capacity <= MAX_FIELDS \
            or not isinstance(rows, list) or len(rows) != capacity:
        raise ValueError("invalid canonical field count/capacity")
    # Exact allocation in V6.0: unused rows would be unvalidated metadata.
    if count != capacity:
        raise ValueError("V6.0 requires exactly allocated Fields")
    annotations, fields = {}, []
    for row in rows:
        if set(row) != FIELD:
            raise ValueError("invalid canonical field row shape")
        path, logical, access = (text(row[k]) for k in ("CanonicalPath", "LogicalType", "EffectiveAccess"))
        lower, extent = row["LowerBound"], row["ElementCount"]
        if not PATH.fullmatch(path) or len(path.encode("utf-8")) > PATH_WIDTH or path in annotations:
            raise ValueError("invalid or duplicate canonical field path")
        if logical not in LOGICAL_TYPES or access not in ACCESS:
            raise ValueError("unsupported canonical logical type/access")
        if type(lower) is not int or type(extent) is not int or not 0 <= extent <= MAX_FIELDS \
                or not -(1 << 31) <= lower < (1 << 31) or (extent == 0 and lower != 0):
            raise ValueError("invalid canonical logical extent")
        annotation = dict(effectiveAccess=access)
        if logical:
            annotation["logicalType"] = logical
        if extent:
            annotation.update(lowerBound=lower, elementCount=extent)
        annotations[path] = annotation
        fields.append(dict(CanonicalPath=path, LogicalType=logical, EffectiveAccess=access,
                           LowerBound=lower, ElementCount=extent))
    legacy, digest = text(record["LegacyContentHash"]), text(record["ContentHash"])
    if not re.fullmatch(r"[A-F0-9]{16}", legacy) or digest != content_hash(fields, legacy) \
            or type(record["ConfigRevision"]) is not int or record["ConfigRevision"] != revision(digest):
        raise ValueError("canonical manifest content hash/revision mismatch")
    return dict(schemaMajor=MAJOR, valid=True, truncated=False, contentHash=digest,
                configRevision=record["ConfigRevision"], annotations=annotations,
                publicationStage=STAGE, legacyContentHash=legacy)


def read_manifest(comm, symbols, templates):
    """Read the unique V6 header discovered by shape, rejecting ambiguous roots."""
    from fraktal_ab_canonical_reader import decode_record
    by_handle = {row["handle"]: row for row in templates}
    found = []
    for symbol in symbols:
        template = by_handle.get(symbol["handle"])
        if symbol.get("arrayRank", 0) or not template or not HEADER <= {
                member["name"] for member in template["members"]}:
            continue
        reply = comm.Read(symbol["name"])
        if reply.Status != "Success" or not isinstance(reply.Value, (bytes, bytearray)):
            raise ValueError("canonical manifest record read failed")
        record = decode_record(bytes(reply.Value), symbol["handle"], templates)
        if record["Magic"] == MAGIC:
            found.append(normalize(record))
    if len(found) != 1:
        raise ValueError("canonical manifest missing or ambiguous")
    return found[0]
