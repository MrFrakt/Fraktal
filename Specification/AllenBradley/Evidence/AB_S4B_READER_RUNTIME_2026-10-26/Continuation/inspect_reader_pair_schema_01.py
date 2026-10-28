from pathlib import Path
import gzip
import json

W = Path(__file__).parent
D = W.parent / 'retry_reader_01'
report = json.loads(gzip.decompress((D / 'candidate_regressions_configuration_01.json.gz').read_bytes()))
pair = report['pair']
result = dict(pairKeys=list(pair), projectionKeys=list(pair['projection']),
    manifestKeys=list(pair['capture']['manifest']),
    additionalKeys=list(pair['legacyInputs']['additional']),
    viewValues={key: value for key, value in pair['projection']['values'].items()
        if '/ReadView/' in key and ('/Definitions[0]/' in key or '/Values[0]/' in key or key.count('/') == 2)})
with (D / 'pair_schema_01.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result, indent=2))
