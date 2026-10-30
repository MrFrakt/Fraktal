from pathlib import Path
import shutil
W=Path(__file__).parent;OLD=Path('C:/work/fraktal-ab-s4b-q-20261028/session_01')
for name in ['qualification_session_v2.py','readonly_stages.py','session_ready.py','authorization.template.json','workflow_checks_01.py']:
    raw=(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),W.as_posix())
    if name=='qualification_session_v2.py':
        before="""        run('candidate_regressions', PY, D / 'candidate_regressions_v2.py', '--execute-fixture',
            '--expect-serial', '601FC87B', '--credential-file', CREDENTIAL,
            '--output', D / 'candidate_regressions.json')
        from readonly_stages import execute_readonly_stages
        read_errors=[]
"""
        after="""        read_errors=[]
        try:
            run('candidate_regressions', PY, D / 'candidate_regressions_v2.py', '--execute-fixture',
                '--expect-serial', '601FC87B', '--credential-file', CREDENTIAL,
                '--output', D / 'candidate_regressions.json')
        except Exception as error:
            # The fixture stops writes and restores its state before returning.
            # An observer failure must not bypass independent read-only gates.
            read_errors.append(dict(stage='candidate_regressions',error=f'{type(error).__name__}: {error}'))
        run('guard_readonly', PY, D / 'scripts/guard_echo.py')
        from readonly_stages import execute_readonly_stages
"""
        assert raw.count(before)==1;raw=raw.replace(before,after)
    if name=='workflow_checks_01.py':
        assert "if failure in readonly or failure is None:" in raw
        raw=raw.replace("if failure in readonly or failure is None:","if failure in readonly or failure in ['candidate_regressions',None]:")
    with (W/name).open('x',encoding='utf-8') as f:f.write(raw)
print('Prepared P5 helper correction; no processes or controller calls')
