"""Compare generated L5X with the SDK's first export, including actual values.

The existing construct inventory and SFC graph comparator own structural checks.
This adds ST/RLL executable content and every authored decorated initial value;
equal line counts alone cannot prove an imported program or nameplate survived.
No controller operations are performed.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
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


def alarm_metadata(root):
    """Authored native alarm configuration, including messages and identity.

    Inventory of tags/code is insufficient: dropping AlarmConditions leaves
    both unchanged. Compare all authored fields; SDK-added parameter defaults
    are permitted. New/missing conditions or definitions are never permitted.
    """
    result = {}
    owners = {'Controller', 'Program', 'Tag', 'AddOnInstructionDefinition',
              'DataTypeAlarmDefinition'}

    def scalar(name, value):
        if name == 'Expression':
            return re.sub(r'\s+', '', value).casefold()
        if value.lower() in ('true', 'false'):
            return value.lower()
        if re.fullmatch(r'-?\d+(?:\.\d+)?', value):
            return str(Decimal(value).normalize())
        return value

    def fields(node, path='', values=None):
        if values is None:
            values = {}
        identity = next((node.get(n) for n in ('Name', 'Lang', 'Type') if node.get(n)), '')
        path += '/' + node.tag + (':' + identity if identity else '')
        for name, value in node.attrib.items():
            key = path + '/@' + name
            if key in values:
                raise ValueError('duplicate native alarm metadata: ' + key)
            values[key] = scalar(name, value)
        if not len(node):
            value = node.text or ''
            if value.strip():
                values[path + '/#text'] = value
        for child in node:
            fields(child, path, values)
        return values

    def walk(node, path=''):
        if node.tag in owners:
            path += '/' + node.tag + ':' + node.get('Name', '')
        if (node.tag == 'Tag' and node.get('DataType') in ('ALARM_DIGITAL', 'ALARM_ANALOG')
                and node.find("Data[@Format='Alarm']") is None):
            # These native object tags acquire default configuration on import.
            # Keep the identity explicit, even when no parameter was authored.
            key = path + '/Data:Alarm'
            if key in result:
                raise ValueError('duplicate native alarm identity: ' + key)
            result[key] = {}
        if (node.tag in ('AlarmCondition', 'MemberAlarmDefinition')
                or node.tag == 'Data' and node.get('Format') == 'Alarm'):
            key = path + '/' + node.tag + ':' + node.get('Name', 'Alarm')
            if key in result:
                raise ValueError('duplicate native alarm identity: ' + key)
            result[key] = fields(node)
            return
        for child in node:
            walk(child, path)
    walk(root)
    return result


def alarm_differences(first, second):
    before, after = alarm_metadata(first), alarm_metadata(second)
    differences = []
    for key in sorted(set(before) | set(after)):
        if key not in before or key not in after:
            differences.append(key)
            continue
        differences += [key + field for field, value in before[key].items()
                        if after[key].get(field) != value]
    return len(before), differences


def compare(source: Path, exported: Path):
    shape, graph = inventory.compare(source, exported), sfc.compare(source, exported)
    first, second = ET.parse(source).getroot(), ET.parse(exported).getroot()
    code_a, code_b = executable(first), executable(second)
    data_a, data_b = initials(first), initials(second)
    code_diff = ['/'.join(k) for k in sorted(set(code_a) | set(code_b)) if code_a.get(k) != code_b.get(k)]
    data_diff = [k for k in sorted(data_a) if data_a[k] != data_b.get(k)]
    alarm_count, alarm_diff = alarm_differences(first, second)
    return dict(Schema='fraktal.ab.native-readback', SchemaVersion=1,
                Inventory=shape, SFC=graph, ExecutableBodies=len(code_a),
                ExecutableDifferences=code_diff, AuthoredInitialValues=len(data_a),
                InitialValueDifferences=data_diff,
                AuthoredAlarmRecords=alarm_count, AlarmDifferences=alarm_diff,
                Equivalent=shape['Equivalent'] and graph['Equivalent'] and not code_diff
                    and not data_diff and not alarm_diff)


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
