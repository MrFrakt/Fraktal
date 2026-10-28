from pathlib import Path
W = Path(__file__).parent
old = Path('C:/work/fraktal-ab-s4b-20261025/offline_01')
source = (old / 'test_session_ready_01.py').read_text(encoding='utf-8')
before = "W/'session_ready_template.py'"
assert source.count(before) == 1
source = source.replace(before, "W.parent/'session_01/session_ready.py'")
exec(compile(source, str(old / 'test_session_ready_01.py'), 'exec'), globals())
