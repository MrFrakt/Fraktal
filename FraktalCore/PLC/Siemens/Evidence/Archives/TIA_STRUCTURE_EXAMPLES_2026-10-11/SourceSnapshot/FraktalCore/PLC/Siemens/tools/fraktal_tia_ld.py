"""Read native Siemens Ladder networks and prove generated/exported parity.

IDs and FlgNet version numbers are serialization details. Operands, typed call
pins, return slots, contacts, coils, wiring and network order are retained.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def local(tag):
    return tag.rsplit('}', 1)[-1]


def child(node, name):
    return next(c for c in node if local(c.tag) == name)


def operand(node):
    scope = node.get('Scope')
    if scope == 'LocalVariable':
        return '#' + '.'.join(c.get('Name') for c in node.iter() if local(c.tag) == 'Component')
    if scope == 'LiteralConstant':
        return child(child(node, 'Constant'), 'ConstantValue').text
    raise ValueError('Unsupported access scope: ' + str(scope))


def network(net):
    parts = child(net, 'Parts')
    nodes = {p.get('UId'): p for p in parts}
    if len(nodes) != len(parts):
        raise ValueError('Duplicate part UID')
    wires = list(child(net, 'Wires'))
    accesses = {uid: operand(p) for uid, p in nodes.items() if local(p.tag) == 'Access'}
    labels = {uid: ('operand', value) for uid, value in accesses.items()}
    calls = []
    for uid, p in nodes.items():
        kind = local(p.tag)
        if kind == 'Call':
            info = child(p, 'CallInfo')
            labels[uid] = ('call', info.get('Name'))
            pins = [(q.get('Name'), q.get('Section'), q.get('Type').replace('"', '').lower()) for q in info]
            calls.append({'name': info.get('Name'), 'kind': info.get('BlockType'), 'pins': sorted(pins)})
        elif kind == 'Part':
            if p.get('Name') not in ('Contact', 'Coil'):
                raise ValueError('Unsupported Ladder part: ' + str(p.get('Name')))
            operands = []
            for w in wires:
                if any(local(c.tag) == 'NameCon' and c.get('UId') == uid and c.get('Name') == 'operand' for c in w):
                    operands.extend(accesses[c.get('UId')] for c in w if local(c.tag) == 'IdentCon')
            if len(operands) != 1:
                raise ValueError('Contact/coil needs exactly one operand')
            labels[uid] = (p.get('Name'), operands[0])
        elif kind != 'Access':
            raise ValueError('Unsupported part node: ' + kind)
    edges = []
    for w in wires:
        endpoints = []
        for c in w:
            kind = local(c.tag)
            if kind == 'Powerrail': endpoints.append(('powerrail',))
            elif kind in ('NameCon', 'IdentCon'):
                if c.get('UId') not in labels: raise ValueError('Wire points to absent node')
                endpoints.append((*labels[c.get('UId')], c.get('Name', '')))
            else: raise ValueError('Unsupported wire endpoint: ' + kind)
        edges.append(sorted(endpoints))
    return {'calls': calls, 'nodes': sorted(labels.values()), 'wires': sorted(edges)}


def dump(text):
    root = ET.fromstring(text.lstrip('\ufeff'))
    nets = [network(n) for n in root.iter() if local(n.tag) == 'FlgNet']
    if not nets: raise ValueError('No Ladder networks found')
    return {'networks': nets, 'network_count': len(nets),
            'call_count': sum(len(n['calls']) for n in nets)}


def parity(generated, exported):
    expected = dump(Path(generated).read_text('utf-8-sig'))
    actual = dump(Path(exported).read_text('utf-8-sig'))
    if expected != actual:
        different = [i + 1 for i, (a, b) in enumerate(zip(expected['networks'], actual['networks'])) if a != b]
        raise ValueError('Ladder graph changed: networks ' + str(different) +
                         ', counts ' + str((expected['network_count'], actual['network_count'])))
    return {'networks': actual['network_count'], 'calls': actual['call_count']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('generated', type=Path)
    parser.add_argument('exported', type=Path, nargs='?')
    args = parser.parse_args()
    print(json.dumps(parity(args.generated, args.exported) if args.exported else
                     dump(args.generated.read_text('utf-8-sig')), indent=2))
