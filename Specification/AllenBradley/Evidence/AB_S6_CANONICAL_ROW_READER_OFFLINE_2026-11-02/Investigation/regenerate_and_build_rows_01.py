"""New append-only output names for the unchanged accepted-source build gate."""
from pathlib import Path
original = Path(__file__).with_name('regenerate_and_build.py').read_text(encoding='utf-8')
assert '_01' in original and '_02' not in original
exec(compile(original.replace('_01', '_02'), __file__, 'exec'))
