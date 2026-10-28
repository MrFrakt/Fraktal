"""Only the existing 31 genealogy vectors on the exact authorized V6.7 image."""
from pathlib import Path
import json,os,sys
D=Path(__file__).parent
sys.path.insert(0,str(D))
from qualification_session import authorize
authorize(json.loads((D/'authorization.json').read_bytes()))
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from fraktal_ab_genealogy_execute import main
if __name__=='__main__':raise SystemExit(main(expected_declaration='fraktal_ab_genealogy_s4_demo'))
