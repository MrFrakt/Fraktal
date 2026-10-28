from pathlib import Path
W=Path(__file__).parent
source=Path('C:/work/fraktal-ab-s4b-20261025/offline_01/compatibility_generated_01.py').read_text(encoding='utf-8')
exec(compile(source,'compatibility_generated_01.py','exec'),{'__file__':__file__})
