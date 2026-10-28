"""Seal the completed freshness session before any reader changes."""
from pathlib import Path

W = Path(__file__).parent
original = W / 'seal_lookup_attempt_01.py'
archived = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26/Continuation/seal_lookup_attempt_01.py')
assert original.read_bytes() == archived.read_bytes()
source = original.read_text(encoding='utf-8')

def replace(before, after, count=1):
    global source
    assert source.count(before) == count, (before, source.count(before))
    source = source.replace(before, after)

replace("D = W.parent / 'retry_lookup_01'", "D = W.parent / 'retry_freshness_01'")
replace('AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26', 'AB_S4B_FRESHNESS_RETRY_ATTEMPT_2026-10-26')
replace("len(dart['samples']) == 140", "len(dart['samples']) == 884")
replace("exactFailedAttemptCountersRecorded=False", "exactFailedAttemptCountersRecorded=True")
replace("observerSamples=140", "observerSamples=884", 3)
replace('call_2b13d9faea7945c9803fd0d2782b3c10:0', 'call_9f47a022b96c480b81af9d85ec59f551:0', 2)
replace('Approve guarded S4b lookup retry', 'Approve guarded S4b freshness retry', 2)
start = source.index("report = '''")
end = source.index('\nassert sum(', start)
source = source[:start] + (W / 'freshness_attempt_report.txt').read_text(encoding='utf-8') + source[end:]
replace("assert sum(row['uncertain'] > 0 for row in dart['samples']) == 59", """assert sum(row['uncertain'] > 0 for row in dart['samples']) == 78
assert all(row['bad'] == 0 for row in dart['samples'])
dv = root['identityDataValue']
assert dv['coherenceAttempts'] == 3 and dv['coherenceAcquisitionUs'] == 6237
assert [row['reason'] for row in dv['coherenceFailures']] == ['revision-changed', 'odd-before', 'odd-before']
assert [row['before'] for row in dv['coherenceFailures']] == [123678, 123679, 123679]
assert [row.get('after') for row in dv['coherenceFailures']] == [123679, None, None]""")
start = source.index("for name in ('authorize_lookup_retry_01.py'")
end = source.index("\nfor name in ('authorize_lookup_retry_01.log'", start)
source = source[:start] + """for name in ('authorize_freshness_retry_01.py', 'inspect_freshness_runtime_01.py',
             'replay_freshness_pairs_01.py', 'seal_freshness_attempt_01.py',
             'freshness_attempt_report.txt', 'PENDING_S4B_AGE_BOUNDARY_AUDIT_2026-10-26.md'):
    archive(W / name, 'Continuation/' + name)
""" + source[end:]
replace("('authorize_lookup_retry_01.log', 'authorize_lookup_retry_01_exit.json')", "('authorize_freshness_retry_01.log', 'authorize_freshness_retry_01_exit.json')")
replace("schema='fraktal.ab.s4b-lookup-retry-attempt'", "schema='fraktal.ab.s4b-freshness-retry-attempt'")
replace('AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26/manifest.json', 'AB_S4B_FRESHNESS_RETRY_PREPARATION_2026-10-26/manifest.json')
replace("W / 'sealed_lookup_attempt_01.json'", "W / 'sealed_freshness_attempt_01.json'")
exec(compile(source, str(original), 'exec'), {'__file__': __file__})
