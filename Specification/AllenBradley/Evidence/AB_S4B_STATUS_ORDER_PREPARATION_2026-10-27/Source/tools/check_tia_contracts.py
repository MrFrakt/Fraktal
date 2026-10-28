#!/usr/bin/env python3
"""Check the implemented S7-1500 candidate ABI against its immutable V1 baseline.

Core DUTs and the existing binding remain authoritative. This read-only gate
compares their derived layout, enum ordinals, capacities and HMI type projection
with the baseline; it never regenerates the baseline during a check. This is a
partial R3 gate, not a release or qualification of unimplemented profiles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TIA = ROOT / 'FraktalCore/PLC/Siemens'
sys.path.insert(0, str(TIA / 'tools'))
from fraktal_tia_binding import Catalog, native_scalar, split_type
from fraktal_tia_sequence_view import published_types
import tia_lint

BASELINE = TIA / 'Contracts/TIA_FROZEN_CONTRACTS_V1.json'
PART = ROOT / 'Specification/Fraktal_TIA_Part_IV.md'
ADAPTER = ROOT / 'FraktalCore/HMI/packages/fraktal_opcua_client/lib/src/webapi_session_client.dart'
GROUPS = {
    'module': ('ST_ModuleStatus', 'ST_ModuleTiming', 'ST_Diagnostic', 'ST_StateFlag'),
    'mailbox': ('ST_HmiRequest', 'ST_HmiResponse'),
    'configuration': ('ST_ConfigEntry', 'ST_ConfigPage', 'ST_ModelId',
                      'ST_ConfigSetInfo', 'ST_ConfigPersistStatus'),
    'sequence': ('ST_SequenceStepDef', 'ST_SequenceStep', 'ST_SequenceCursor',
                 'ST_SequenceAnnotation', 'ST_StepRecord', 'ST_CondRecord',
                 'ST_StepTiming', 'ST_CycleSummary'),
    'access': ('ST_AccessPolicy', 'ST_ModePolicy'),
    'operator': ('ST_CommandInfo', 'ST_ReleaseReport', 'ST_DecisionRequest'),
    'events': ('ST_AlarmEvent', 'ST_PartContext'),
}
HEADINGS = ('TIA §3.8 Configuration, providers, and value-type binding',
            'TIA §3.13 HMI projection and snapshot coherence',
            'TIA candidate contract baseline, version 1')


def normalized(value):
    return re.sub(r'\s+|"', '', value).casefold()


def access_flags(attributes):
    return {name: not re.search(name + r"\s*:=\s*'False'", attributes, re.I)
            for name in ('ExternalAccessible', 'ExternalVisible', 'ExternalWritable')}


def adapter_types(text):
    """Read the adapter's deliberately simple, exhaustive datatype switch.

    Refuse an unfamiliar expression instead of silently freezing a partial map.
    Behavioral codecs (notably LDT and wide integers) still have Dart tests.
    """
    body = re.search(r'String get opcUaType\s*=>\s*switch\s*\(datatype\)\s*\{(.*?)\};', text, re.S)
    if not body:
        raise ValueError('HMI datatype switch not found')
    result = {}
    for arm in body[1].split(','):
        arm = arm.strip()
        if not arm or arm == '_ => datatype':
            continue
        match = re.fullmatch(r"((?:'[a-z0-9]+'\s*(?:\|\|\s*)?)+)\s*=>\s*'([A-Za-z0-9]+)'", arm)
        if not match:
            raise ValueError('unrecognized HMI datatype arm: ' + arm)
        for name in re.findall(r"'([^']+)'", match[1]):
            if name in result:
                raise ValueError('duplicate HMI datatype: ' + name)
            result[name] = match[2]
    if not result:
        raise ValueError('empty HMI datatype switch')
    return result


def collect(catalog=None, adapter=None):
    catalog = catalog or Catalog.read()
    types = catalog.resolve([name for group in GROUPS.values() for name in group])
    enums = {'E_HmiRequestKind', 'E_StepResult'}
    capacities = set()
    for fields in types.values():
        for field in fields:
            _, _, scalar, _ = split_type(field['core_type'])
            if scalar in catalog.enums:
                enums.add(scalar)
            capacities.update(re.findall(r'\bMAX_\w+\b', field['core_type']))
    # No table is allocated: sentinel dimensions expose the owning generator's
    # consumed-size layout, including the main-line cursor at index zero.
    view = published_types(101, 102, 103)
    view = {name: value.replace('101', '$steps').replace('102', '$branches')
            .replace('103', '$annotations') for name, value in view.items()}
    scalars = ('BOOL', 'BYTE', 'WORD', 'DWORD', 'SINT', 'USINT', 'INT', 'UINT',
               'DINT', 'UDINT', 'LINT', 'ULINT', 'REAL', 'LREAL', 'TIME', 'DT',
               'STRING(254)', 'STRING(255)', 'STRING(480)')
    return {
        'groups': {name: list(records) for name, records in GROUPS.items()},
        'typeMap': {name: native_scalar(name, catalog.enums) for name in scalars},
        'records': types,
        'enums': {name: catalog.enums[name] for name in sorted(enums)},
        'capacities': {name: catalog.capacities[name] for name in sorted(capacities)},
        'sequencePublication': view,
        'webApiTypes': adapter_types(ADAPTER.read_text(encoding='utf-8') if adapter is None else adapter),
    }


def differences(expected, actual, path='contract'):
    """Exact V1 equality: additions also require an explicit versioned review."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        result = []
        for key in sorted(expected.keys() | actual.keys()):
            location = path + '.' + key
            if key not in actual:
                result.append(location + ': missing')
            elif key not in expected:
                result.append(location + ': addition requires a versioned contract review')
            else:
                result.extend(differences(expected[key], actual[key], location))
        return result
    if isinstance(expected, list) and isinstance(actual, list):
        result = []
        if len(expected) != len(actual):
            result.append(path + ': item count differs from V1 baseline')
        for index, (left, right) in enumerate(zip(expected, actual)):
            result.extend(differences(left, right, path + '[' + str(index) + ']'))
        return result
    if type(expected) is not type(actual) or expected != actual:
        return [path + ': differs from V1 baseline']
    return []


