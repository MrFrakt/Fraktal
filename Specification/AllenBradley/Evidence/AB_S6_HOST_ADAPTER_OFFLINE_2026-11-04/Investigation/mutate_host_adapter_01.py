"""Mutate the host adapter's source in memory; each mutant must fail its suite.

Each mutant replaces one exact line of fraktal_ab_host_adapter.py, executes the
mutated text into the loaded module, runs test_fraktal_ab_host_adapter, and
restores the original text before the next one. No file is changed and no
controller is contacted.
"""
import json
import sys
import unittest
from pathlib import Path

TOOLS = Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
sys.path.insert(0, str(TOOLS))
import fraktal_ab_host_adapter as adapter
import test_fraktal_ab_host_adapter as suite

SOURCE = (TOOLS / 'fraktal_ab_host_adapter.py').read_text(encoding='utf-8')
MUTANTS = [
    ('a missing set answered as found', "        except (documents.SetRejected, UnicodeError, FileNotFoundError):\n            return self._status(job, binding.REFUSED)",
     "        except (documents.SetRejected, UnicodeError, FileNotFoundError):\n            return self._status(job, binding.OK)"),
    ('a full store not refused', "len(headers) >= documents.MAX_SETS", "len(headers) >= 99"),
    ('an import commit not kept', "            name, self.committed = document[0]['set'], document",
     "            name = document[0]['set']"),
    ('a restore that hides its losses', "status=binding.LOST if losses else binding.OK", "status=binding.OK"),
    ('a boolean rendered as a number', "value=('TRUE' if values[c.ordinal - 1] else 'FALSE') if c.value_type == 2 else str(values[c.ordinal - 1])",
     "value=str(values[c.ordinal - 1])"),
    ('invalid value text coerced', "                types.append(-1)\n                values.append(0)",
     "                types.append(kind)\n                values.append(0)"),
    ('the catalog never published', "            return self._answer(job, [dict(Kind=binding.CATALOG,",
     "            return self._status(job, binding.OK) or self._answer(job, [dict(Kind=binding.CATALOG,"),
    ('a keep that never writes', "                self.medium.write(key, document)", "                pass"),
]


def run():
    loaded = unittest.defaultTestLoader.loadTestsFromModule(suite)
    result = unittest.TextTestRunner(stream=open('nul', 'w'), verbosity=0).run(loaded)
    return result.testsRun, len(result.failures) + len(result.errors)


def load(text):
    exec(compile(text, adapter.__file__, 'exec'), adapter.__dict__)


def main():
    report = dict(baseline=None, mutants=[])
    report['baseline'] = dict(zip(('tests', 'failed'), run()))
    print('baseline', report['baseline'], flush=True)
    # The emitted controller benches do not change between mutants: build once.
    suite.setUpModule = lambda: None
    for label, old, new in MUTANTS:
        if SOURCE.count(old) != 1:
            raise SystemExit(f'mutant anchor not unique: {label} ({SOURCE.count(old)})')
        load(SOURCE.replace(old, new))
        try:
            ran, failed = run()
        finally:
            load(SOURCE)
        report['mutants'].append(dict(label=label, tests=ran, failed=failed, killed=failed > 0))
        print(('killed  ' if failed else 'SURVIVED'), failed, label, flush=True)
    report['passed'] = report['baseline']['failed'] == 0 and all(m['killed'] for m in report['mutants'])
    if len(sys.argv) > 1:
        with Path(sys.argv[1]).open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(report, stream, indent=2)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
