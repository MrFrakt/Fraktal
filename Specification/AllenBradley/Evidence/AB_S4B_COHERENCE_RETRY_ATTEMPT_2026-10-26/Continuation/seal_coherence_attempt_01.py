"""Preserve the paced run before correcting its newly exposed aging gap."""
from pathlib import Path

W = Path(__file__).parent
original = W / 'seal_lookup_attempt_01.py'
archived = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26/Continuation/seal_lookup_attempt_01.py')
assert original.read_bytes() == archived.read_bytes()
source = original.read_text(encoding='utf-8')

def replace(before, after):
    global source
    assert source.count(before) == 1, before
    source = source.replace(before, after)

replace("D = W.parent / 'retry_lookup_01'", "D = W.parent / 'retry_coherence_01'")
replace("OUT = E / 'AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26'", "OUT = E / 'AB_S4B_COHERENCE_RETRY_ATTEMPT_2026-10-26'")
replace("len(dart['samples']) == 140", "len(dart['samples']) == 588")
start = source.index("assert dart['error'] ==")
end = source.index('\nstages = ', start)
source = source[:start] + """assert dart['error'] == 'FormatException: Bad value in cyclic qualification.'
assert dart['samples'][-1]['bad'] == 1 and all(row['bad'] == 0 for row in dart['samples'][:-1])
analysis = load(D / 'failure_analysis_01.json')
assert analysis['retainedNonGoodOrOldest'][0]['path'] == 'Press/ShiftHistoryTruncated'
assert analysis['retainedNonGoodOrOldest'][0]['reason'] == 'coherence-unavailable'
assert not any(row.get('qualificationRejectedRootSample') for row in dart['snapshots'])
""" + source[end:]
replace("failed = {'qualification_run_01', 'candidate_regressions', 'dart_observer'}",
        "failed = {'qualification_run_01', 'candidate_regressions', 'dart_observer', 'readonly_diagnostics_01'}")
start = source.index('summary = dict(')
end = source.index("\nsave(D / 'runtime_summary_01.json'", start)
source = source[:start] + """summary = dict(passed=False, nativeAccepted=False, serial='601FC87B', candidateCases=41,
    candidateCasesPassed=True, pairedCapturesReplayed=87, minimumPairedPaths=4799, maximumPairedPaths=5407,
    observerPassed=False, observerError=dart['error'], observerRows=588, nonBadRows=587,
    finalBadValues=1, badSnapshotCaptured=False, configurationPages=0, rootRefusals=0,
    sampleAgeMs=inspection['sampleAgeMs'], rpcUs=inspection['rpcUs'],
    maximumAcceptedRowWindowUs=inspection['maximumAcceptedRowWindowUs'],
    lastRetainedUncertainPath='Press/ShiftHistoryTruncated',
    implementationSlowExpiryMs=10000, publishedSlowExpiryMs=15000,
    specificBadPathConfirmed=False, supplementaryReadOnlySamples=33,
    supplementaryCaptureInterruptedByRollback=True, baselineCases=31, genealogyRestored=True,
    finalChecksPassed=True, originalDocumentsRestored=5, stageExits=stages,
    baselineScanMedianUs=statistics.median(row['FRK_Press_HealthProbe.TaskLastScanUs'] for row in timing),
    baselineScanCumulativeMaxUs=max(row['FRK_Press_HealthProbe.TaskMaxScanUs'] for row in timing),
    baselineOverlaps=max(row['FRK_Press_HealthProbe.TaskOverlapCount'] for row in timing),
    authorizationConsumed=True, currentControllerChangesAuthorized=False,
    dumpFiles=[], faultClears=0, clockChanges=0, powerOperations=0, hardKills=0)
""" + source[end:]
replace('call_2b13d9faea7945c9803fd0d2782b3c10:0', 'call_6af11f6634e14bc29c3a346b410be129:0')
replace('Approve guarded S4b lookup retry', 'Approve guarded S4b paced coherence retry')
start = source.index("report = '''")
end = source.index('\nassert sum(', start)
source = source[:start] + (W / 'coherence_attempt_report.txt').read_text(encoding='utf-8') + source[end:]
replace("assert sum(row['uncertain'] > 0 for row in dart['samples']) == 59", "assert sum(row['uncertain'] > 0 for row in dart['samples']) == 41")
start = source.index("for name in ('authorize_lookup_retry_01.py'")
end = source.index("\nfor name in ('authorize_lookup_retry_01.log'", start)
source = source[:start] + """for name in ('authorize_coherence_retry_01.py', 'inspect_coherence_runtime_01.py', 'replay_coherence_pairs_01.py',
             'coherence_readonly_diagnostics_01.dart', 'run_coherence_readonly_diagnostics_01.py',
             'analyze_coherence_failure_01.py', 'seal_coherence_attempt_01.py', 'coherence_attempt_report.txt'):
    archive(W / name, 'Continuation/' + name)
""" + source[end:]
replace("('authorize_lookup_retry_01.log', 'authorize_lookup_retry_01_exit.json')",
        "('authorize_coherence_retry_01.log', 'authorize_coherence_retry_01_exit.json')")
replace("schema='fraktal.ab.s4b-lookup-retry-attempt'", "schema='fraktal.ab.s4b-coherence-retry-attempt'")
replace('AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26/manifest.json', 'AB_S4B_COHERENCE_RETRY_PREPARATION_2026-10-26/manifest.json')
replace('observerSamples=140', 'observerSamples=588')
replace("W / 'sealed_lookup_attempt_01.json'", "W / 'sealed_coherence_attempt_01.json'")
replace('observerSamples=140, artifacts=len(artifacts)', 'observerSamples=588, artifacts=len(artifacts)')
exec(compile(source, str(original), 'exec'), {'__file__': __file__})
