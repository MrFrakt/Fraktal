"""Compare Dart pages to the independent post-fixture oracle; no controller I/O."""
from pathlib import Path
import gzip
import json

W = Path(__file__).parent
D = Path('C:/work/fraktal-ab-s4b-timing-20261027/session_01')
load = lambda path: json.loads(gzip.decompress(path.read_bytes()))
dart = load(D / 'dart_qualification.json.gz')
idle = load(D / 'idle_equivalence.json.gz')
assert idle['passed']
pair = idle['pair']
oracle = pair['projection']['values']
services = pair['capture']['manifest']['readServices']
comparisons = []
for service in services:
    assert (service['Kind'], service['Version']) == (1, 1)
    root = service['CanonicalRoot']
    fields = {key[len(root) + 1:]: value for key, value in oracle.items()
        if key.startswith(root + '/')}
    definitions = {}
    for index in range(fields['DefinitionCount']):
        prefix = f'Definitions[{index}]/'
        definitions[index] = {key[len(prefix):]: value for key, value in fields.items()
            if key.startswith(prefix)}
        assert definitions[index]['DefinitionIndex'] == index
    values = []
    for index in range(fields['ValueCount']):
        prefix = f'Values[{index}]/'
        row = {key[len(prefix):]: value for key, value in fields.items()
            if key.startswith(prefix)}
        assert row['Revision'] == fields['Revision']
        values.append(row)
    ordinals = sorted({row['ModelOrdinal'] for row in values})
    actual = [page for page in dart['configurationPages'] if page['root'] == service['RootSymbol']]
    assert sorted(page['modelOrdinal'] for page in actual) == ordinals
    for ordinal in ordinals:
        selected = sorted((row for row in values if row['ModelOrdinal'] == ordinal),
            key=lambda row: row['DefinitionIndex'])
        expected = dict(PageCount=1, EntryCount=len(selected))
        for index, row in enumerate(selected, 1):
            joined = dict(definitions[row['DefinitionIndex']], ValueText=row['ValueText'], Readable=row['Readable'])
            expected.update({f'Entries[{index}]/{key}': value for key, value in joined.items()})
        page = next(page['page'] for page in actual if page['modelOrdinal'] == ordinal)
        assert page.keys() == expected.keys(), (ordinal, sorted(page.keys() ^ expected.keys()))
        differences = [key for key in expected if type(page[key]) is not type(expected[key]) or page[key] != expected[key]]
        assert not differences, (ordinal, differences)
        comparisons.append(dict(root=service['RootSymbol'], modelOrdinal=ordinal,
            entries=len(selected), scalars=len(expected), valuesAndTypesEqual=True))
assert len(dart['configurationPages']) == len(comparisons) and comparisons
result = dict(passed=True, readOnly=True, controllerAccess=False,
    source='Independent idle legacy/Core oracle joined by manifest ReadServices, not Dart values',
    pages=len(comparisons), scalarComparisons=sum(row['scalars'] for row in comparisons), rows=comparisons)
with (D / 'configuration_page_comparison_01.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
