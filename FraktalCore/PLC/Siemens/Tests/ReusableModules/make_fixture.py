"""The P9 reusable module types composed under one root Unit, for native compile.

Every type is bound by the same function the press uses (command labels from
the type's own catalog, band reasons from the TC3 module reason list), and the
typed APIs call the same sequence runtime the press ships. Nothing here is
station logic: the root only owns the three modules so each is instantiated.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TIA = HERE.parents[1]
sys.path.insert(0, str(TIA / 'tools'))
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
from fraktal_tia_binding import Catalog
from fraktal_tia_examples import bind, module_type, sequence_sources

MODULES = TIA / 'Framework/Modules'
# (directory, stem, api source name or None); the cylinder is the clamp's child.
TYPES = ((MODULES / 'EquipmentModules/Clamp', 'clamp', '22_ClampApi.scl'),
         (MODULES / 'ControlModules/ConfigurableCylinder', 'configurable_cylinder', '22_ConfigurableCylinderApi.scl'),
         (MODULES / 'ControlModules/Separator', 'separator', '22_SeparatorApi.scl'),
         (MODULES / 'ControlModules/Cylinder', 'cylinder', '22_CylinderApi.scl'))
LEASE = ('STRUCT OwnerIndex : DINT; ChainIndex : DINT; BranchIndex : DINT; '
         'Step : DINT; Raised : BOOL; AbortIssued : BOOL; ReleasedScan : UDINT; END_STRUCT')


def declaration(catalog):
    records = {'ST_SequenceCommandLease': LEASE,
               'ST_BenchUnitParCfg': 'STRUCT SchemaVersion : UINT := 1; Timeout : TIME := T#10s; END_STRUCT',
               'ST_BenchUnitParCmd': 'STRUCT Reserved : BOOL; END_STRUCT',
               'ST_BenchUnitOutCmd': 'STRUCT Done : BOOL; END_STRUCT',
               'ST_BenchUnitOutImm': 'STRUCT Ready : BOOL; END_STRUCT'}
    types = []
    for directory, stem, _ in TYPES:
        module, module_records = module_type(directory, stem, catalog)
        records.update(module_records)
        types.append(module)
    unit = {'name': 'FB_BenchUnit', 'tier': 'UNIT', 'type_key': 'bench.reusableModulesUnit',
            'children': [{'name': 'Clamp', 'type': 'FB_ClampEM'},
                         {'name': 'ConfigCyl', 'type': 'FB_ConfigurableCylinderCM'},
                         {'name': 'Separator', 'type': 'FB_SeparatorCM'}],
            'contract': {k: 'ST_BenchUnit' + k for k in ('ParCfg', 'ParCmd', 'OutCmd', 'OutImm')},
            'commands': [{'id': 1, 'label': 'Run'}], 'timeout': 'Timeout',
            'unit': {'modes': ['AUTO', 'MANUAL'], 'initial': 'MANUAL', 'run_command': 1},
            # The typed module APIs are called from chains; a sequence view is
            # what brings the chain runtime they bind against into the program.
            'sequence_view': {'capacity': 8, 'branches': 2, 'annotations': 4},
            'logic': {'cyclic': '    #OutImm.Ready := TRUE;'}}
    return {'schema_version': 1, 'target_family': 'S7-1500', 'registry_capacity': 16,
            'types': [unit, *types], 'roots': [{'name': 'BenchUnit', 'type': 'FB_BenchUnit'}],
            'records': records}


def build():
    catalog = Catalog.read()
    sources, manifest = GEN.build(DECL.validate(declaration(catalog)), True)
    sources.update(sequence_sources(catalog))
    for directory, stem, api in TYPES:
        commands = {c['label']: c['id'] for c in json.loads((directory / (stem + '.json')).read_bytes())['commands']}
        sources[api] = bind((directory / (stem + '_api.scl.in')).read_text('ascii'), catalog, commands)
    sim = MODULES / 'ControlModules/ConfigurableCylinder/configurable_cylinder_sim.scl.in'
    sources['38_ConfigurableCylinderSim.scl'] = bind(sim.read_text('ascii'), catalog)
    return sources, manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out', type=Path)
    a = p.parse_args()
    sources, _ = build()
    a.out.mkdir(parents=True, exist_ok=False)
    for name, text in sources.items():
        (a.out / name).write_bytes(text.encode('ascii'))
    print(json.dumps(dict(sources=len(sources))))