def audit(baseline, current, part, digest):
    findings = []
    if baseline.get('schema') != 'fraktal.tia.frozen-contracts' or baseline.get('schemaVersion') != 1:
        findings.append('unsupported frozen-contract schema/version')
    if baseline.get('profile') != 'reference-1500-implemented-subset':
        findings.append('baseline must name the implemented S7-1500 subset')
    marker = '<!-- TIA-CONTRACTS-V1 sha256:' + digest + ' -->'
    if part.count('<!-- TIA-CONTRACTS-V1 ') != 1 or part.count(marker) != 1:
        findings.append('Part IV baseline digest missing, duplicated or changed')
    for heading in HEADINGS:
        if part.count(heading) != 1:
            findings.append('Part IV heading missing/duplicated: ' + heading)
    findings.extend(differences(baseline.get('contracts', {}), current))
    return findings


def generated_records(directory, records):
    """Check every frozen UDT present in a generated package; reject duplicates."""
    result = {}
    for path in sorted(directory.rglob('*.udt')):
        for block in tia_lint.parse_blocks(path.read_text(encoding='utf-8-sig')):
            if block.kind != 'TYPE' or block.name not in records:
                continue
            if block.name in result:
                raise ValueError('duplicate generated UDT: ' + block.name)
            result[block.name] = [
                {'member': d.name, 'native_type': d.type_text,
                 **access_flags(d.attrs)}
                for d in block.decls]
    return result


def native_records(directory, records):
    """Read Openness-exported UDT interfaces, including order and visibility."""
    result = {}
    for path in sorted(directory.rglob('*.type.xml')):
        tree = ET.parse(path)
        name = tree.findtext('.//SW.Types.PlcStruct/AttributeList/Name')
        if name not in records:
            continue
        if name in result:
            raise ValueError('duplicate native UDT: ' + name)
        members = tree.findall('.//Interface/{*}Sections/{*}Section/{*}Member')
        result[name] = []
        for member in members:
            flags = {a.attrib['Name']: a.text for a in member.findall('./{*}AttributeList/{*}BooleanAttribute')}
            result[name].append({'member': member.attrib['Name'], 'native_type': member.attrib['Datatype'],
                                 **{key: flags.get(key, 'true').lower() == 'true'
                                    for key in ('ExternalAccessible', 'ExternalVisible', 'ExternalWritable')}})
    return result


def audit_layouts(expected, actual, label):
    if not actual:
        return [label + ': no frozen UDTs found; refusing vacuous success']
    findings = [label + '.' + name + ': frozen UDT missing' for name in sorted(expected.keys() - actual.keys())]
    for name, fields in actual.items():
        wanted = [{'member': f['member'], 'native_type': f['native_type'],
                   **{key: f['accessible'] for key in
                      ('ExternalAccessible', 'ExternalVisible', 'ExternalWritable')}} for f in expected[name]]
        # Native exporters canonicalize whitespace, quoting and scalar case.
        clean = lambda rows: [{**f, 'native_type': normalized(f['native_type'].split(':=')[0])} for f in rows]
        findings.extend(differences(clean(wanted), clean(fields), label + '.' + name))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=BASELINE)
    parser.add_argument('--generated', type=Path, help='also compare all frozen UDTs in a full-profile package')
    parser.add_argument('--native', type=Path, help='also compare all frozen UDTs in full-profile Openness XML exports')
    args = parser.parse_args(argv)
    try:
        raw = args.baseline.read_bytes()
        baseline = json.loads(raw)
        current = collect()
        findings = audit(baseline, current, PART.read_text(encoding='utf-8'), hashlib.sha256(raw).hexdigest())
        counts = {}
        for label, path, read in [('generated', args.generated, generated_records), ('native', args.native, native_records)]:
            if path is not None:
                layouts = read(path, current['records'])
                counts[label] = len(layouts)
                findings.extend(audit_layouts(current['records'], layouts, label))
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        print('ERROR [tia-contracts] ' + str(exc), file=sys.stderr)
        return 2
    for finding in findings:
        print('TIA-CONTRACT: ' + finding)
    if findings:
        return 1
    print('Fraktal/TIA candidate V1 contract: clean (' + str(len(current['records'])) +
          ' records, ' + str(len(current['enums'])) + ' enums; ' +
          ', '.join(k + '=' + str(v) for k, v in counts.items()) + '). R3 remains partial.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
