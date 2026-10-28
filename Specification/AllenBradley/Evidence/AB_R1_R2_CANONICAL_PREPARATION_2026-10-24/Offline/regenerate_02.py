from pathlib import Path
import hashlib, json, os, sys
from dataclasses import replace
from unittest.mock import patch
R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';W=Path(__file__).parent
sys.path.insert(0,str(T));os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
import fraktal_ab_genealogy_s3i_demo as demo
import fraktal_ab_s3i_native_checks as native
app=replace(demo.application(),canonical_table_driven=True,canonical_type_manifest=True)
with patch.object(demo,'application',return_value=app):
 report=native.generate(Path('C:/work/echo38_5580_seed.L5X'),W/'s3i_r1_r2_regen_02.L5X')
(W/'generation_regen_02.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
