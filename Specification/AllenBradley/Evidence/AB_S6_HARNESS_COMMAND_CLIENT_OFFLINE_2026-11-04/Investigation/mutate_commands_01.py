"""Mutation check for the O11 command client tests (scratch apparatus)."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

TOOLS = Path(sys.argv[1]).resolve()
NAME = 'fraktal_ab_harness_commands'
SOURCE = (TOOLS / (NAME + '.py')).read_text(encoding='utf-8')
MUTANTS = {
    'sequence-first': (
        [("    writes = [dict(path=f'{root}/HmiRequest/{name}', valueType=kind,",
          "    writes = [dict(path=f'{root}/HmiRequest/Sequence', valueType='uint32', value=sequence)]\n"
          "    writes += [dict(path=f'{root}/HmiRequest/{name}', valueType=kind,"),
         ("    writes.append(dict(path=f'{root}/HmiRequest/Sequence', valueType='uint32',\n"
          "                       value=_value('Sequence', 'uint32', sequence)))\n", "")],
        ['Encoding.test_every_argument_is_written_with_its_zero_and_sequence_last']),
    'no-close-on-failure': (
        [("        except Exception as error:\n            self.close()\n",
          "        except Exception as error:\n            self._socket = None\n")],
        ['Transport.test_transport_failure_closes_and_is_never_replayed']),
    'no-settled-check': (
        [("    if values[paths[1]] & 0xffffffff != previous:\n", "    if False:\n")],
        ['Command.test_an_unsettled_mailbox_writes_nothing']),
    'no-origin': (
        [("            self._socket = self._connect(self._url, origin=self._origin,",
          "            self._socket = self._connect(self._url, origin=None,")],
        ['Loopback.test_real_websocket_carries_a_loopback_origin_and_one_json_request']),
}


def run(directory, tests):
    names = [f'test_{NAME}.{t}' for t in tests]
    env = dict(os.environ, PYTHONPATH=str(TOOLS))
    return subprocess.run([sys.executable, '-m', 'unittest', *names], cwd=directory,
                          capture_output=True, text=True, env=env).returncode


failures = 0
for name, (edits, tests) in MUTANTS.items():
    text = SOURCE
    for old, new in edits:
        assert text.count(old) == 1, (name, old)
        text = text.replace(old, new)
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, NAME + '.py').write_text(text, encoding='utf-8')
        killed = run(tmp, tests) != 0
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(TOOLS / (NAME + '.py'), tmp)
        original = run(tmp, tests) == 0
    print(f'{name}: mutant {"KILLED" if killed else "SURVIVED"}, original {"passes" if original else "FAILS"}')
    failures += (not killed) + (not original)
sys.exit(1 if failures else 0)
