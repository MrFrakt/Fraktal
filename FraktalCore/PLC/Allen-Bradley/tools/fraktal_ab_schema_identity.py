"""The external surface of one generated image, and the WP6.6 schema-identity gate.

The generator collapse (S6 WP6.6) moves code and data inside the controller.
It must not move what a client can discover. This records that surface
offline, from the image itself rather than from the generator's own
description of it:

- every controller tag whose ExternalAccess is not `None`: its type,
  dimensions, access and its initial data, decoded to plain values;
- every data type and AOI those tags reach, member by member, with each
  member's type, dimension, access and visibility.

The canonical header's three derived hashes (`ContentHash`, `ConfigRevision`
and `LegacyContentHash`) are recorded apart from its data. They fold in
content the collapse removes by design, so the gate reports them and does not
compare them.

`compare(before, after, declared)` is the gate. It lists every difference
between two surfaces at the finest path it can name: a tag or type added or
removed, a tag attribute, a type member, or one leaf of a tag's data
(`Tag.Data.Member[3].Leaf`). Each must be covered by a declared change: a path
pattern, the change it permits (`removed`, `added` or `changed`) and the plan
item that makes it. A difference no declaration covers fails, and so does a
declaration that covers nothing, because a change nobody needs is a claim
nobody checked.

Station selection is process state (`FRAKTAL_AB_DECLARATION`), so recording
runs one declaration per process. `--seed` is the Studio export the image is
generated into; only its controller shell reaches the image. Contacts no
controller.
"""

from __future__ import annotations

import argparse
import fnmatch
import gzip
import hashlib
import json
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

SCHEMA = 'fraktal.ab.schema-identity'
SCHEMA_VERSION = 1
DERIVED_HASHES = ('ContentHash', 'ConfigRevision', 'LegacyContentHash')
ATOMIC = {'BOOL', 'SINT', 'INT', 'DINT', 'LINT', 'USINT', 'UINT', 'UDINT', 'ULINT',
          'REAL', 'LREAL', 'BIT', 'LDT', 'DT', 'TIME', 'LTIME', 'TIMER', 'COUNTER', 'CONTROL', 'STRING'}


CHANGES = ('removed', 'added', 'changed')


@dataclass(frozen=True)
class Declared:
    """One change the plan makes to the surface, over a family of paths."""

    pattern: str      # fnmatch over a difference path (see `differences`)
    change: str       # removed | added | changed
    reason: str       # the plan item that makes it

    def __post_init__(self):
        if self.change not in CHANGES:
            raise ValueError(f'unknown change {self.change!r}')


def _value(node: ET.Element):
    """Decorated data as plain JSON values: structures are objects, arrays lists."""
    tag = node.tag
    if tag in ('Structure', 'StructureMember'):
        return {child.get('Name'): _value(child) for child in node}
    if tag in ('Array', 'ArrayMember'):
        return [_value(child) for child in node]
    if tag == 'Element':
        if len(node):
            return _value(node[0]) if len(node) == 1 and node[0].tag == 'Structure' else [_value(c) for c in node]
        return node.get('Value')
    if tag in ('DataValue', 'DataValueMember'):
        return node.get('Value') if node.get('Value') is not None else (node.text or '')
    raise ValueError(f'unknown decorated element {tag}')


def _data(tag: ET.Element):
    for data in tag.findall('Data'):
        if data.get('Format') == 'Decorated':
            return _value(data[0]) if len(data) else None
    return None


def surface(l5x: Path) -> dict:
    """The published surface of the image at `l5x`."""
    root = ET.parse(l5x).getroot()
    controller = root.find('Controller')
    types = {}
    for definition in controller.iter('DataType'):
        types[definition.get('Name')] = dict(kind='udt', members=[
            {k: m.get(k) for k in ('Name', 'DataType', 'Dimension', 'ExternalAccess', 'Hidden', 'Target', 'BitNumber')
             if m.get(k) is not None}
            for m in definition.iter('Member')])
    for aoi in controller.iter('AddOnInstructionDefinition'):
        types[aoi.get('Name')] = dict(kind='aoi', members=[
            {k: p.get(k) for k in ('Name', 'DataType', 'Dimensions', 'Usage', 'ExternalAccess', 'Required', 'Visible')
             if p.get(k) is not None}
            for p in aoi.iter('Parameter')])
    tags, derived = {}, {}
    for tag in controller.find('Tags'):
        access = tag.get('ExternalAccess') or 'Read/Write'
        if access == 'None':
            continue
        data = _data(tag)
        if isinstance(data, dict) and all(name in data for name in DERIVED_HASHES):
            for name in DERIVED_HASHES:
                derived[f"{tag.get('Name')}.{name}"] = data.pop(name)
        tags[tag.get('Name')] = {k: v for k, v in dict(
            DataType=tag.get('DataType'), Dimensions=tag.get('Dimensions'), ExternalAccess=access,
            Constant=tag.get('Constant'), Data=data).items() if v is not None}
    reached, pending = {}, [t['DataType'] for t in tags.values()]
    while pending:
        name = pending.pop()
        if name in reached or name in ATOMIC or name not in types:
            continue
        reached[name] = types[name]
        pending.extend(m['DataType'] for m in types[name]['members'] if 'DataType' in m)
    return dict(tags=tags, types=dict(sorted(reached.items())), derivedHashes=derived)


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest().upper()


