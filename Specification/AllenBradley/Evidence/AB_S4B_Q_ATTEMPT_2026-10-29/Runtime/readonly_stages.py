"""WP4b.6 order and failure isolation; stages never gain a write surface."""
def execute_readonly_stages(run,*,python,directory,tools,timing):
    jobs=[
      ('configuration_comparison',[python,directory/'configuration_comparison.py']),
      ('idle_equivalence',[python,directory/'candidate_equivalence.py','--expect-serial','601FC87B','--output',directory/'idle_equivalence.json.gz']),
      ('generic_acquire',[python,tools/'fraktal_ab_canonical_acquire.py','--expect-serial','601FC87B','--output',directory/'generic_snapshot.json.gz','--capture-output',directory/'generic_capture.json.gz']),
      ('desktop_profile',[python,directory/'desktop_profile.py']),
      ('candidate_timing',[python,timing,directory/'candidate_timing.json','--candidate'])]
    failures=[]
    for label,args in jobs:
        try:run(label,*args)
        except Exception as error:failures.append(dict(stage=label,error=f'{type(error).__name__}: {error}'))
    return failures
