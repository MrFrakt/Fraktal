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
VIEW_MINOR = 1
FRAGMENT_MINOR = 2
FRAGMENT_HEADER = HEADER | {'FragmentRevision','BindingsCount','BindingsCapacity','Bindings'}
SERVICE_MINOR = 3
SERVICE_HEADER = FRAGMENT_HEADER | {'ServicesCount','ServicesCapacity','Services'}
VIEW_FIELD = FIELD | {"CountPath", "Indices"}
COUNT_PATH = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:/[A-Za-z_][A-Za-z0-9_]*)+\Z")


def body(fields, legacy_hash, stage=STAGE, *, minor=MINOR, bindings=None, services=None):
    result=dict(schemaMajor=MAJOR, schemaMinor=minor, publicationStage=stage,
                legacyContentHash=legacy_hash, fields=fields)
    if minor>=FRAGMENT_MINOR:result['bindings']=bindings
    if minor>=SERVICE_MINOR:result['services']=services
    return result


def content_hash(fields, legacy_hash, stage=STAGE, *, minor=MINOR, bindings=None, services=None):
    raw = json.dumps(body(fields, legacy_hash, stage, minor=minor,bindings=bindings,services=services), ensure_ascii=True,
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
    minor=record.get('SchemaMinor')
    if set(record) != (SERVICE_HEADER if minor==SERVICE_MINOR else FRAGMENT_HEADER if minor==FRAGMENT_MINOR else HEADER) or record["Magic"] != MAGIC:
        raise ValueError("unrecognized canonical manifest header")
    if any(type(record[k]) is not int for k in ("Magic", "SchemaMajor", "SchemaMinor", "PublicationStage")) \
            or record["SchemaMajor"] != MAJOR or record["SchemaMinor"] not in (MINOR, VIEW_MINOR, FRAGMENT_MINOR, SERVICE_MINOR) \
            or not STAGE <= record["PublicationStage"] < (1 << 31):
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
    minor = record["SchemaMinor"]
    annotations, fields = {}, []
    for row in rows:
        if set(row) != (VIEW_FIELD if minor >= VIEW_MINOR else FIELD):
            raise ValueError("invalid canonical field row shape")
        path, logical, access = (text(row[k]) for k in ("CanonicalPath", "LogicalType", "EffectiveAccess"))
        lower, extent = row["LowerBound"], row["ElementCount"]
        if not PATH.fullmatch(path) or len(path.encode("utf-8")) > PATH_WIDTH or path in annotations:
            raise ValueError("invalid or duplicate canonical field path")
        if logical not in LOGICAL_TYPES | ({'UINT16'} if minor>=SERVICE_MINOR else set()) or access not in ACCESS:
            raise ValueError("unsupported canonical logical type/access")
        if type(lower) is not int or type(extent) is not int or not 0 <= extent <= MAX_FIELDS \
                or not -(1 << 31) <= lower < (1 << 31) or (extent == 0 and lower != 0):
            raise ValueError("invalid canonical logical extent")
        annotation = dict(effectiveAccess=access)
        if logical:
            annotation["logicalType"] = logical
        if extent:
            annotation.update(lowerBound=lower, elementCount=extent)
        normalized = dict(CanonicalPath=path, LogicalType=logical, EffectiveAccess=access,
                          LowerBound=lower, ElementCount=extent)
        if minor >= VIEW_MINOR:
            count_path, selection = text(row["CountPath"]), text(row["Indices"])
            if count_path and (not COUNT_PATH.fullmatch(count_path) or len(count_path.encode('utf-8')) > PATH_WIDTH):
                raise ValueError("invalid canonical array view reference/selection")
            indices = json.loads(selection) if selection else None
            if selection and (not isinstance(indices,list) or
                    any(type(i) is not int or not 0 <= i < extent for i in indices) or indices != sorted(set(indices))):
                raise ValueError("invalid canonical array view extent/selection")
            if (count_path or indices is not None) and (not extent or (count_path and indices is not None)):
                raise ValueError("invalid canonical array view extent/selection")
            if count_path:
                annotation['countPath'] = count_path
            if indices is not None:
                annotation['indices'] = indices
            normalized.update(CountPath=count_path, Indices=selection)
        annotations[path] = annotation
        fields.append(normalized)
    bindings=[]
    if minor>=FRAGMENT_MINOR:
        count,capacity=record['BindingsCount'],record['BindingsCapacity']
        if type(count) is not int or type(capacity) is not int or not 1<=count==capacity<=1024 \
                or not isinstance(record['Bindings'],list) or len(record['Bindings'])!=capacity:
            raise ValueError('invalid canonical binding count/capacity')
        sources=set()
        for item in record['Bindings']:
            if set(item)!={'SourceSymbol','TargetRoot'}:raise ValueError('invalid canonical record binding')
            binding={key:text(value) for key,value in item.items()}
            if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,79}',value) for value in binding.values()) \
                    or binding['SourceSymbol'] in sources or binding['SourceSymbol']==binding['TargetRoot']:
                raise ValueError('invalid or duplicate canonical record binding')
            sources.add(binding['SourceSymbol']);bindings.append(binding)
        if type(record['FragmentRevision']) is not int or not 0<=record['FragmentRevision']<1<<31:
            raise ValueError('invalid fragment data revision')
    services=[]
    if minor>=SERVICE_MINOR:
        count,capacity=record['ServicesCount'],record['ServicesCapacity']
        if type(count) is not int or type(capacity) is not int or not 1<=count==capacity<=16 \
                or not isinstance(record['Services'],list) or len(record['Services'])!=capacity:
            raise ValueError('invalid canonical service count/capacity')
        kinds=set()
        for item in record['Services']:
            if set(item)!={'Kind','Version','BuildRevision','RequestSymbol','RequestMember','ResponseSymbol'}:
                raise ValueError('invalid canonical service descriptor')
            if type(item['Kind']) is not int or item['Kind'] not in (1,2) or item['Kind'] in kinds or type(item['Version']) is not int or item['Version']!=1:
                raise ValueError('unsupported or duplicate canonical service')
            if type(item['BuildRevision']) is not int or not 1<=item['BuildRevision']<1<<31:
                raise ValueError('invalid canonical service build revision')
            service={k:(text(v) if k.endswith(('Symbol','Member')) else v) for k,v in item.items()}
            if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,79}',service[k]) for k in ('RequestSymbol','RequestMember','ResponseSymbol')):
                raise ValueError('invalid canonical service symbol/member')
            kinds.add(item['Kind']);services.append(service)
    legacy, digest = text(record["LegacyContentHash"]), text(record["ContentHash"])
    if not re.fullmatch(r"[A-F0-9]{16}", legacy) or digest != content_hash(fields, legacy, record['PublicationStage'], minor=minor,
            **({'bindings':bindings} if minor>=FRAGMENT_MINOR else {}),
            **({'services':services} if minor>=SERVICE_MINOR else {})) \
            or type(record["ConfigRevision"]) is not int or record["ConfigRevision"] != revision(digest):
        raise ValueError("canonical manifest content hash/revision mismatch")
    result=dict(schemaMajor=MAJOR, schemaMinor=minor, valid=True, truncated=False, contentHash=digest,
                configRevision=record["ConfigRevision"], annotations=annotations,
                publicationStage=record['PublicationStage'], legacyContentHash=legacy)
    if minor>=FRAGMENT_MINOR:result.update(bindings=bindings,fragmentRevision=record['FragmentRevision'])
    if minor>=SERVICE_MINOR:result['services']=services
    return result


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
