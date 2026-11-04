"""Which values of a sealed Access pair's independent reference differ today?

Replicates the press S3-exit replay's reference check for one sealed pair
(default context: page 0, model 0, empty provider view, as that replay uses
for Access captures) and prints every differing path with both values.
Read-only: the sealed file is only read.
"""
import gzip
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

# argv: pair file, application module, [legacy station declaration, gate module]
# The station and gate default to the application and the S3k gate.
os.environ['FRAKTAL_AB_DECLARATION'] = sys.argv[3] if len(sys.argv) > 3 else sys.argv[2]
sys.dont_write_bytecode = True
sys.path.insert(0, 'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import importlib  # noqa: E402
import fraktal_ab_manifest as manifest  # noqa: E402
import fraktal_ab_models as models  # noqa: E402
import fraktal_ab_press_execute as execute  # noqa: E402
import fraktal_ab_s2_equivalence as shared  # noqa: E402
gate = importlib.import_module(sys.argv[4] if len(sys.argv) > 4 else 'fraktal_ab_s3k_equivalence')

app = importlib.import_module(sys.argv[2]).application()
pair = json.loads(gzip.decompress(Path(sys.argv[1]).read_bytes()))['pair']
responses = {r['tag']: SimpleNamespace(Status=r['status'], Value=bytes.fromhex(r['rawHex'])
                                       if r['rawHex'] is not None else r['value']) for r in pair['rawReads']}


class Held:
    def Read(self, name):
        return responses[name]


held = Held()
u = execute.read_unit(held)
ctx = {m.name: execute.read_module(held, m.name) for m in app.modules}
codes = models.read(held, app)
additional = gate.additional_inputs(held, app)
inputs_equal = json.loads(json.dumps(dict(unit=u, contexts=ctx, codes=codes, additional=additional))) \
    == pair['legacyInputs']
context = dict(page=0, model=0, provider_state={})
expected = shared.oracle(
    app, manifest.content(app), u, ctx, codes,
    expected=gate.subset_paths(app, codes, canonical=False,
                               count=additional['host']['metadata']['Count'] if additional['host'] is not None else 0,
                               shift_count=additional['line_shift']['Count'], page=0, model=0),
    extra=lambda a, unit: gate.extra_values(a, unit, additional, **context), logical_types=gate.logical_types)
sealed = pair['projection']
paths = sorted(set(expected['values']) | set(sealed['values']))
diff = [dict(path=p, today=expected['values'].get(p, '<absent>'), sealed=sealed['values'].get(p, '<absent>'),
             todayType=expected['types'].get(p), sealedType=sealed['types'].get(p))
        for p in paths if expected['values'].get(p, '<absent>') != sealed['values'].get(p, '<absent>')
        or expected['types'].get(p) != sealed['types'].get(p)]
print(json.dumps(dict(legacyInputsEqual=inputs_equal, paths=len(paths), differing=len(diff), rows=diff[:40]),
                 indent=1, default=str))
