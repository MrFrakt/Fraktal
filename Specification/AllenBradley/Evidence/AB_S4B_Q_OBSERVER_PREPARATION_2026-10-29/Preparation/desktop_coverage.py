"""Semantic desktop acceptance; process exit or a claimed flag is insufficient."""
def validate_coverage(value,expected,*,require_live):
    if value.get('passed') is not True or value.get('readOnly') is not True or value.get('coverageValidated') is not True:
        raise ValueError('desktop completion/coverage proof missing')
    if value.get('live') is not require_live or value.get('capturedFixtureOnly') is require_live:
        raise ValueError('desktop proof context differs')
    for field in ('modules','fieldbusNodes'):
        actual=value.get(field)
        wanted=expected[field]
        if not isinstance(actual,list) or not actual or len(actual)!=len(wanted) or set(actual)!=set(wanted):
            raise ValueError('desktop '+field+' coverage differs')
    shots=value.get('shots',[])
    projected=[{key:shot.get(key) for key in ('file','module','tab')} for shot in shots]
    if projected!=expected['shots']:
        raise ValueError('desktop surface traversal incomplete')
    if any(shot.get('link')!='live' or type(shot.get('rootCount')) is not int or shot['rootCount']<1 for shot in shots):
        raise ValueError('stale/empty desktop frame cannot be accepted')
    roots={name.split('.')[0] for name in expected['modules']}
    if value.get('refusedActions',0)<2*len(roots):
        raise ValueError('read-only refusal traversal incomplete')
    return True
