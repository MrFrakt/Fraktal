from pathlib import Path
import sys,json
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from candidate_profile import configure,CANONICAL_SHA256
configure()
import fraktal_ab_genealogy_s3i_demo as demo
import fraktal_ab_canonical_publication as publication
import fraktal_ab_s3f_fixture_execute as fixture
import fraktal_ab_s3i_lifetime_execute as lifetime
import fraktal_ab_manifest as legacy
app=demo.application();header=publication.manifest_values(app)
assert app.canonical_type_manifest and app.canonical_table_driven
assert header['SchemaMinor']==4 and header['TypeAnnotationsCount']==137 and header['PathExceptionsCount']==2
assert fixture.expected_manifest(app)==header['ContentHash']
assert legacy.content_hash(app)=='6DEC4C1DC2F7F78A'
assert lifetime.ACD==CANONICAL_SHA256
assert json.loads((Path(__file__).parent/'authorization.json').read_bytes())['CurrentOwnerApproved'] is False
print(json.dumps(dict(passed=True,readOnly=True,controllerAccess=False,canonicalSha256=CANONICAL_SHA256,manifest=header['ContentHash'],stage=app.canonical_publication_stage,typeAnnotations=137,pathExceptions=2)))
