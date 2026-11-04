"""Source mutations of the V6.11 host ingress and client binding, run against
the unchanged focused tests. Each mutant must be killed by a named failure.

A mutant lives in a temporary directory that shadows only its own module
(cwd and PYTHONPATH first); the tools directory supplies everything else.
Literal TRUE/FALSE are avoided so a kill is semantic, not a parse error.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

TOOLS = Path(sys.argv[1])
TESTS = ('test_fraktal_ab_host_services', 'test_fraktal_ab_host_service_binding')
MUTANTS = {
    'fraktal_ab_host_services.py': {
        'no commit re-read': ("OR ({c} <> {w}.Seen) THEN {w}.Error := {binding.COLLIDED}",
                              "THEN {w}.Error := {binding.COLLIDED}"),
        'half circle counts as ahead': ("({w}.Upper >= 32768)", "({w}.Upper > 32768)"),
        'refused claim keeps the job': ("f'IF ({w}.Claimed <> 0) AND ({w}.Error <> 0)",
                                        "f'IF ({w}.Claimed <> 0) AND ({w}.Error < 0)"),
        'key extents unbounded': ("f'ELSIF {w}.Bad <> 0 THEN {w}.Error := {binding.INVALID};',", ""),
        'first scan keeps the job': ("f'IF S:FS AND ({r}.JobSequence <> 0) THEN'",
                                     "f'IF S:FS AND (0 = 1) AND ({r}.JobSequence <> 0) THEN'"),
        'any sequence claims': ("f'ELSIF {w}.Claimed = 0 THEN {w}.Error := {binding.NO_JOB};',", ""),
        'chunk order unchecked': ("OR ({s}.Chunk <> {r}.NextChunk) THEN", "THEN"),
        'reply copied every scan': ("f'IF {w}.Dirty <> 0 THEN', f'CPS({r},{reply_tag(app)},1);'",
                                    "f'IF {w}.Armed <> 0 THEN', f'CPS({r},{reply_tag(app)},1);'"),
        'job text only shortened': ("f'{r}.{name}.DATA[{w}.Index] := 0;'", "f'{r}.{name}.LEN := 0;'"),
        'manifest revision unchecked': (
            "f'ELSIF {s}.ManifestRevision <> {pub.header_tag(app)}.ConfigRevision THEN {w}.Error := {binding.STALE_REVISION};',", ""),
    },
    'fraktal_ab_host_service_binding.py': {
        'writer advances from the refusal': ("    serial = reply['Serial']\n", "    serial = reply['AckSequence']\n"),
        'roots may split their ingress': ("            if ingress.setdefault(root, shared) != shared:\n",
                                          "            if ingress.setdefault(root, shared) is None:\n"),
        'text one byte over its width': ("        if len(raw) > width or b'\\0' in raw:\n",
                                         "        if len(raw) > width + 1 or b'\\0' in raw:\n"),
        'request size unbounded': ("or sizes[handle] > row['MaximumChunkBytes'] \\\n", "\\\n"),
    },
}
results = []
for module, mutants in MUTANTS.items():
    source = (TOOLS / module).read_text(encoding='utf-8')
    for name, (old, new) in mutants.items():
        assert source.count(old) == 1, (module, name)
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, module).write_text(source.replace(old, new), encoding='utf-8')
            for test in TESTS:
                shutil.copy(TOOLS / (test + '.py'), directory)
            env = dict(os.environ, PYTHONPATH=os.pathsep.join([directory, str(TOOLS)]))
            run = subprocess.run([sys.executable, '-m', 'unittest', *TESTS], cwd=directory, env=env,
                                 capture_output=True, text=True, timeout=600)
        failed = sorted({line.split(' (')[0].split(': ', 1)[1] for line in run.stderr.splitlines()
                         if line.startswith(('FAIL: ', 'ERROR: '))})
        results.append(dict(module=module, mutant=name, exitCode=run.returncode,
                            killed=run.returncode != 0 and bool(failed), failingTests=failed))
        print(('KILLED   ' if results[-1]['killed'] else 'SURVIVED ') + name, failed[:3])
print(json.dumps(dict(mutants=len(results), killed=sum(r['killed'] for r in results), results=results), indent=1))
raise SystemExit(0 if all(r['killed'] for r in results) else 1)
