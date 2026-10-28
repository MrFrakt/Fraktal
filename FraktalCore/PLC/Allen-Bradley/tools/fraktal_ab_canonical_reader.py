#!/usr/bin/env python3
"""S1 read-only reference oracle. No declaration, projection or station imports.

The pure reader consumes a recorded Symbol/Template/raw-byte acquisition plus
the PLC manifest's logical annotations. The physical V6 loader lives in
fraktal_ab_canonical_manifest and normalizes the controller-resident record.
No file supplies station facts to a live read.
Canonical decoding requires Template attribute 5 structure sizes. Historical S0
captures lack those sizes and have a separately labelled diagnostic replay.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import gzip
import json
from pathlib import Path
import re
import struct
from types import SimpleNamespace

from fraktal_ab_s0_canonical_measure import (
    decode, discover_templates, is_string, member_table,
)

SCHEMA = "fraktal.ab.canonical-capture"
SNAPSHOT = "fraktal.opcua.snapshot.v1"
MAX_BYTES = 16 * 1024 * 1024
MAX_LEAVES = 100_000
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
NATIVE_TYPES = {0xC1: "Boolean", 0xC2: "SByte", 0xC3: "Int16", 0xC4: "Int32",
                0xC5: "Int64", 0xC6: "Byte", 0xC7: "UInt16", 0xC8: "UInt32",
                0xC9: "UInt64", 0xCA: "Float", 0xCB: "Double", 0xD3: "UInt32",
                0xCC: "DateTime"}


def load_json(path):
    """Bound both compressed and expanded inputs; captures are untrusted data."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("capture exceeds 16 MiB expanded budget")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def template_objects(templates, *, require_sizes=True):
    objects, sizes = {}, {}
    for template in templates:
        handle = template["handle"]
        if type(handle) is not int or not 0 < handle <= 0xFFF or handle in objects:
            raise ValueError("invalid or duplicate full Template instance handle")
        fields, names = [], set()
        for row in template["members"]:
            name = row["name"]
            if not NAME.fullmatch(name) or name in names:
                raise ValueError("invalid or duplicate Template member name")
            names.add(name)
            info, code, offset = row["info"], row["code"], row["offset"]
            if any(type(v) is not int for v in (info, code, offset)) or not (
                    0 <= info <= 0xFFFF and 0 <= code <= 0xFFFF and offset >= 0):
                raise ValueError("invalid member definition")
            fields.append(SimpleNamespace(TagName=name, DataType=row.get("typeName"),
                                          Bytes=struct.pack("<HHI", info, code, offset)))
        objects[handle] = SimpleNamespace(Type=handle, Name=template.get("name", ""), Fields=fields)
        size = template.get("byteSize")
        if size is not None:
            if type(size) is not int or not 0 < size <= MAX_BYTES:
                raise ValueError("invalid Template structure byte size")
            sizes[handle] = size
        elif require_sizes:
            raise ValueError("missing Template attribute 5 structure byte size")
    return objects, sizes


def timestamp_ns(value):
    """Exact signed Unix ns -> UTC; never pass through float/microsecond rounding."""
    if value == 0:
        return 0
    seconds, nanos = divmod(value, 1_000_000_000)
    stamp = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)
    text = stamp.strftime("%Y-%m-%dT%H:%M:%S")
    # Preserve the oracle/Dart millisecond spelling while retaining every ns.
    fraction=f"{nanos:09d}".rstrip("0").ljust(3,"0")
    return text + "." + fraction + "Z"


def _annotation_key(path):
    return re.sub(r"\[-?\d+\]", "[*]", path)


def decode_record(raw, handle, templates):
    objects, sizes = template_objects(templates)
    if handle not in objects or len(raw) != sizes[handle]:
        raise ValueError("record length differs from Template structure size")
    return decode(raw, 0, member_table(objects[handle]), objects, sizes[handle],
                  template_sizes=sizes, strict=True, native_times=True)


