"""Physical canonical manifest V6. Shared wire rules; no station imports.

The V5 context manifest remains available to the migration oracle. A V6 reader
finds this record by its header shape and magic, never an application tag name.
Only a PLC-resident, hash-validated manifest can describe a live acquisition.
"""
from __future__ import annotations

import hashlib
import json
import re
import fraktal_ab_read_coherence as read_coherence

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
TYPE_MINOR = 4
PRODUCT_MINOR = 5
COMMAND_MINOR = 6
IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,39}\Z')
TYPE_FIELD = frozenset(('TypeName', 'MemberName', 'LogicalType', 'LowerBound',
                        'ElementCount', 'CountMember', 'EffectiveAccess'))
READ_MINOR = read_coherence.MINOR
TYPE_HEADER = (SERVICE_HEADER - {'FieldsCount', 'FieldsCapacity', 'Fields', 'Bindings', 'Services'}) | {
    'TypeAnnotationsCount', 'TypeAnnotationsCapacity', 'TypeAnnotations',
    'PathExceptionsCount', 'PathExceptionsCapacity'}
PRODUCT_HEADER = TYPE_HEADER | {'DataProductsCount', 'DataProductsCapacity'}
PRODUCT_FIELD = frozenset(('SourceSymbol', 'CoreType', 'CanonicalRoot'))
COMMAND_HEADER = PRODUCT_HEADER | {'CommandBindingsCount','CommandBindingsCapacity','CommandOperationsCount','CommandOperationsCapacity'}
READ_HEADER = COMMAND_HEADER | read_coherence.HEADER_FIELDS
READ_SERVICE_MINOR = 8
READ_SERVICE_HEADER = READ_HEADER | {"ReadServicesCount","ReadServicesCapacity","ReadServices"}


