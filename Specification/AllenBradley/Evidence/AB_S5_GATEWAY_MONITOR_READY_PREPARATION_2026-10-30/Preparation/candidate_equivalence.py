from functools import partial
import sys
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_s4b_equivalence as gate
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_genealogy_s4b_owner_demo as candidate
if __name__=='__main__':raise SystemExit(shared.main(partial(gate.run,application_factory=candidate.application),description=gate.__doc__))