def replay_s0(capture):
    """Historical diagnostic only: S0 omitted structure sizes and a manifest.

    This reproduces the measured bytes, including native time units. It cannot
    establish canonical discovery or strict layout/array-bound acceptance.
    """
    if capture.get("schema") != "fraktal.ab.s0-raw-capture":
        raise ValueError("not an S0 capture")
    templates = [dict(value, name=name) for name, value in capture["templates"].items()]
    objects, _ = template_objects(templates, require_sizes=False)
    symbol = next(s for s in capture["symbols"] if s["TagName"] == capture["tag"])
    raw = bytes.fromhex(capture["rawHex"])
    if len(raw) != capture["recordBytes"]:
        raise ValueError("S0 capture record length mismatch")
    return decode(raw, 0, member_table(objects[symbol["DataTypeValue"]]), objects,
                  len(raw), native_times=True)


def snapshot(capture):
    """Project only PLC-published structure, types and annotations, without derivations.

    annotations is {canonical/path: {logicalType?, lowerBound?, elementCount?}}.
    Array member names use [*] only for an ancestor array. Every physical array
    requires a logical extent. No fallback assumes that a Logix zero is Core zero.
    """
    if capture.get("schema") != SCHEMA or capture.get("schemaVersion") != 1:
        raise ValueError("unsupported canonical capture schema")
    manifest = capture["manifest"]
    if manifest.get("schemaMajor") != 6 or manifest.get("valid") is not True \
            or manifest.get("truncated") is not False:
        raise ValueError("unsupported, invalid or truncated canonical manifest")
    minor = manifest.get('schemaMinor', 0)
    if type(minor) is not int or minor not in (0, 1, 2, 3, 4, 5, 6, 7, 8):
        raise ValueError('unsupported canonical manifest minor version')
    if minor<2 and any(key in manifest for key in ('bindings','fragmentRevision')):
        raise ValueError('record bindings require manifest V6.2')
    if minor<5 and 'dataProducts' in manifest:raise ValueError('data products require manifest V6.5')
    if minor<6 and 'commandBindings' in manifest:raise ValueError('command bindings require V6.6')
    if minor<7 and 'readCoherenceBindings' in manifest:raise ValueError('read-coherence bindings require V6.7')
    token = tuple(coherence_token(manifest))
    if not isinstance(token[0], str) or not token[0] or type(token[1]) is not int:
        raise ValueError("invalid manifest coherence token")
    if capture.get("coherenceBefore") != list(token) or capture.get("coherenceAfter") != list(token):
        raise ValueError("manifest changed during acquisition")
    objects, sizes = template_objects(capture["templates"])
    annotations = manifest.get('annotations', {}) if minor>=4 else manifest['annotations']
    type_annotations, path_exceptions, used_pairs = {}, {}, set()
    if minor >= 4:
        from fraktal_ab_canonical_manifest import type_tables
        if 'annotations' in manifest:
            raise ValueError('V6.4 cannot mix path and type annotations')
        type_annotations, path_exceptions = type_tables(manifest['typeAnnotations'], manifest['pathExceptions'])
    used, values, types = set(), {}, {}
    symbols = {}
    for symbol in capture["symbols"]:
        name = symbol["name"]
        if not NAME.fullmatch(name) or name in symbols:
            raise ValueError("invalid or duplicate controller Symbol")
        symbols[name] = symbol
    records = {}
    for record in capture["records"]:
        if record["tag"] in records:
            raise ValueError("duplicate tag sample")
        records[record["tag"]] = record
    commands=[]
    if minor>=6:
        from fraktal_ab_command_binding import bindings as validate_commands
        commands=validate_commands(manifest.get('commandBindings'))
        from fraktal_ab_command_binding import operations as validate_operations
        validate_operations(manifest.get('commandOperations'))
        if {r['RequestSymbol'] for r in manifest.get('services',[])}&set(records):
            raise ValueError('staged service/request values are forbidden in persisted cyclic captures')
        if {r['PayloadSymbol'] for r in commands}&set(records):
            raise ValueError('command-only payload values are forbidden in persisted cyclic captures')
        if {r['ResponseSymbol'] for r in commands}&set(records):
            raise ValueError('on-demand command replies are not cyclic records')
    if minor<8 and 'readServices' in manifest:raise ValueError('read services require V6.8')
    roots = []
    for name, symbol in symbols.items():
        if symbol.get("arrayRank", 0) != 0:
            continue
        udt = objects.get(symbol.get("handle"))
        if udt and any(r["name"] == "Status" and r["struct"] and not r["array"]
                       for r in member_table(udt)):
            roots.append(name)
    if not roots:
        raise ValueError("no controller-scope module with a top-level Status")
    decoded_roots, schema_rows = {}, {}
    root_symbols = {root:root for root in roots}
    for root in roots:
        handle = symbols[root]['handle']
        if root not in records:
            raise ValueError(f'{root}: discovered root has no acquired bytes')
        value = decode_record(bytes.fromhex(records[root]['rawHex']),handle,capture['templates'])
        identity = value.get('Status',{}).get('Name',{})
        if not isinstance(identity,dict) or not identity.get('string') \
                or bytes.fromhex(identity['bytes']).decode('utf-8') != root:
            raise ValueError(f'{root}: root browse name differs from Status.Name')
        if value['Status'].get('ModuleType') != 1:
            raise ValueError(f'{root}: root is not a Unit')
        decoded_roots[root] = value

    product_sources=set()
    if minor>=5:
        from fraktal_ab_canonical_manifest import data_products
        for product in data_products(manifest.get('dataProducts')):
            source,root=product['SourceSymbol'],product['CanonicalRoot']
            if source in roots or any(root==old or root.startswith(old+'/') or old.startswith(root+'/') for old in roots):
                raise ValueError('data product collides with a module root')
            symbol=symbols.get(source)
            if not symbol or symbol.get('arrayRank',0) or source not in records or symbol.get('handle') not in objects:
                raise ValueError('data product Symbol/sample unavailable')
            handle=symbol['handle']
            if is_string(member_table(objects[handle])) is not None:
                raise ValueError('data product must be a structured record')
            decoded_roots[root]=decode_record(bytes.fromhex(records[source]['rawHex']),handle,capture['templates'])
            root_symbols[root]=source;product_sources.add(source)

    if minor>=7:
        from fraktal_ab_read_coherence import validate_rows
        validate_rows(manifest.get('readCoherenceBindings'),expected_prefixes=set(roots)|set(decoded_roots))
        for binding in manifest['readCoherenceBindings']:
            symbol=symbols.get(binding['RevisionSymbol'])
            if not symbol or symbol.get('atomic')!=0xC4 or symbol.get('arrayRank',0):
                raise ValueError('read-coherence revision Symbol is not a DINT scalar')

    if minor>=8:
        from fraktal_ab_config_read_view import validate_descriptors
        for descriptor in validate_descriptors(manifest.get('readServices')):
            if descriptor['RootSymbol'] not in roots or descriptor['CanonicalRoot'] not in decoded_roots \
                    or descriptor['CanonicalRoot'] in roots:
                raise ValueError('read-service root/product is not published')
            view=decoded_roots[descriptor['CanonicalRoot']]
            identity=view.get('RootIdentity',{})
            if view.get('SchemaVersion')!=1 or not identity.get('string') \
                    or bytes.fromhex(identity['bytes']).decode('utf-8')!=descriptor['RootSymbol']:
                raise ValueError('read-service view version/identity differs')
    fragments=[]
    if minor>=2:
        bindings=manifest.get('bindings')
        if not isinstance(bindings,list) or not (0 if minor>=4 else 1)<=len(bindings)<=1024:
            raise ValueError('invalid canonical record bindings')
        sources=set()
        for binding in bindings:
            if not isinstance(binding,dict) or set(binding)!={'SourceSymbol','TargetRoot'}:
                raise ValueError('invalid canonical record binding')
            source,target=binding['SourceSymbol'],binding['TargetRoot']
            if not isinstance(source,str) or not isinstance(target,str) or not NAME.fullmatch(source) \
                    or source in sources or source in roots or source in product_sources or target not in roots:
                raise ValueError('invalid canonical fragment source/root')
            sources.add(source)
            symbol=symbols.get(source)
            if not symbol or symbol.get('arrayRank',0) or source not in records or symbol.get('handle') not in objects:
                raise ValueError('canonical fragment symbol/sample unavailable')
            handle=symbol['handle']
            if is_string(member_table(objects[handle])) is not None:
                raise ValueError('canonical fragment must be a structured record')
            value=decode_record(bytes.fromhex(records[source]['rawHex']),handle,capture['templates'])
            fragments.append((target,handle,value))
        if set(records)!=set(roots)|sources|product_sources:raise ValueError('unbound canonical tag sample')

    def schema_walk(path, handle, depth=0, *, fragment=False):
        if depth > 64:
            raise ValueError('canonical template tree exceeds depth budget')
        for row in member_table(objects[handle]):
            if fragment and row['name']=='Status':raise ValueError('fragment cannot define a module identity')
            key = path+'/'+row['name']
            if minor >= 4:
                pair = (objects[handle].Name, row['name'])
                annotation = dict(type_annotations.get(pair, {}))
                if pair in type_annotations:used_pairs.add(pair)
                if 'countMember' in annotation:
                    annotation['countPath'] = path+'/'+annotation.pop('countMember')
                if key in annotations and annotations[key] != annotation:
                    raise ValueError('conflicting type-scoped annotation: '+key)
                if annotation:annotations[key] = annotation
            if key in schema_rows:
                old=schema_rows[key]
                if not fragment or not old['struct'] or not row['struct'] or old['array']!=row['array'] \
                        or (row['array'] and old['info']!=row['info']) \
                        or is_string(member_table(objects[old['handle']])) is not None \
                        or is_string(member_table(objects[row['handle']])) is not None:
                    raise ValueError('fragment leaf collision or container shape mismatch: '+key)
            else:schema_rows[key] = row
            if row['struct'] and is_string(member_table(objects[row['handle']])) is None:
                schema_walk(key+('[*]' if row['array'] else ''), row['handle'], depth+1,fragment=fragment)

    for root,source in root_symbols.items():
        schema_walk(root, symbols[source]['handle'])
    native_rows=set(schema_rows)
    for target,handle,unused in fragments:schema_walk(target,handle,fragment=True)
    command_arguments={}
    if minor>=6:
        from fraktal_ab_command_binding import schema as command_schema
        for descriptor in commands:
            root=descriptor['RootSymbol']
            if root not in roots:raise ValueError('command binding root is not a discovered Unit')
            handle=command_schema(descriptor,symbols,objects,sizes,member_table,is_string)
            before=set(schema_rows)
            schema_walk(root+'/HmiRequest',handle,fragment=True)
            for path in set(schema_rows)-before:
                row=schema_rows[path]
                width=is_string(member_table(objects[row['handle']])) if row['struct'] else None
                command_arguments[path]=dict(readRole='CommandOnly',
                    nativeType='String' if width is not None else NATIVE_TYPES[row['atomic']],
                    **({'byteCapacity':width} if width is not None else {}))
    if minor >= 4:
        by_name = {}
        for handle,template in objects.items():
            if not any(pair[0]==template.Name for pair in type_annotations):continue
            shape = (sizes[handle],member_table(template))
            if template.Name in by_name and by_name[template.Name] != shape:
                raise ValueError('ambiguous annotated Template name')
            by_name[template.Name] = shape
        if set(type_annotations) != used_pairs:
            raise ValueError('type annotations refer to absent Template members')
        for key, exception in path_exceptions.items():
            if key not in schema_rows:
                raise ValueError('path exception refers to an absent member')
            annotations.setdefault(key, {}).update(exception)
        if any(row['array'] and key not in annotations for key,row in schema_rows.items()):
            raise ValueError('physical array lacks a type-scoped logical extent')
    if set(annotations)-set(schema_rows):
        raise ValueError('manifest contains annotations for paths absent from acquired roots')

    allowed_logical = {"DURATION": (0xC4,), "ENUM": (0xC4,), "BOOL": (0xC1,),
                       "TIMESTAMP": (0xCC,), "BITSTRING32": (0xD3, 0xC4)}
    if minor>=3:allowed_logical['UINT16']=(0xC4,)
    for key, annotation in annotations.items():
        row = schema_rows[key]
        allowed_keys = {'logicalType','lowerBound','elementCount','effectiveAccess'} | ({'countPath','indices'} if minor else set())
        if not isinstance(annotation,dict) or set(annotation)-allowed_keys:
            raise ValueError(f'{key}: unsupported annotation')
        if 'effectiveAccess' in annotation and annotation['effectiveAccess'] not in ('Read Only','Read/Write'):
            raise ValueError(f'{key}: invalid published effective access')
        logical = annotation.get('logicalType')
        permitted = (0xC1,0xD3) if row['array'] and logical == 'BOOL' else allowed_logical.get(logical,())
        if logical is not None and row['atomic'] not in permitted:
            raise ValueError(f'{key}: logical/native type mismatch')
        if row['array']:
            lower, extent = annotation.get('lowerBound'), annotation.get('elementCount')
            if type(lower) is not int or type(extent) is not int or not 0 < extent <= MAX_LEAVES:
                raise ValueError(f'{key}: array lacks explicit logical bound/count')
            selection, count_path = annotation.get('indices'), annotation.get('countPath')
            if selection is not None and (not isinstance(selection,list) or
                    any(type(i) is not int or not 0 <= i < extent for i in selection) or selection != sorted(set(selection))):
                raise ValueError(f'{key}: invalid array index selection')
            if count_path is not None:
                target = schema_rows.get(count_path) if isinstance(count_path,str) else None
                if selection is not None or target is None or target['array'] or target['struct'] \
                        or target['atomic'] not in (0xC2,0xC3,0xC4,0xC5,0xC6,0xC7,0xC8,0xC9) \
                        or (('[*]' in count_path or count_path not in native_rows) if minor<4 else
                            count_path.rsplit('/',1)[0] != key.rsplit('/',1)[0]) \
                        or count_path.split('/')[0] != key.split('/')[0]:
                    raise ValueError(f'{key}: count reference is not a published same-root integer scalar')
        elif any(k in annotation for k in ('lowerBound','elementCount','countPath','indices')):
            raise ValueError(f'{key}: array annotation on scalar')

    # A logical sibling can be in the native record while its array is in a
    # bound metadata fragment. Schema validation above proves disjoint leaves
    # and matching containers before we assemble their count lookup view.
    count_roots = deepcopy(decoded_roots) if minor>=4 else None
    def merge_count_view(target, source):
        if isinstance(target,dict) and isinstance(source,dict):
            for key,value in source.items():
                if key in target:merge_count_view(target[key],value)
                else:target[key]=deepcopy(value)
        elif isinstance(target,list) and isinstance(source,list) and len(target)==len(source):
            for left,right in zip(target,source):merge_count_view(left,right)
        else:
            raise ValueError('fragment count view has colliding leaves or mismatched containers')
    if minor>=4:
        for target,handle,value in fragments:merge_count_view(count_roots[target],value)

    def array_indices(path, annotation):
        extent = annotation['elementCount']
        count_path = annotation.get('countPath')
        if count_path is not None:
            if minor>=4:
                concrete = path.rsplit('/',1)[0]+'/'+count_path.rsplit('/',1)[1]
                owner = next(r for r in count_roots if concrete.startswith(r+'/'))
                value, prefix = count_roots[owner], owner
                for segment in concrete[len(owner)+1:].split('/'):
                    match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)(?:\[(-?\d+)\])?',segment)
                    name,index = match.groups()
                    prefix = prefix+'/'+name if prefix else name
                    value = value[name]
                    if index is not None:
                        value = value[int(index)-annotations[_annotation_key(prefix)]['lowerBound']]
                        prefix += '['+index+']'
            else:
                value = decoded_roots
                for segment in count_path.split('/'):
                    value = value[segment]
            if type(value) is not int or not 0 <= value <= extent:
                raise ValueError(f'{path}: live array count exceeds logical capacity')
            return range(value)
        return annotation.get('indices', range(extent))

    def scalar(path, value, code, annotation):
        logical = annotation.get("logicalType")
        if logical is not None and (logical not in allowed_logical or code not in allowed_logical[logical]):
            raise ValueError(f"{path}: logical/native type mismatch")
        data_type = NATIVE_TYPES.get(code)
        if data_type is None:
            raise ValueError(f"{path}: native type has no canonical V2 mapping: {hex(code)}")
        if code in (0xC5, 0xC9):
            value = str(value)
        elif code == 0xCC:
            value = timestamp_ns(value)
        if logical=='BITSTRING32':
            value=value & 0xffffffff
            data_type='UInt32'
        if logical=='UINT16':
            if type(value) is not int or not 0<=value<=65535:
                raise ValueError('logical UINT16 is outside its declared range')
            data_type='UInt16'
        put(path, value, data_type)

    def put(path, value, data_type):
        if path in values or len(values) >= MAX_LEAVES:
            raise ValueError("duplicate path or canonical leaf budget exceeded")
        values[path], types[path] = value, data_type

    def walk(path, value, row, depth=0):
        if depth > 64:
            raise ValueError("canonical tree exceeds depth budget")
        key = _annotation_key(path)
        annotation = annotations.get(key, {})
        if key in annotations:
            used.add(key)
        if not isinstance(annotation, dict) or set(annotation) - ({"logicalType", "lowerBound", "elementCount", "effectiveAccess"} | ({'countPath','indices'} if minor else set())):
            raise ValueError(f"{path}: unsupported annotation")
        if "effectiveAccess" in annotation and annotation["effectiveAccess"] not in ("Read Only", "Read/Write"):
            raise ValueError(f"{path}: invalid published effective access")
        if row["array"]:
            lower, count = annotation.get("lowerBound"), annotation.get("elementCount")
            if type(lower) is not int or type(count) is not int or not 0 < count <= MAX_LEAVES:
                raise ValueError(f"{path}: array lacks explicit logical bound/count")
            code = row["atomic"]
            selected = array_indices(path, annotation)
            if annotation.get("logicalType") == "BOOL" and code in (0xD3, 0xC1):
                if (code == 0xD3 and (len(value) < (count+31)//32 if minor else len(value) != (count+31)//32)) \
                        or (code == 0xC1 and (row['info'] < count if minor else row["info"] != count)):
                    raise ValueError(f"{path}: logical BOOL extent differs from physical storage")
                for i in selected:
                    bit = bool(value[i // 32] >> (i % 32) & 1) if code == 0xD3 else i in value
                    put(f"{path}[{i + lower}]", bit, "Boolean")
                return
            if (count > len(value) if minor else count != len(value)):
                raise ValueError(f"{path}: logical array count differs from Template extent")
            if code == 0xC1:
                raise ValueError(f"{path}: packed BOOL array requires logical BOOL annotation")
            for i in selected:
                item = value[i]
                # The element inherits its member's type annotation, not its bounds.
                item_path = f"{path}[{i + lower}]"
                if row["struct"]:
                    walk_struct(item_path, item, row["handle"], depth + 1)
                else:
                    scalar(item_path, item, code, annotation)
        elif "lowerBound" in annotation or "elementCount" in annotation:
            raise ValueError(f"{path}: array annotation on scalar")
        elif row["struct"]:
            if set(annotation) - {"effectiveAccess"}:
                raise ValueError(f"{path}: logical type on a structure")
            walk_struct(path, value, row["handle"], depth + 1)
        else:
            scalar(path, value, row["atomic"], annotation)

    def walk_struct(path, value, handle, depth):
        rows = member_table(objects[handle])
        if is_string(rows) is not None:
            put(path, bytes.fromhex(value["bytes"]).decode("utf-8"), "String")
            return
        if any(row["name"] == "Status" and row["struct"] for row in rows):
            status = value.get("Status", {})
            identity = status.get("Name", {})
            if not isinstance(identity, dict) or identity.get("string") is not True \
                    or bytes.fromhex(identity["bytes"]).decode("utf-8") != path.replace("/", ".") \
                    or status.get("ModuleType") not in (1, 2, 3):
                raise ValueError(f"{path}: module identity/type differs from its canonical browse path")
        for row in rows:
            if row["name"] in value:
                walk(f"{path}/{row['name']}", value[row["name"]], row, depth)

    for root,source in root_symbols.items():
        walk_struct(root, decoded_roots[root], symbols[source]['handle'], 0)
    for target,handle,value in fragments:walk_struct(target,value,handle,0)
    if not minor and set(annotations) != used:
        raise ValueError("manifest contains annotations for paths absent from acquired roots")
    return dict(schema=SNAPSHOT, schemaVersion=1, values=values, types=types,
                nodeCount=len(values), moduleCount=sum(p.endswith("/Status/Name") for p in values),
                contentHash=token[0], configRevision=token[1], truncated=False,
                dataValues={p: dict(value=v, type=types[p], status=0) for p, v in values.items()},
                **(dict(commandBindings=commands,commandArguments=command_arguments) if minor>=6 else {}),
                **(dict(readCoherenceBindings=manifest['readCoherenceBindings']) if minor>=7 else {}),
                **(dict(readServices=manifest['readServices']) if minor>=8 else {}))


def template_byte_size(comm, handle):
    """Read class 0x6C attribute 5, per Rockwell 1756-PM020I pp. 44-49.

    pylogix returns its connected reply including the 46-byte transport prefix.
    Validate the service, count, attribute ID and per-attribute status before use.
    """
    status, packet = comm.conn.send(comm._cip_message(0x03, 0x6C, handle, [5]))
    if status != 0 or packet is None or len(packet) != 60:
        raise ValueError("Template structure-size attribute read failed")
    service, reserved, general, extended, count, attribute, result, size = struct.unpack(
        "<BBBBHHHI", packet[46:])
    if (service, reserved, general, extended, count, attribute, result) != (0x83, 0, 0, 0, 1, 5, 0) \
            or not 0 < size <= MAX_BYTES:
        raise ValueError("invalid Template structure-size attribute reply")
    return size


def template_structure_handle(comm,handle):
    """Template attribute 1, not the instance ID; never read payload bytes.

    Rockwell 1756-PM020I pp. 12, 52-53 defines this write-type parameter.
    """
    status,packet=comm.conn.send(comm._cip_message(0x03,0x6C,handle,[1]))
    if status!=0 or packet is None or len(packet)!=58:
        raise ValueError('Template structure-handle attribute read failed')
    fields=struct.unpack('<BBBBHHHH',packet[46:])
    if fields[:7]!=(0x83,0,0,0,1,1,0):raise ValueError('invalid Template structure-handle reply')
    return fields[7]


def coherence_token(manifest):
    token=[manifest.get('contentHash'),manifest.get('configRevision')]
    if manifest.get('schemaMinor',0)>=2:
        revision=manifest.get('fragmentRevision')
        if type(revision) is not int or not 0<=revision<1<<31:raise ValueError('invalid fragment data revision')
        token.append(revision)
    return token


def read_document(comm, manifest_reader=None, *, expect_serial):
    """Read-only acquisition with the standard physical V6 loader by default.

    manifest_reader(comm, symbols, templates) reads/normalizes the PLC manifest.
    It is called before and after the roots to validate configuration coherence.
    This does not promise scan-atomicity across tags; a stable paired-state fixture
    or PLC snapshot generation is still required for live value equivalence.
    """
    if manifest_reader is None:
        from fraktal_ab_canonical_manifest import read_manifest
        manifest_reader = read_manifest
    identity = comm.GetDeviceProperties()
    if identity.Status != "Success" or identity.Value is None \
            or int(str(identity.Value.SerialNumber), 0) != int(expect_serial, 16):
        raise ValueError("controller serial guard failed")
    reply = comm.GetTagList(allTags=False)
    if reply.Status != "Success":
        raise ValueError("Symbol discovery failed")
    objects = discover_templates(comm)
    templates = [dict(handle=h, name=u.Name, byteSize=template_byte_size(comm, h),
                      members=member_table(u)) for h, u in objects.items()]
    symbols = [dict(name=t.TagName, handle=t.DataTypeValue, arrayRank=t.Array)
               for t in reply.Value if t.Struct and NAME.fullmatch(t.TagName)]
    before = deepcopy(manifest_reader(comm, symbols, templates))
    if before.get('schemaMinor',0)>=6:
        for binding in before['commandBindings']:
            name=binding['CommitSymbol']
            tags=[t for t in reply.Value if t.TagName==name]
            if len(tags)!=1 or tags[0].Struct or tags[0].Array or tags[0].DataTypeValue!=0xC4:
                raise ValueError('command commit Symbol is not a DINT scalar')
            symbols.append(dict(name=name,atomic=0xC4,arrayRank=0))
    if before.get('schemaMinor',0)>=7:
        for name in sorted({b['RevisionSymbol'] for b in before['readCoherenceBindings']}):
            matches=[t for t in reply.Value if t.TagName==name]
            if len(matches)!=1 or matches[0].Struct or matches[0].Array or matches[0].DataTypeValue!=0xC4:
                raise ValueError('read-coherence revision Symbol is not a DINT scalar')
            if name not in {s['name'] for s in symbols}:symbols.append(dict(name=name,atomic=0xC4,arrayRank=0))
    if before.get('schemaMinor',0)>=6:
        forbidden={b['PayloadSymbol'] for b in before['commandBindings']}|{s['RequestSymbol'] for s in before.get('services',[])}
        planned={s['name'] for s in symbols if s.get('handle') in objects and not s.get('arrayRank',0)
                 and any(r['name']=='Status' and r['struct'] for r in member_table(objects[s['handle']]))}
        planned|={b['SourceSymbol'] for b in before.get('bindings',[])}|{b['SourceSymbol'] for b in before.get('dataProducts',[])}
        if planned&forbidden:raise ValueError('cyclic read plan includes a command or service input')
        by_handle={t['handle']:t for t in templates}
        by_name={s['name']:s for s in symbols}
        for b in before['commandBindings']:
            handle=by_name[b['PayloadSymbol']]['handle']
            by_handle[handle]['structureHandle']=template_structure_handle(comm,handle)
    records = []
    for symbol in symbols:
        if symbol["arrayRank"] or not any(r["name"] == "Status" and r["struct"]
                                         for r in member_table(objects.get(symbol.get("handle"),SimpleNamespace(Fields=[])))):
            continue
        sample = comm.Read(symbol["name"])
        if sample.Status != "Success" or not isinstance(sample.Value, (bytes, bytearray)):
            raise ValueError("canonical root read failed")
        records.append(dict(tag=symbol["name"], rawHex=bytes(sample.Value).hex()))
    if before.get('schemaMinor',0)>=2:
        for binding in before['bindings']:
            source=binding['SourceSymbol']
            if source not in {s['name'] for s in symbols}:raise ValueError('canonical fragment Symbol unavailable')
            sample=comm.Read(source)
            if sample.Status!='Success' or not isinstance(sample.Value,(bytes,bytearray)):
                raise ValueError('canonical fragment read failed')
            records.append(dict(tag=source,rawHex=bytes(sample.Value).hex()))
    if before.get('schemaMinor',0)>=5:
        for product in before['dataProducts']:
            source=product['SourceSymbol']
            if source not in {s['name'] for s in symbols}:raise ValueError('data product Symbol unavailable')
            sample=comm.Read(source)
            if sample.Status!='Success' or not isinstance(sample.Value,(bytes,bytearray)):
                raise ValueError('data product read failed')
            records.append(dict(tag=source,rawHex=bytes(sample.Value).hex()))
    after = manifest_reader(comm, symbols, templates)
    capture = dict(schema=SCHEMA, schemaVersion=1, serial=expect_serial, readOnly=True,
                   templates=templates, symbols=symbols, records=records, manifest=before,
                   coherenceBefore=coherence_token(before), coherenceAfter=coherence_token(after))
    if before != after:
        raise ValueError("manifest changed during acquisition")
    return snapshot(capture), capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--s0-diagnostic", action="store_true")
    args = parser.parse_args()
    capture = load_json(args.capture)
    result = (dict(schema="fraktal.ab.s0-diagnostic-replay", canonicalAcceptance=False,
                   decoded=replay_s0(capture)) if args.s0_diagnostic else snapshot(capture))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(output=str(args.output), values=result.get("nodeCount"),
                         canonicalAcceptance=not args.s0_diagnostic)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
