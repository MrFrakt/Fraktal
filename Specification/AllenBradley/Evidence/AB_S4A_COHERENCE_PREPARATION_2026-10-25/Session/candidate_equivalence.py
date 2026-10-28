"""Migration-only value equivalence, independent of shipping small-group proof."""
import sys
from functools import partial
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_genealogy_s4_demo as candidate
import fraktal_ab_s3k_equivalence as oracle
import fraktal_ab_s2_equivalence as shared
if __name__=='__main__':raise SystemExit(shared.main(partial(oracle.run,candidate_factory=candidate.application),description=__doc__))