def summary(record: dict) -> dict:
    return dict(tags=len(record['tags']), types=len(record['types']),
                tagFingerprint=fingerprint(record['tags']), typeFingerprint=fingerprint(record['types']))


def _walk(before, after, path: str, out: list) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after), key=str):
            if key not in after:
                out.append((f'{path}.{key}', 'removed'))
            elif key not in before:
                out.append((f'{path}.{key}', 'added'))
            else:
                _walk(before[key], after[key], f'{path}.{key}', out)
    elif isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            if index >= len(after):
                out.append((f'{path}[{index}]', 'removed'))
            elif index >= len(before):
                out.append((f'{path}[{index}]', 'added'))
            else:
                _walk(before[index], after[index], f'{path}[{index}]', out)
    elif before != after:
        out.append((path, 'changed'))


def _members(definition: dict) -> dict:
    return {'@kind': definition['kind'], '@order': [m['Name'] for m in definition['members']],
            **{m['Name']: m for m in definition['members']}}


def differences(before: dict, after: dict) -> list[tuple[str, str]]:
    """(path, change) for every difference. A whole tag or type added or
    removed is one entry named by itself. Inside one present in both, a type is
    compared member by member (`Type.Member.Attribute`, with `Type.@order` for
    the member order) and a tag attribute by attribute, its data leaf by leaf
    (`Tag.Data.Member[3].Leaf`)."""
    out = []
    for section in ('tags', 'types'):
        old, new = before[section], after[section]
        for name in sorted(set(old) | set(new)):
            if name not in new:
                out.append((name, 'removed'))
            elif name not in old:
                out.append((name, 'added'))
            elif section == 'types':
                _walk(_members(old[name]), _members(new[name]), name, out)
            else:
                _walk(old[name], new[name], name, out)
    return out


def compare(before: dict, after: dict, declared=()) -> dict:
    """Every surface difference, and which declared change covers it."""
    used, uncovered, covered = set(), [], []
    for path, change in differences(before, after):
        match = next((d for d in declared if d.change == change and fnmatch.fnmatchcase(path, d.pattern)), None)
        if match is None:
            uncovered.append(dict(path=path, change=change))
        else:
            used.add(match)
            covered.append(dict(path=path, change=change, reason=match.reason))
    unused = [dict(pattern=d.pattern, change=d.change, reason=d.reason) for d in declared if d not in used]
    return dict(passed=not uncovered and not unused, uncovered=uncovered, covered=covered,
                unusedDeclarations=unused,
                derivedHashes=dict(before=before['derivedHashes'], after=after['derivedHashes']))


def generate_surface(declaration: str, seed: Path) -> dict:
    """Generate the selected declaration's image into `seed` and record its surface."""
    os.environ['FRAKTAL_AB_DECLARATION'] = declaration
    import fraktal_ab_generate as gen
    import fraktal_ab_station as station
    app = station.application()
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / 'app.L5X'
        gen.generate(app, seed, out)
        record = surface(out)
    return dict(schema=SCHEMA, schemaVersion=SCHEMA_VERSION, declaration=declaration, application=app.name, **record)


def write(record: dict, path: Path) -> None:
    payload = json.dumps(record, sort_keys=True, indent=1).encode('utf-8') + b'\n'
    with path.open('xb') as stream:
        stream.write(gzip.compress(payload, mtime=0) if path.suffix == '.gz' else payload)


def read(path: Path) -> dict:
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--declaration', required=True)
    parser.add_argument('--seed', type=Path, required=True, help='the Studio export to generate into')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--record', type=Path, help='write this declaration\'s surface (refuses to overwrite)')
    action.add_argument('--check', type=Path, help='compare this declaration\'s surface with a recorded one')
    parser.add_argument('--declared', type=Path, help='JSON list of {pattern, change, reason}')
    args = parser.parse_args(argv)
    record = generate_surface(args.declaration, args.seed)
    if args.record:
        write(record, args.record)
        print(json.dumps(summary(record)))
        return 0
    declared = [Declared(**d) for d in json.loads(args.declared.read_text(encoding='utf-8'))] \
        if args.declared else []
    result = compare(read(args.check), record, declared)
    print(json.dumps(dict(summary=summary(record), **result), indent=1))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
