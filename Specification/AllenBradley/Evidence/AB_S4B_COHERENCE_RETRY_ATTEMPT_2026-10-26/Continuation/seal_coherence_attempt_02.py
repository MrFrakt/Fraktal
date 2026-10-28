from pathlib import Path

W = Path(__file__).parent
source = (W / 'seal_coherence_attempt_01.py').read_text(encoding='utf-8')
for before, after in {
    "replace('call_2b13d9faea7945c9803fd0d2782b3c10:0', 'call_6af11f6634e14bc29c3a346b410be129:0')":
        "assert source.count('call_2b13d9faea7945c9803fd0d2782b3c10:0') == 2\nsource = source.replace('call_2b13d9faea7945c9803fd0d2782b3c10:0', 'call_6af11f6634e14bc29c3a346b410be129:0')",
    "replace('Approve guarded S4b lookup retry', 'Approve guarded S4b paced coherence retry')":
        "assert source.count('Approve guarded S4b lookup retry') == 2\nsource = source.replace('Approve guarded S4b lookup retry', 'Approve guarded S4b paced coherence retry')",
    "replace('observerSamples=140', 'observerSamples=588')":
        "replace('pairedCapturesReplayed=87, observerSamples=140,', 'pairedCapturesReplayed=87, observerSamples=588,')",
    "'analyze_coherence_failure_01.py', 'seal_coherence_attempt_01.py', 'coherence_attempt_report.txt'":
        "'analyze_coherence_failure_01.py', 'seal_coherence_attempt_01.py', 'seal_coherence_attempt_02.py', 'coherence_attempt_report.txt'",
}.items():
    assert source.count(before) == 1, before
    source = source.replace(before, after)
exec(compile(source, str(W / 'seal_coherence_attempt_01.py'), 'exec'), {'__file__': __file__})
