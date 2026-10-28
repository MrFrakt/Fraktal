import sys
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_s4b_equivalence as gate
import fraktal_ab_s2_equivalence as shared
if __name__=='__main__':raise SystemExit(shared.main(gate.run,description=gate.__doc__))
