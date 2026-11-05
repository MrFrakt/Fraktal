"""Produce host events on the candidate: the unchanged genealogy fixture's core rows.

The baseline fixture opens with the legacy configuration restore, which V6.11
replaces by the host job the adapter already ran. So the opening rows are only
the login; then the fixture's own core regressions run in ST, SFC and LD (happy,
NOK, held, held-abort, held-mode, adopted fault), each producing part and mode
events, and its cleanup restores the inputs, the policy and MANUAL.
"""
from pathlib import Path
import os, sys

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_s6_host_demo'
sys.path.insert(0, str(ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_genealogy_execute as genealogy


def login_only(run):
    run.login()


raise SystemExit(genealogy.main(
    ['--execute-fixture', '--expect-serial', '601FC87B', '--credential-file', 'C:/work/fraktal_echo38_access_fixture.json',
     '--output', str(D / 'events_fixture.json')],
    expected_declaration='fraktal_ab_genealogy_s6_host_demo', exercise_rows=login_only))
