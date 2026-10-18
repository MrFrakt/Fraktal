"""Compare generated L5X with the SDK's first export, including actual values.

The existing construct inventory and SFC graph comparator own structural checks.
This adds ST/RLL executable content and every authored decorated initial value;
equal line counts alone cannot prove an imported program or nameplate survived.
No controller operations are performed.
"""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_l5x_inventory as inventory
import fraktal_ab_sfc_roundtrip_compare as sfc


def normalized(text):
    # Keep quoted operands intact. Ignore only presentation whitespace/comments.
    pattern = r"\(\*.*?\*\)|//[^\n]*(?:\n|$)|'(?:\$[^\r\n]|''|[^'])*'|\s+"
    return re.sub(pattern, lambda m: m.group() if m.group().startswith("'") else '',
                  text, flags=re.DOTALL)


def executable(root):
    result = {}
    for owner in [*root.findall('.//Controller/AddOnInstructionDefinitions/AddOnInstructionDefinition'),
                  *root.findall('.//Controller/Programs/Program')]:
        for routine in owner.findall('Routines/Routine'):
            key = (owner.get('Name'), routine.get('Name'))
            if routine.get('Type') == 'ST':
                result[key] = normalized('\n'.join(n.text or '' for n in routine.findall('STContent/Line')))
            elif routine.get('Type') == 'RLL':
                result[key] = tuple(normalized(n.text or '') for n in routine.findall('RLLContent/Rung/Text'))
    return result


def ascii_payload(value):
    """Logix dollar-escaped ASCII initializers, independent of spelling."""
    if not value or value == "''":
        return b''
    if not (value.startswith("'") and value.endswith("'")):
        raise ValueError('invalid ASCII initializer')
    text, result, index = value[1:-1], bytearray(), 0
    while index < len(text):
        ch = text[index]
        if ch == '$':
            index += 1
            if index >= len(text):
                raise ValueError('truncated ASCII escape')
            if text[index] in ("'", '$'):
                result.append(ord(text[index]))
            elif index + 1 < len(text) and re.fullmatch('[0-9A-Fa-f]{2}', text[index:index+2]):
                result.append(int(text[index:index+2],16))
                index += 1
            else:
                raise ValueError('unrecognized ASCII escape')
        else:
            result.append(ord(ch))
        index += 1
    return bytes(result)


def initials(root):
    result = {}
    def walk(node, path):
        suffix = node.get('Name') or node.get('Index')
        if suffix:
            path += '/' + suffix
        if 'Value' in node.attrib:
            result[path] = ascii_payload(node.get('Value')) if node.get('Radix') == 'ASCII' else node.get('Value')
        elif node.tag in ('DataValueMember', 'DataValue') and node.get('Radix') == 'ASCII':
            value = ''.join(node.itertext()).strip()
            result[path] = ascii_payload(value)
        for child in node:
            walk(child, path)
    for owner in [root.find('Controller'), *root.findall('.//Controller/Programs/Program')]:
        if owner is None:
            continue
        for tag in owner.findall('Tags/Tag'):
            data = tag.find("Data[@Format='Decorated']")
            if data is not None:
                walk(data, owner.get('Name', '') + '/' + tag.get('Name', ''))
    return result


def compare(source: Path, exported: Path):
    shape, graph = inventory.compare(source, exported), sfc.compare(source, exported)
    first, second = ET.parse(source).getroot(), ET.parse(exported).getroot()
    code_a, code_b = executable(first), executable(second)
    data_a, data_b = initials(first), initials(second)
    code_diff = ['/'.join(k) for k in sorted(set(code_a) | set(code_b)) if code_a.get(k) != code_b.get(k)]
    data_diff = [k for k in sorted(data_a) if data_a[k] != data_b.get(k)]
    return dict(Schema='fraktal.ab.native-readback', SchemaVersion=1,
                Inventory=shape, SFC=graph, ExecutableBodies=len(code_a),
                ExecutableDifferences=code_diff, AuthoredInitialValues=len(data_a),
                InitialValueDifferences=data_diff,
                Equivalent=shape['Equivalent'] and graph['Equivalent'] and not code_diff and not data_diff)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('exported', type=Path)
    args = parser.parse_args(argv)
    report = compare(args.source, args.exported)
    print(json.dumps(report, indent=2))
    return 0 if report['Equivalent'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
