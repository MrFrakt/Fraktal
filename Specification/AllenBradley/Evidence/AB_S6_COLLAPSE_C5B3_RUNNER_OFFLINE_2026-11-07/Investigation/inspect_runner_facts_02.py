"""Read-only inspection of canonical SignalTower paths and consumer classification."""
from pathlib import Path
import json, sys

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
sys.path.insert(0, str(R / 'FraktalCore/PLC/Allen-Bradley/tools'))

import fraktal_ab_canonical_reader as reader
import fraktal_ab_genealogy_s6_collapse_demo as gen_profile
import fraktal_ab_press_s6_collapse_echo38 as press_profile

session = R / 'Specification/AllenBradley/Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04/Session'
capture = reader.load_json(session / 'capture_canonical.json.gz')
legacy = json.loads((session / 'capture_legacy.json').read_bytes())
snap = reader.snapshot(capture)['values']

tower_paths = {k: v for k, v in snap.items() if 'SignalTower' in k or k.endswith('/MachineState')}
app = gen_profile.application()
press = press_profile.application()

classification = json.loads((R / 'Specification/AllenBradley/AB_S6_CONSUMER_CLASSIFICATION_2026-11-02_03.json').read_bytes())
interesting = {
    'fraktal_ab_tower_execute',
    'fraktal_ab_part_execute',
    'fraktal_ab_genealogy_execute',
    'fraktal_ab_text_resource_execute',
    'fraktal_ab_resource_execute',
    'fraktal_ab_press_canonical_execute',
    'fraktal_ab_s3k_fixture_execute',
    'fraktal_ab_s3f_fixture_execute',
}
consumer_rows = [
    dict(
        module=c['module'],
        classification=c['classification'],
        effective=c['effectiveClassification'],
        stage=c['stage'],
        action=c['action'],
        importedBy=c['importedBy'],
    )
    for c in classification['consumers']
    if c['module'] in interesting
]

out = dict(
    towerCanonicalPaths=tower_paths,
    legacyKeys=sorted(legacy.keys()),
    genealogyFixtureObservation=app.fixture_observation,
    genealogyRecords=[dict(name=r.name, stationCfg=r.station_cfg, members=[m.name for m in r.members]) for r in app.records],
    pressRecords=[dict(name=r.name, stationCfg=r.station_cfg, members=[m.name for m in r.members]) for r in press.records],
    consumers=consumer_rows,
    controllerAccess=False,
)
with (W / 'inspect_runner_facts_02.json').open('x', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print(json.dumps(dict(passed=True, towerPathCount=len(tower_paths))))
