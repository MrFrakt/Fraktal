"""Mutation check for the S6 row-body batching tests (scratch apparatus).

Each mutant is a copy of fraktal_ab_canonical_live.py placed first on sys.path;
the named tests must FAIL against it and pass against the original.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

TOOLS = Path(sys.argv[1]).resolve()
SOURCE = (TOOLS / 'fraktal_ab_canonical_live.py').read_text(encoding='utf-8')

MUTANTS = {
    'plan-inside-attempt-loop': (
        [("        packets = self._body.plan(tuple(selected.values()))\n", ""),
         ("        for attempt in range(1, 21):\n",
          "        for attempt in range(1, 21):\n"
          "            packets = self._body.plan(tuple(selected.values()))\n")],
        ['Rows.test_body_is_planned_once_before_any_proof_and_outside_its_window']),
    'parse-only-when-coherent': (
        [("                samples = {loc.path: raw for packet, reply in zip(packets, replies)\n",
          "                samples = lambda: {loc.path: raw for packet, reply in zip(packets, replies)\n"),
         ("                    decoded = {p: self._decode(selected[p], raw) for p, raw in samples.items()}",
          "                    decoded = {p: self._decode(selected[p], raw) for p, raw in samples().items()}")],
        ['Wire.test_malformed_reply_refuses_even_from_a_torn_attempt']),
    'read-cap-65': (
        [("MAX_PACKET_READS = 64\n", "MAX_PACKET_READS = 65\n")],
        ['Wire.test_connection_budget_caps_reads_and_bytes']),
    'no-reply-byte-bound': (
        [("                          or 6 + 2 + 2 * count + received + 4 + reply > capacity):",
          "                          ):")],
        ['Wire.test_every_sealed_leaf_replays_exactly_through_bounded_packets']),
}


def run(directory, tests):
    # The working directory precedes PYTHONPATH, so the copy under test shadows
    # the tools tree while the test module (and its capture path) stays there.
    names = ['test_fraktal_ab_canonical_live.' + t for t in tests]
    env = dict(os.environ, PYTHONPATH=str(TOOLS))
    result = subprocess.run([sys.executable, '-m', 'unittest', *names], cwd=directory,
                            capture_output=True, text=True, env=env)
    return result


failures = 0
for name, (edits, tests) in MUTANTS.items():
    text = SOURCE
    for old, new in edits:
        assert text.count(old) == 1, (name, old)
        text = text.replace(old, new)
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, 'fraktal_ab_canonical_live.py').write_text(text, encoding='utf-8')
        killed = run(tmp, tests).returncode != 0
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(TOOLS / 'fraktal_ab_canonical_live.py', tmp)
        original = run(tmp, tests).returncode == 0
    print(f'{name}: mutant {"KILLED" if killed else "SURVIVED"}, original {"passes" if original else "FAILS"}')
    failures += (not killed) + (not original)
sys.exit(1 if failures else 0)
