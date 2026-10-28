from pathlib import Path

W = Path(__file__).parent
source = (W / 'replay_lookup_pairs_01.py').read_text(encoding='utf-8')
before = "D = Path('C:/work/fraktal-ab-s4b-20261025/retry_lookup_01')"
assert source.count(before) == 1
source = source.replace(before, "D = Path('C:/work/fraktal-ab-s4b-20261025/retry_coherence_01')")
exec(compile(source, str(W / 'replay_lookup_pairs_01.py'), 'exec'), {'__file__': __file__})
