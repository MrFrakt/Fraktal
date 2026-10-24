"""Read-only S3f inventory. No controller or store connection; no oracle edits."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import re
import sys

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
WORK = Path(__file__).parent
TOOLS = ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0, str(TOOLS))
import fraktal_ab_genealogy_s3e_demo as demo
import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_projection as projection
import fraktal_ab_sets as sets


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


capture_path = TOOLS / 'fixtures/canonical/genealogy_projection_01.json.gz'
compressed = capture_path.read_bytes()
expanded = gzip.decompress(compressed)
capture = json.loads(expanded)
previous_path = ROOT / 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3E_INVENTORY_2026-10-22.json'
previous = json.loads(previous_path.read_text())
app = demo.application()
assert app.canonical_publication_stage == 7


def selected(path):
    return path.startswith((app.name + '/ConfigPersist/', app.name + '/ConfigSet',
                            app.name + '/HmiResponse/ConfigPage/')) or path == app.name + '/Status/ConfigRev'


def python_type(value):
    return 'Boolean' if type(value) is bool else 'String' if type(value) is str else 'Int32' if type(value) is int else 'Double' if type(value) is float else 'UNSUPPORTED'


def core_type(path, old):
    # Each exception is tied to an owning Core declaration below, not inferred
    # by a runtime reader. These are audit annotations, not an accepted map.
    leaf = path.rsplit('/', 1)[-1]
    if '/HmiResponse/ConfigPage/Entries[' in path:
        return 'Double' if leaf in ('Minimum', 'Maximum') else 'UInt32' if leaf == 'WriteRevision' else old
    if '/HmiResponse/ConfigPage/' in path:
        return 'Int16' if leaf in ('PageCount', 'EntryCount') else old
    if '/ConfigSets[' in path:
        return 'DateTime' if leaf == 'CreatedAt' else 'UInt32' if leaf == 'ConfigRev' else 'Int16' if leaf == 'RecordCount' else old
    if '/ConfigPersist/' in path:
        return 'DateTime' if leaf == 'PendingSince' else 'UInt32' if leaf == 'WindowMs' else old
    if leaf == 'ConfigRev':
        return 'UInt32'
    if leaf in ('ConfigSetCount', 'ConfigSetDocumentLine', 'ConfigSetDocumentLines'):
        return 'Int16'
    return old


added = {}
for path, value in sorted(capture['values'].items()):
    if not selected(path):
        continue
    assert path not in previous['paths'], path
    old = python_type(value)
    added[path] = dict(projectionPath=path, value=value, legacyType=old,
                       proposedCoreType=core_type(path, old), ownerApprovalRequired=core_type(path, old) != old)
assert len(added) == 801
entries = capture['values'][app.name + '/HmiResponse/ConfigPage/EntryCount']
assert entries == len(gen.editable_values(app)) == 30
assert len(previous['paths']) == 2154
assert len(set(previous['paths']) | set(added)) == 2955

params_path = ROOT / 'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Params/PL_Fraktal.TcGVL'
params = params_path.read_text(encoding='utf-8')
page_size = int(re.search(r'MAX_CONFIG_PAGE\s*:\s*INT\s*:=\s*(\d+)', params)[1])
assert page_size == 16
page_counts = [min(page_size, entries - start) for start in range(0, entries, page_size)]
assert page_counts == [16, 14]

entry_rows = []
prefix = app.name + '/HmiResponse/ConfigPage/Entries['
for index in range(1, entries + 1):
    entry_rows.append({p.rsplit('/', 1)[-1]: v for p, v in capture['values'].items() if p.startswith(prefix + str(index) + ']/')})
assert len({row['WriteKey'] for row in entry_rows}) == entries
assert {p.rsplit('/', 1)[-1] for p in added if p.startswith(prefix)} == set(entry_rows[0])
revision = projection._config_revision(app, entry_rows)
assert revision == capture['values'][app.name + '/Status/ConfigRev']

# Reproduce the non-empty-list distinction without reading or writing a store.
header = dict(set='s3f_inventory_only', root=app.name, kind=1, model='', records=5,
              configRev=manifest.config_revision(app), created=1792713600, clock=0)
overlay = sets.list_values(app.name, [header])
empty = sets.empty_values(app.name)
assert empty[app.name + '/ConfigSetCount'] == 0
assert overlay[app.name + '/ConfigSetCount'] == 1
assert type(overlay[app.name + '/ConfigSets[1]/CreatedAt']) is int

# Existing PendingSince is HHMMSSmmm. The same number occurs on any date and
# cannot establish an absolute timestamp. Numeric zero must remain unset.
sets_source = (TOOLS / 'fraktal_ab_sets.py').read_text(encoding='utf-8')
assert "f'{p}.PendingSince := FRK_{app.name}_NowTime;'" in sets_source
dates = [datetime.datetime(2026, 10, day, 12, 34, 56, tzinfo=datetime.timezone.utc) for day in (21, 22)]
clock = 123456000
timestamp_vector = [dict(date=d.strftime('%Y%m%d'), legacyNowTime=clock,
                         expectedUtc=d.isoformat().replace('+00:00', 'Z')) for d in dates]
assert timestamp_vector[0]['legacyNowTime'] == timestamp_vector[1]['legacyNowTime']
assert timestamp_vector[0]['expectedUtc'] != timestamp_vector[1]['expectedUtc']

sources = [capture_path, previous_path, params_path]
sources += [TOOLS / name for name in ('fraktal_ab_projection.py', 'fraktal_ab_sets.py',
    'fraktal_ab_set_broker.py', 'fraktal_ab_mailbox.py', 'fraktal_ab_generate.py')]
sources += [ROOT / 'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core' / name for name in (
    'DUTs/ST_ConfigEntry.TcDUT', 'DUTs/ST_ConfigPage.TcDUT', 'DUTs/ST_ConfigPersistStatus.TcDUT',
    'DUTs/ST_ConfigSetInfo.TcDUT', 'BaseClasses/FB_UnitBase.TcPOU', 'BaseClasses/FB_ConfigPager.TcPOU')]
sources += [ROOT / 'Specification' / name for name in (
    'Fraktal_Core_Part_I.md', 'Fraktal_AB_Part_III.md', 'Fraktal_TIA_Part_IV.md',
    'OPCUA_TRANSPORT.md', 'HMI_CONTRACT.md')]
changes = {p: row for p, row in added.items() if row['ownerApprovalRequired']}
types = {}
for row in changes.values():
    key = row['legacyType'] + '->' + row['proposedCoreType']
    types[key] = types.get(key, 0) + 1
result = dict(
    schema='fraktal.ab.s3f-surface-inventory', schemaVersion=1,
    status='review-required-not-a-passed-preparation', date='2026-10-22',
    capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    controllerAccess=False, tagWrites=0, productionSourceChanges=False,
    sourceProjection=capture_path.relative_to(ROOT).as_posix(),
    sourceCompressedSha256=digest(compressed), sourceExpandedSha256=digest(expanded),
    previousPaths=2154, addedLegacyPaths=801, cumulativeLegacyPaths=2955,
    editableEntries=entries, entryFields=len(entry_rows[0]),
    legacyPageCount=1, legacyPageEntryCount=30, referenceWindowEntries=page_size,
    proposedPageEntryCounts=page_counts,
    referenceWindowSource=params_path.relative_to(ROOT).as_posix(),
    referenceWindowIsNormativeCoreConstant=False,
    normativePagingRequirement='Core 3.10.2: paging shall not require a full manifest buffer in the PLC',
    proposedTypeChanges=len(changes), proposedTypeChangeCounts=types,
    coreFieldsAbsentFromFrozenOracle=['HmiResponse/ConfigPage/Revision', 'HmiResponse/ConfigPage/PageIndex',
        'ConfigPersist/LastSetName', 'ConfigPersist/LastSetRecords',
        *[f'ConfigSets[{i}]/{n}' for i in range(1, 5) for n in ('Used', 'SetSchema')]],
    legacyRevision=revision, legacyRevisionAlgorithm='SHA256 of build revision and ordered WriteKey/ValueText/effective-level/readability strings; first 31 bits',
    revisionDoesNotIncludeBootIdentity=True,
    pendingSinceSource='FRK_<root>_NowTime: HHMMSSmmm, without a date',
    pendingSinceCounterexample=timestamp_vector,
    listOverlayCounterexample=dict(emptyProjectionCount=0, brokerListCount=1,
        createdAtLegacyType='Int32 Unix seconds', pureFunctionsOnly=True, externalStoreAccess=False),
    providerBoundary='The host adapter owns medium I/O; the PLC must own the validated published response. Generic clients must not reconstruct it.',
    approvedD2BoundCorrectionsUnchanged=True, acceptanceRulesChanged=False,
    paths=added,
    sourceBindings={p.relative_to(ROOT).as_posix(): dict(bytes=p.stat().st_size, sha256=digest(p.read_bytes())) for p in sources},
)
for path in (WORK / 'inventory_01.json', ROOT / 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3F_INVENTORY_2026-10-22.json'):
    with path.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
print(json.dumps({k: result[k] for k in ('status', 'previousPaths', 'addedLegacyPaths', 'cumulativeLegacyPaths',
    'editableEntries', 'entryFields', 'proposedPageEntryCounts', 'proposedTypeChanges', 'proposedTypeChangeCounts',
    'controllerAccess', 'tagWrites', 'acceptanceRulesChanged')}))
