"""Fixed opt-in engineering fixture profile, not a runtime client mapping."""
from dataclasses import replace
from pathlib import Path
import os
CANONICAL_SHA256 = 'D170F1E3BA9CCBF4FB00CF265FB43E43FC40FFB82CDF95322C48570D33FF906C'
def configure():
    os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
    assert (Path(__file__).parent/'canonical.sha256').read_text().strip()==CANONICAL_SHA256
    import fraktal_ab_genealogy_s3i_demo as demo
    if not getattr(demo.application,'r1_r2_profile',False):
        original=demo.application
        def selected():return replace(original(),canonical_type_manifest=True,canonical_table_driven=True)
        selected.r1_r2_profile=True
        demo.application=selected
    import fraktal_ab_s3i_lifetime_execute as lifetime
    lifetime.ACD=CANONICAL_SHA256
