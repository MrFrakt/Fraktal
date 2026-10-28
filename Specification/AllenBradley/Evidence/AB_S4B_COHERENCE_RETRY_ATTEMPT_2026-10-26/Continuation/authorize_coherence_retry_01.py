from pathlib import Path

W = Path(__file__).parent
original = W / 'authorize_lookup_retry_01.py'
archived = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26/Continuation/authorize_lookup_retry_01.py')
assert original.read_bytes() == archived.read_bytes()
source = original.read_text(encoding='utf-8')
for before, after in {
    "D = Path('C:/work/fraktal-ab-s4b-20261025/retry_lookup_01')": "D = Path('C:/work/fraktal-ab-s4b-20261025/retry_coherence_01')",
    'AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26': 'AB_S4B_COHERENCE_RETRY_PREPARATION_2026-10-26',
    '7da9844267de8f3c0a080bec16b8144960e17c1f4ec2813cdd2d3dc32c332ff5': 'c450a27d88eac25776c188edae3ee91b23595601d0aabfe07b097630e6984408',
    'qualification_lookup_retry': 'qualification_coherence_retry',
    'Approve guarded S4b lookup retry': 'Approve guarded S4b paced coherence retry',
    'call_2b13d9faea7945c9803fd0d2782b3c10:0': 'call_6af11f6634e14bc29c3a346b410be129:0',
}.items():
    assert source.count(before) == 1, before
    source = source.replace(before, after)
exec(compile(source, str(original), 'exec'), {'__file__': __file__})
