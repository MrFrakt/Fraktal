"""Run only the fixed R1/R2 candidate apparatus; no new write vectors."""
from pathlib import Path
import importlib,os,sys
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from candidate_profile import configure
configure()
mode=sys.argv.pop(1)
if mode=='fixture':
    from fraktal_ab_s3i_fixture_execute import main
elif mode=='lifetime':
    from fraktal_ab_s3i_lifetime_execute import main
elif mode=='equivalence':
    import fraktal_ab_s3i_equivalence as gate
    import fraktal_ab_s2_equivalence as shared
    def main():return shared.main(gate.run,description=gate.__doc__)
else:raise ValueError('fixed candidate mode required')
raise SystemExit(main())
