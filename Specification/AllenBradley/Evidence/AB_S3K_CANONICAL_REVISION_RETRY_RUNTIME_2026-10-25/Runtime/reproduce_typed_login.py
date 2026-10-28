"""Offline causal reproduction with a synthetic account, never real credentials."""
from pathlib import Path
import dataclasses
import json
import sys

R = Path(__file__).parent
sys.path.insert(0, 'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import test_fraktal_ab_access as fixture
import fraktal_ab_access as access
import fraktal_ab_canonical_commands as commands
import fraktal_ab_mailbox as mb
import fraktal_ab_st_model as st

app = dataclasses.replace(fixture.APP, canonical_publication_stage=13)
rows = []
for legacy in (701, 12):
    c = fixture.controller()
    fixture.add_access(c, app)
    q = c.tags[mb.request_tag_name(app)]
    q.update(Sequence=legacy, Kind=mb.LOGIN, IntValue=access.LOGIN_PIN,
             User=fixture.string('tester', 32), Secret=fixture.string(fixture.PIN.decode(), 32))
    c.tags['FRK_Press_HmiLastSequence'] = 12
    c.tags[commands.work_tag(app)] = {'OwnerSequence': 12}
    c.run('\n'.join(access.login(app)))
    valid = c.tags[access.tag(app, 'Work')]['LoginValid']
    cyclic = st.parse('\n'.join(access.cyclic(app)))
    for unused in range((access.PIN_HASH_ROUNDS + 1) * access.HASH_BLOCK_SCANS):
        c.run(cyclic)
        if not c.tags[access.tag(app, 'State')]['LoginBusy']:
            break
    state = c.tags[access.tag(app, 'State')]
    rows.append(dict(legacySequence=legacy, ownerSequence=12, validAtStart=valid,
                     currentLevel=state['CurrentLevel'], loginFailed=state['LoginFailed'],
                     resultSequence=state['LoginResultSequence']))
assert rows[0]['currentLevel'] == 0 and rows[0]['validAtStart'] == 0
assert rows[1]['currentLevel'] == 4 and rows[1]['validAtStart'] == 1
record = dict(passed=True, reproduced=True, controllerAccess=False, realCredentialsUsed=False, rows=rows,
              explanation='LoginRequest copied the legacy Sequence; HmiLastSequence is the independent typed token. A sequence mismatch marks the correct synthetic PIN invalid before hashing.')
with (R / 'typed_login_reproduction_01.json').open('x') as out:
    json.dump(record, out, indent=2)
print(json.dumps(record))
