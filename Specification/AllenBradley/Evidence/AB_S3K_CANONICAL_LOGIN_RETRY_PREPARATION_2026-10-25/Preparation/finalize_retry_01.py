"""Pin the offline login correction into an unapproved retry session."""
from pathlib import Path
import hashlib
import json

W = Path(__file__).parent
R = W.parent / 'retry_login_01'
OLD = W.parent / 'retry_revision_01'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest().upper()
capacity = json.loads((W / 'capacity_auto_02.json').read_bytes())
assert capacity['VerifiedFit'] and capacity['SourceUnchanged'] and capacity['ReviewProcessClosed']
pin = sha(W / 'command_a_02.ACD')
source = sha(W / 's3k_command_a_02.L5X')
assert pin == capacity['CanonicalSha256']


def write(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)


for origin, target in [('command_a_02.ACD', 's3k_command_a.ACD'), ('s3k_command_a_02.L5X', 's3k_command_a.L5X'),
                       ('capacity_auto_02.json', 'capacity_review.json'), ('prepared_compare_02.log', 'canonical_prepared_compare.json')]:
    write(R / target, (W / origin).read_bytes())
write(R / 'canonical.sha256', (pin + '\n').encode())
write(R / 'genealogy.sha256', (OLD / 'genealogy.sha256').read_bytes())
driver = R / 'retry_session.py'
text = driver.read_text()
assert text.count("PIN = 'UNPREPARED'") == text.count("SOURCE = 'UNPREPARED'") == 1
text = text.replace("PIN = 'UNPREPARED'", "PIN = '" + pin + "'")
text = text.replace("SOURCE = 'UNPREPARED'", "SOURCE = '" + source + "'")
assert text.index("run('restore_original_medium'") < text.index("run('baseline_regressions'")
driver.write_text(text)
template = R / 'authorization.template.json'
value = json.loads(template.read_bytes())
assert not value['CurrentOwnerApproved'] and not (R / 'authorization.json').exists()
value.update(CanonicalSha256=pin, SourceSha256=source,
             OwnerCapacityConfirmed={key: capacity[key] for key in ('UsedStandardBlocks', 'AvailableBlocks', 'TotalBlocks', 'DisplayedUsagePercent')})
template.write_text(json.dumps(value, indent=2) + '\n')
verify = (W.parent / 'compatibility_fix_01/verify_retry_01.py').read_text()
verify = verify.replace("W.parent / 'retry_revision_01'", "W.parent / 'retry_login_01'")
verify = verify.replace("W.parent / 'download_01/preflight_final_01_exit.json'", "W.parent / 'retry_revision_01/preflight_final_exit.json'")
verify = verify.replace("prior = Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c/preflight.json')", "prior = W.parent / 'retry_revision_01/preflight.json'")
verify = verify.replace('retry_no_approval_02.log', 'retry_no_approval_01.log').replace('retry_checks_02.json', 'retry_checks_01.json')
write(W / 'verify_retry_01.py', verify.encode())
with (W / 'retry_prepared_01.json').open('x') as stream:
    json.dump(dict(passed=True, approved=False, controllerOperations=0, canonicalSha256=pin, sourceSha256=source,
                   rollbackRestoresOriginalHostDocuments=True), stream, indent=2)
print(json.dumps(dict(prepared=True, canonicalSha256=pin, sourceSha256=source, approved=False)))