def data_products(rows):
    """Generic product binding validation. CoreType is descriptive, not dispatch."""
    if not isinstance(rows,list) or len(rows)>1024:
        raise ValueError('invalid data product table')
    sources,roots=set(),[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!=PRODUCT_FIELD:
            raise ValueError('invalid data product descriptor')
        source,core,root=(row[k] for k in ('SourceSymbol','CoreType','CanonicalRoot'))
        if not isinstance(source,str) or not IDENTIFIER.fullmatch(source) or source in sources \
                or not isinstance(core,str) or not IDENTIFIER.fullmatch(core) \
                or not isinstance(root,str) or not COUNT_PATH.fullmatch(root) or len(root.encode('utf-8'))>PATH_WIDTH \
                or any(root==old or root.startswith(old+'/') or old.startswith(root+'/') for old in roots):
            raise ValueError('invalid, duplicate or overlapping data product binding')
        sources.add(source);roots.append(root)
    return rows


def type_tables(rows, exceptions):
    """Validate plain V6.4 rows; called by both engineering and wire decoding."""
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_FIELDS \
            or not isinstance(exceptions, list) or len(exceptions) > MAX_FIELDS:
        raise ValueError('invalid V6.4 annotation tables')
    annotations, paths = {}, {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != TYPE_FIELD:
            raise ValueError('invalid V6.4 type annotation shape')
        if any(not isinstance(row[k], str) or not IDENTIFIER.fullmatch(row[k])
               for k in ('TypeName', 'MemberName')):
            raise ValueError('invalid V6.4 type/member identifier')
        pair = (row['TypeName'], row['MemberName'])
        logical, access = row['LogicalType'], row['EffectiveAccess']
        lower, extent, count = row['LowerBound'], row['ElementCount'], row['CountMember']
        if pair in annotations or logical not in LOGICAL_TYPES | {'UINT16'} or access not in ACCESS | {''}:
            raise ValueError('duplicate or unsupported V6.4 type annotation')
        if type(lower) is not int or type(extent) is not int or not 0 <= extent <= MAX_FIELDS \
                or not -(1 << 31) <= lower < (1 << 31) or (extent == 0 and lower != 0):
            raise ValueError('invalid V6.4 logical extent')
        if not isinstance(count, str) or (count and (not IDENTIFIER.fullmatch(count) or not extent)):
            raise ValueError('invalid V6.4 sibling count member')
        annotation = {}
        if logical: annotation['logicalType'] = logical
        if access: annotation['effectiveAccess'] = access
        if extent: annotation.update(lowerBound=lower, elementCount=extent)
        if count: annotation['countMember'] = count
        if not annotation:
            raise ValueError('redundant empty V6.4 type annotation')
        annotations[pair] = annotation
    for row in exceptions:
        if not isinstance(row, dict) or set(row) != {'CanonicalPath', 'Indices'}:
            raise ValueError('invalid V6.4 path exception shape')
        path, selection = row['CanonicalPath'], row['Indices']
        if not isinstance(path, str) or not PATH.fullmatch(path) or len(path.encode('utf-8')) > PATH_WIDTH \
                or path in paths or not isinstance(selection, str) or len(selection.encode('utf-8')) > PATH_WIDTH:
            raise ValueError('invalid or duplicate V6.4 path exception')
        indices = json.loads(selection)
        if not isinstance(indices, list) or any(type(i) is not int or not 0 <= i < MAX_FIELDS for i in indices) \
                or indices != sorted(set(indices)):
            raise ValueError('invalid V6.4 index selection')
        paths[path] = dict(indices=indices)
    return annotations, paths


def body(fields, legacy_hash, stage=STAGE, *, minor=MINOR, bindings=None, services=None,
         type_annotations=None, path_exceptions=None, products=None, commands=None, operations=None, read_coherence_bindings=None, read_services=None):
    result=dict(schemaMajor=MAJOR, schemaMinor=minor, publicationStage=stage,
                legacyContentHash=legacy_hash, fields=fields)
    if minor>=FRAGMENT_MINOR:result['bindings']=bindings
    if minor>=SERVICE_MINOR:result['services']=services
    if minor >= TYPE_MINOR:
        del result['fields']
        result.update(typeAnnotations=type_annotations, pathExceptions=path_exceptions)
    if minor>=PRODUCT_MINOR:result['dataProducts']=products
    if minor>=COMMAND_MINOR:result.update(commandBindings=commands,commandOperations=operations)
    if minor>=READ_MINOR:result['readCoherenceBindings']=read_coherence_bindings
    if minor>=READ_SERVICE_MINOR:result['readServices']=read_services
    return result


def content_hash(fields, legacy_hash, stage=STAGE, *, minor=MINOR, bindings=None, services=None,
                 type_annotations=None, path_exceptions=None, products=None, commands=None, operations=None, read_coherence_bindings=None, read_services=None):
    raw = json.dumps(body(fields, legacy_hash, stage, minor=minor,bindings=bindings,services=services,
                         type_annotations=type_annotations,path_exceptions=path_exceptions,products=products,commands=commands,operations=operations,read_coherence_bindings=read_coherence_bindings,read_services=read_services), ensure_ascii=True,
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
    expected = SERVICE_HEADER if minor==SERVICE_MINOR else FRAGMENT_HEADER if minor==FRAGMENT_MINOR else HEADER
    if minor in (TYPE_MINOR,PRODUCT_MINOR,COMMAND_MINOR,READ_MINOR,READ_SERVICE_MINOR):
        expected = (READ_SERVICE_HEADER if minor==READ_SERVICE_MINOR else READ_HEADER if minor==READ_MINOR else COMMAND_HEADER if minor==COMMAND_MINOR else PRODUCT_HEADER if minor==PRODUCT_MINOR else TYPE_HEADER) | {name for name in ('Bindings', 'Services', 'PathExceptions', 'DataProducts', 'CommandBindings', 'CommandOperations')
                                  if record.get(name+'Count', 0)}
    if set(record) != expected or record["Magic"] != MAGIC:
        raise ValueError("unrecognized canonical manifest header")
    if any(type(record[k]) is not int for k in ("Magic", "SchemaMajor", "SchemaMinor", "PublicationStage")) \
            or record["SchemaMajor"] != MAJOR or record["SchemaMinor"] not in (MINOR, VIEW_MINOR, FRAGMENT_MINOR, SERVICE_MINOR, TYPE_MINOR, PRODUCT_MINOR, COMMAND_MINOR, READ_MINOR, READ_SERVICE_MINOR) \
            or not STAGE <= record["PublicationStage"] < (1 << 31):
        raise ValueError("unsupported canonical manifest version/stage")
    if record["Valid"] is not True or record["Truncated"] is not False:
        raise ValueError("canonical manifest is invalid or truncated")
    type_rows, exception_rows = [], []
    if minor >= TYPE_MINOR:
        for name, target, columns in (('TypeAnnotations', type_rows, TYPE_FIELD),
                                      ('PathExceptions', exception_rows, {'CanonicalPath', 'Indices'})):
            count, capacity, rows = record[name+'Count'], record[name+'Capacity'], record.get(name, [])
            if type(count) is not int or type(capacity) is not int or not 0 <= count == capacity <= MAX_FIELDS \
                    or not isinstance(rows, list) or len(rows) != capacity:
                raise ValueError('invalid V6.4 table count/capacity')
            for row in rows:
                if not isinstance(row, dict) or set(row) != columns:
                    raise ValueError('invalid V6.4 table row shape')
                target.append({k: v if k in ('LowerBound', 'ElementCount') else text(v) for k, v in row.items()})
        type_tables(type_rows, exception_rows)
        rows = []
    else:
        count, capacity, rows = record["FieldsCount"], record["FieldsCapacity"], record["Fields"]
        if type(count) is not int or type(capacity) is not int or not 0 < count <= capacity <= MAX_FIELDS \
                or not isinstance(rows, list) or len(rows) != capacity:
            raise ValueError("invalid canonical field count/capacity")
        # Exact allocation: unused rows would be unvalidated metadata.
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
        if type(count) is not int or type(capacity) is not int or not (0 if minor>=TYPE_MINOR else 1)<=count==capacity<=1024 \
                or not isinstance(record.get('Bindings',[]),list) or len(record.get('Bindings',[]))!=capacity:
            raise ValueError('invalid canonical binding count/capacity')
        sources=set()
        for item in record.get('Bindings',[]):
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
        if type(count) is not int or type(capacity) is not int or not (0 if minor>=TYPE_MINOR else 1)<=count==capacity<=16 \
                or not isinstance(record.get('Services',[]),list) or len(record.get('Services',[]))!=capacity:
            raise ValueError('invalid canonical service count/capacity')
        kinds=set()
        for item in record.get('Services',[]):
            if set(item)!={'Kind','Version','BuildRevision','RequestSymbol','RequestMember','ResponseSymbol'}:
                raise ValueError('invalid canonical service descriptor')
            if type(item['Kind']) is not int or item['Kind'] not in ((1,2,3) if minor>=COMMAND_MINOR else (1,2)) or item['Kind'] in kinds or type(item['Version']) is not int or item['Version']!=1:
                raise ValueError('unsupported or duplicate canonical service')
            if type(item['BuildRevision']) is not int or not 1<=item['BuildRevision']<1<<31:
                raise ValueError('invalid canonical service build revision')
            service={k:(text(v) if k.endswith(('Symbol','Member')) else v) for k,v in item.items()}
            if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,79}',service[k]) for k in ('RequestSymbol','RequestMember','ResponseSymbol')):
                raise ValueError('invalid canonical service symbol/member')
            kinds.add(item['Kind']);services.append(service)
    products=[]
    if minor>=PRODUCT_MINOR:
        count,capacity=record['DataProductsCount'],record['DataProductsCapacity']
        if type(count) is not int or type(capacity) is not int or not 0<=count==capacity<=1024 \
                or not isinstance(record.get('DataProducts',[]),list) or len(record.get('DataProducts',[]))!=capacity:
            raise ValueError('invalid data product count/capacity')
        for row in record.get('DataProducts',[]):
            if not isinstance(row,dict) or set(row)!=PRODUCT_FIELD:raise ValueError('invalid data product descriptor')
            products.append({k:text(v) for k,v in row.items()})
        data_products(products)
    commands=[];command_operations=[]
    if minor>=COMMAND_MINOR:
        from fraktal_ab_command_binding import FIELD as CMD_FIELD, TEXT_FIELDS, bindings as validate_commands
        count,capacity=record['CommandBindingsCount'],record['CommandBindingsCapacity']
        if type(count) is not int or type(capacity) is not int or not 1<=count==capacity<=1024 \
                or not isinstance(record.get('CommandBindings'),list) or len(record['CommandBindings'])!=capacity:
            raise ValueError('invalid command binding count/capacity')
        for row in record['CommandBindings']:
            if not isinstance(row,dict) or set(row)!=CMD_FIELD:raise ValueError('invalid command binding row')
            commands.append({k:text(v) if k in TEXT_FIELDS else v for k,v in row.items()})
        validate_commands(commands)
        from fraktal_ab_command_binding import operations as validate_operations, OPERATION_FIELD
        if record['CommandOperationsCount']!=39 or record['CommandOperationsCapacity']!=39 or not isinstance(record.get('CommandOperations'),list):
            raise ValueError('invalid command operation count/capacity')
        for row in record['CommandOperations']:
            if not isinstance(row,dict) or set(row)!=OPERATION_FIELD:raise ValueError('invalid command operation row')
            command_operations.append({k:text(v) if k=='RefusalKey' else v for k,v in row.items()})
        validate_operations(command_operations)
    coherence_rows=[]
    if minor>=READ_MINOR:
        count,capacity=record['ReadCoherenceBindingsCount'],record['ReadCoherenceBindingsCapacity']
        if type(count) is not int or type(capacity) is not int or not 1<=count==capacity<=1024 \
                or not isinstance(record['ReadCoherenceBindings'],list) or len(record['ReadCoherenceBindings'])!=count:
            raise ValueError('invalid read-coherence count/capacity')
        for row in record['ReadCoherenceBindings']:
            if not isinstance(row,dict) or set(row)!=read_coherence.FIELDS:raise ValueError('invalid read-coherence row')
            coherence_rows.append({k:text(v) if k in ('CanonicalPrefix','RevisionSymbol') else v for k,v in row.items()})
        read_coherence.validate_rows(coherence_rows)
    read_services=[]
    if minor>=READ_SERVICE_MINOR:
        from fraktal_ab_config_read_view import validate_descriptors,SERVICE_FIELD
        count,capacity=record['ReadServicesCount'],record['ReadServicesCapacity']
        if type(count) is not int or type(capacity) is not int or not 1<=count==capacity<=1024 \
                or not isinstance(record['ReadServices'],list) or len(record['ReadServices'])!=count:
            raise ValueError('invalid read-service count/capacity')
        for row in record['ReadServices']:
            if not isinstance(row,dict) or set(row)!=SERVICE_FIELD:raise ValueError('invalid read-service row')
            read_services.append({k:text(v) if k in ('RootSymbol','CanonicalRoot') else v for k,v in row.items()})
        validate_descriptors(read_services)
    legacy, digest = text(record["LegacyContentHash"]), text(record["ContentHash"])
    if not re.fullmatch(r"[A-F0-9]{16}", legacy) or digest != content_hash(fields, legacy, record['PublicationStage'], minor=minor,
            **({'bindings':bindings} if minor>=FRAGMENT_MINOR else {}),
            **({'services':services} if minor>=SERVICE_MINOR else {}),
            **({'type_annotations':type_rows,'path_exceptions':exception_rows} if minor>=TYPE_MINOR else {}),
            **({'products':products} if minor>=PRODUCT_MINOR else {}),
            **({'commands':commands,'operations':command_operations} if minor>=COMMAND_MINOR else {}),
            **({'read_coherence_bindings':coherence_rows} if minor>=READ_MINOR else {}),
            **({'read_services':read_services} if minor>=READ_SERVICE_MINOR else {})) \
            or type(record["ConfigRevision"]) is not int or record["ConfigRevision"] != revision(digest):
        raise ValueError("canonical manifest content hash/revision mismatch")
    result=dict(schemaMajor=MAJOR, schemaMinor=minor, valid=True, truncated=False, contentHash=digest,
                configRevision=record["ConfigRevision"], annotations=annotations,
                publicationStage=record['PublicationStage'], legacyContentHash=legacy)
    if minor>=FRAGMENT_MINOR:result.update(bindings=bindings,fragmentRevision=record['FragmentRevision'])
    if minor>=SERVICE_MINOR:result['services']=services
    if minor>=TYPE_MINOR:
        del result['annotations']
        result.update(typeAnnotations=type_rows,pathExceptions=exception_rows)
    if minor>=PRODUCT_MINOR:result['dataProducts']=products
    if minor>=COMMAND_MINOR:result.update(commandBindings=commands,commandOperations=command_operations)
    if minor>=READ_MINOR:result['readCoherenceBindings']=coherence_rows
    if minor>=READ_SERVICE_MINOR:result['readServices']=read_services
    return result


def read_manifest(comm, symbols, templates):
    """Read the unique V6 header discovered by shape, rejecting ambiguous roots."""
    from fraktal_ab_canonical_reader import decode_record
    by_handle = {row["handle"]: row for row in templates}
    found = []
    for symbol in symbols:
        # An atomic Symbol (the V6.6 command commit) has no Template; it is never the manifest.
        template = by_handle.get(symbol.get("handle"))
        if symbol.get("arrayRank", 0) or not template:
            continue
        names = {member['name'] for member in template['members']}
        if not (HEADER <= names or TYPE_HEADER <= names):
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
