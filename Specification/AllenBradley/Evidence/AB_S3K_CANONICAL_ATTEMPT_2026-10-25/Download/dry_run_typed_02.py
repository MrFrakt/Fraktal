"""Offline dry run: encode every typed vector with the live Templates, execute the generated ingress.

No controller access. The capture is the read-only generic_capture_02 taken from
the downloaded image; the ST model executes the exact generated ingress/resolver.
"""
from pathlib import Path
import gzip, json, struct, sys, tempfile
ROOT = Path('C:/Users/SoftIndVM/Fraktal'); D = Path(__file__).parent
sys.path.insert(0, str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_canonical_commands as commands
import fraktal_ab_canonical_reader as reader
import fraktal_ab_command_binding as binding
import fraktal_ab_config as config
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_part_execute as guarded
import fraktal_ab_s3k_fixture_execute as fixture
import test_fraktal_ab_canonical_commands as model

capture = json.loads(gzip.decompress((D/'generic_capture_02.json.gz').read_bytes()))
descriptor = capture['manifest']['commandBindings'][0]
symbols = {s['name']: s for s in capture['symbols']}
handle = symbols[descriptor['PayloadSymbol']]['handle']
rows = []

model.IngressTests.setUpClass()
case = model.IngressTests('test_first_scan_does_not_replay_visible_commit')
app = case.app
ordinal, record, member = next(v for v in gen.editable_values(app)
    if v[1].station_cfg and v[2].kind != 'boolean' and v[2].minimum < v[2].maximum)
REV = 123


def to_model(decoded):
    out = {k: decoded[k] for k in binding.HEADER}
    args = {}
    for n, v in decoded['Arguments'].items():
        if n in binding.WIDTHS:
            raw = bytes.fromhex(v['bytes']); data = [0]*binding.WIDTHS[n]; data[:len(raw)] = raw
            args[n] = dict(LEN=v['LEN'], DATA=data)
        else:
            args[n] = v
    out['Arguments'] = args
    return out


def run(label, kind, *, token, staged=None, prior=100, expect_error, check=None, **supplied):
    case.setUp()
    case.tags[__import__('fraktal_ab_canonical_publication').header_tag(app)]['ConfigRevision'] = capture['manifest']['configRevision']
    case.tags[app.name]['Status']['ConfigRev'] = REV
    case.work.update(CoreSerial=prior, LastCoreSeen=prior)
    if staged is not False:
        plan = binding.write_plan(capture, descriptor, fixture.arguments(Kind=kind, **supplied),
                                  (token if staged is None else staged) & 0xffffffff, connection_bytes=4000)
        assert len(plan.payload_request) + 110 <= 4000 and plan.payload_bytes == 784
        at = 2 + plan.payload_request[1]*2
        assert struct.unpack_from('<HHH', plan.payload_request, at) == (0x2a0, symbols and next(
            t for t in capture['templates'] if t['handle'] == handle)['structureHandle'], 1)
        raw = plan.payload_request[at+6:]
        regions = fixture.string_regions(raw, capture, descriptor['PayloadSymbol'], ('Secret', 'TextValue'))
        assert all(len(data) == binding.WIDTHS[n] for n, (length, data) in regions.items())
        case.payload.update(to_model(reader.decode_record(raw, handle, capture['templates'])))
    case.tags[commands.commit_tag(app)] = fixture.signed(token)
    case.plc.run(case.ingress)
    assert case.work['Error'] == expect_error, (label, case.work['Error'], expect_error)
    if check: check()
    wiped = all(case.payload['Arguments'][n]['LEN'] == 0 and not any(case.payload['Arguments'][n]['DATA']) for n in ('Secret', 'TextValue'))
    assert wiped, label
    rows.append(dict(vector=label, error=case.work['Error'], wiped=wiped))


def assert_equal(a, b):
    assert a == b, (a, b)


run('query_accepted', mb.QUERY_CONFIG, token=101, expect_error=0, IntValue=0, DurationMs=0)
run('release_report_accepted', mb.RELEASE_START, token=101, expect_error=0)
run('backward_serial_stale', mb.QUERY_CONFIG, token=99, staged=False, expect_error=commands.STALE_SERIAL)
run('staged_sequence_mismatch', mb.QUERY_CONFIG, token=102, staged=101, expect_error=1)
common = dict(TargetPath=app.name, NameValue=member.write_key)
run('stale_revision', mb.WRITE_CONFIG, token=101, expect_error=commands.STALE_REVISION, IntValue=REV ^ 1, TextValue='0', **common)
run('foreign_root', mb.WRITE_CONFIG, token=101, expect_error=commands.FOREIGN_ROOT, TargetPath=fixture.FOREIGN_ROOT,
    NameValue=member.write_key, IntValue=REV, TextValue='0')
run('unknown_key_refused_by_owner', mb.WRITE_CONFIG, token=101, expect_error=0, TargetPath=app.name, NameValue=fixture.UNKNOWN_KEY,
    IntValue=REV, TextValue='0', check=lambda: assert_equal(case.request['IntValue'], 0))
run('fractional_value_invalid', mb.WRITE_CONFIG, token=101, expect_error=1, IntValue=REV, TextValue='1.5', **common)
run('config_write_accepted', mb.WRITE_CONFIG, token=101, expect_error=0, IntValue=REV, TextValue=' 2501.0 ', **common,
    check=lambda: assert_equal((case.request['IntValue'], case.request['BoolValue']), (ordinal, 2501)))
run('login_accepted', mb.LOGIN, token=0, prior=0xffffffff, expect_error=0, User='fixture', Secret='not-a-real-pin',
    check=lambda: assert_equal(case.request['Secret']['LEN'], len('not-a-real-pin')))


# Authorization: the current download-only record must refuse request cases.
current = D/'authorization.json'
pin = json.loads(current.read_text())['CanonicalSha256']
try:
    fixture.authorize(current, pin); refused = False
except guarded.FixtureRefused:
    refused = True
assert refused
draft = dict(json.loads(current.read_text()), MailboxOrTagWritesAuthorized=True)
with tempfile.TemporaryDirectory() as t:
    p = Path(t)/'a.json'; p.write_text(json.dumps(draft))
    fixture.authorize(p, pin)
    for wrong in (dict(draft, Serial='00000000'), dict(draft, FaultClearAuthorized=True), dict(draft, CanonicalSha256='0'*64)):
        p.write_text(json.dumps(wrong))
        try:
            fixture.authorize(p, pin); raise AssertionError('authorization accepted a wrong record')
        except guarded.FixtureRefused:
            pass
result = dict(passed=True, vectors=rows, currentDownloadAuthorizationRefusesRequestCases=True,
              structureHandle=next(t for t in capture['templates'] if t['handle'] == handle)['structureHandle'], payloadBytes=784)
with (D/'dry_run_typed_02.json').open('x') as out: json.dump(result, out, indent=2)
print(json.dumps(dict(passed=True, vectors=len(rows))))
