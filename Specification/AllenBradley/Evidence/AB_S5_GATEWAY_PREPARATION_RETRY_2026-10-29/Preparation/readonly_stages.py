"""P5: every independent read-only gate runs after the writer, including failure."""
def execute_readonly_stages(run,*,python,directory,tools,timing):
    jobs=[
      ('configuration_comparison',[python,directory/'p5_configuration_comparison.py']),
      ('idle_equivalence',[python,directory/'candidate_equivalence.py','--expect-serial','601FC87B','--output',directory/'idle_equivalence.json.gz']),
      ('generic_acquire',[python,tools/'fraktal_ab_canonical_acquire.py','--expect-serial','601FC87B','--output',directory/'generic_snapshot.json.gz','--capture-output',directory/'generic_capture.json.gz']),
      ('candidate_timing',[python,timing,directory/'candidate_timing.json','--candidate'])]
    failures=[]
    for label,args in jobs:
        try:run(label,*args)
        except Exception as error:failures.append(dict(stage=label,error=f'{type(error).__name__}: {error}'))
    return failures
