from pathlib import Path

W = Path(__file__).parent
source = (W / 'inspect_lookup_runtime_01.py').read_text(encoding='utf-8')
before = "D = W.parent / 'retry_lookup_01'"
assert source.count(before) == 1
source = source.replace(before, "D = W.parent / 'retry_reader_01'")
exec(compile(source, str(W / 'inspect_lookup_runtime_01.py'), 'exec'), {'__file__': __file__})
