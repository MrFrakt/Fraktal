import difflib
from pathlib import Path
w=Path(__file__).resolve().parent
for line in difflib.unified_diff((w/'candidate_05/20_000_FB_DeclarationCylinder.scl').read_text('ascii').splitlines(),(w/'candidate_06/20_000_FB_DeclarationCylinder.scl').read_text('ascii').splitlines(),n=2):print(line)
