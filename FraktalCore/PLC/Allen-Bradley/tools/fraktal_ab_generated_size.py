"""Offline code/data growth report; Studio Verify decides controller fit.

ST source bytes and statement terminators are trend measurements, not compiled
instruction bytes. DeclaredDataBytes covers DINT/SINT tag layouts (including
StringFamily padding), excluding AOI instances, aliases and unsupported types.
No compiled code, object metadata or controller reserve is estimated here.
"""
import argparse
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def st_size(source):
    code = re.sub(r'\(\*.*?\*\)|//[^\n]*', '', source, flags=re.S)
    return dict(StSourceBytes=len(source.encode('utf-8')),
                StStatementTerminators=code.count(';'),
                StLines=len(source.splitlines()))


def _dimension(value):
    return math.prod(int(n) for n in (value or '0').split(',')) or 1


def report(root):
    """Measure an emitted XML tree without a controller or a compiler."""
    routines = {}
    for path, scope in (('./Controller/Programs/Program', 'Program'),
                        ('./Controller/AddOnInstructionDefinitions/AddOnInstructionDefinition', 'AOI')):
        for owner in root.findall(path):
            for routine in owner.findall('./Routines/Routine'):
                source = '\n'.join(n.text or '' for n in routine.findall('.//STContent/Line'))
                routines[f'{scope}/{owner.get("Name")}/{routine.get("Name")}'] = {
                    **st_size(source), 'RllRungs': len(routine.findall('.//RLLContent/Rung'))}
    totals = {key: sum(row[key] for row in routines.values())
              for key in ('StSourceBytes', 'StStatementTerminators', 'StLines', 'RllRungs')}
    types = {n.get('Name'): n for n in root.findall('./Controller/DataTypes/DataType')}
    aoi = {n.get('Name') for n in root.findall('./Controller/AddOnInstructionDefinitions/AddOnInstructionDefinition')}
    sizes = {'DINT': 4, 'SINT': 1}

    def type_bytes(name, visiting=()):
        if name in sizes:
            return sizes[name]
        if name not in types or name in visiting:
            return None
        size = 0
        for member in types[name].findall('./Members/Member'):
            item = type_bytes(member.get('DataType'), (*visiting, name))
            if item is None:
                return None
            # Generated DINT/SINT UDT members start on a four-byte boundary.
            size = (size + 3) // 4 * 4 + item * _dimension(member.get('Dimension'))
        sizes[name] = (size + 3) // 4 * 4
        return sizes[name]

    data, excluded = {}, {}
    owners = [('Controller', root.find('./Controller'))]
    owners += [('Program/' + p.get('Name'), p) for p in root.findall('./Controller/Programs/Program')]
    for scope, owner in owners:
        for tag in owner.findall('./Tags/Tag'):
            name, dtype = scope + '/' + tag.get('Name'), tag.get('DataType')
            reason = ('alias' if tag.get('TagType') == 'Alias' else
                      'AOI instance' if dtype in aoi else None)
            size = None if reason else type_bytes(dtype)
            if size is None:
                excluded[name] = reason or 'unsupported type: ' + str(dtype)
            else:
                data[name] = size * _dimension(tag.get('Dimensions'))
    return dict(Schema='fraktal.ab.generated-size', SchemaVersion=1,
                StudioFitVerified=False, Totals={**totals, 'DeclaredDataBytes': sum(data.values())},
                Routines=routines, DeclaredTagBytes=data, ExcludedTags=excluded,
                Limits='Source/statement counts are trends, not compiled memory. '
                       'Data excludes AOI storage, aliases, unsupported types, object metadata and reserve.')


def compare(before, after):
    return dict(TotalDelta={key: after['Totals'][key] - before['Totals'][key]
                           for key in after['Totals']},
                RoutineDelta={name: {key: row[key] - before['Routines'].get(name, {}).get(key, 0)
                                     for key in row}
                              for name, row in after['Routines'].items()
                              if row != before['Routines'].get(name)},
                RemovedRoutines=sorted(set(before['Routines']) - set(after['Routines'])))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args(argv)
    result = report(ET.parse(args.project).getroot())
    if args.baseline:
        result['Comparison'] = compare(report(ET.parse(args.baseline).getroot()), result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
