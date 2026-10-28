from pathlib import Path
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
source=(W/'array_tiers_regression_test.dart').read_text(encoding='utf-8')
for before,after in (
 ("../../fraktal-ab-s4b-20261025/hmi_verify_01/test/cip_publication_test.dart","cip_publication_test.dart"),
 ("../../fraktal-ab-s4b-20261025/hmi_verify_01/test/cip_read_plan_test.dart","cip_read_plan_test.dart")):
    assert source.count(before)==1
    source=source.replace(before,after)
path=R/'FraktalCore/HMI/test/cip_array_tiers_test.dart'
with path.open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Added five array-tier regressions from recorded native fixtures.')
