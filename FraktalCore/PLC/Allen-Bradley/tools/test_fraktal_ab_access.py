"""Execute the emitted access authority, including its real SHA-256 code."""
import copy
import dataclasses
import hashlib
import json
import random
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import fraktal_ab_access as access
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_gateway as gw
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_press_demo as demo
import fraktal_ab_projection as projection
import fraktal_ab_station_template as template
import fraktal_ab_st_model as st

SALT = bytes(range(16))
PIN = b'unit-test-only'
USER = access.User('tester', 4, SALT.hex(), access.pin_hash(SALT, PIN).hex())
APP = dataclasses.replace(demo.application(), access_users=(USER,))


def add_access(c, app=APP, real_sha=False):
    if app.access_users is None:
        return
    for name, members in (('State', access.state_members(app)), ('Audit', access.audit_members()), ('Work', access.work_members())):
        c.tags[access.tag(app, name)] = st.structure(members)
    c.tags[access.tag(app, 'Users')] = access.user_data(app.access_users)
    import fraktal_ab_shelving as shelving
    c.tags[shelving.tag(app)] = st.structure(shelving.members())
    rows = mf.content(app)
    width = mf.key_string_length(app)
    for table in ('Modules', 'Rationalization', 'Localization'):
        c.tags[f'FRK_{app.name}_Mf{table}'] = [
            {k: string(v, width) if isinstance(v, str) else v
             for k, v in row.items()} for row in rows[table]]
    c.tags[mf.header_tag(app)] = dict(Valid=1, Truncated=0,
        **{table + 'Count': len(rows[table]) for table in rows})
    import fraktal_ab_data_access as data
    c.tags[data.tag(app, 'Policy')] = data.policy_data(app)
    c.tags[data.tag(app, 'Levels')] = st.structure(data.levels_members(app))
    c.tags[data.tag(app, 'Work')] = st.structure(data.work_members())
    c.tags[access.tag(app, 'RoundConstants')] = [access._signed(n) for n in access.K]
    request = {n: {'LEN': 0, 'DATA': [0] * width} if k == mb.STRING_MEMBER else 0 for n, k, width, _ in mb.REQUEST_MEMBERS}
    if app.config_sets:
        import fraktal_ab_sets as sets
        request['ConfigSet'] = st.structure(sets.request_members())
    c.tags[access.tag(app, 'LoginRequest')] = request
    c.calls['CPS'] = st.cps_structure
    compiled = st.parse('\n'.join(access.sha_logic(app))) if real_sha else None
    helpers = {name: st.parse('\n'.join(lines)) for name, lines in access.routines(app) if name != access.tag(app, 'Sha256')}
    helpers[data.tag(app, 'ResolveLevel')] = st.parse('\n'.join(data.resolver(app)))
    helpers[data.tag(app, 'RefreshLevels')] = st.parse('\n'.join(data.refresh(app)))
    helpers[shelving.routine_name(app)] = st.parse('\n'.join(shelving.handler(app)))
    helpers[gen.start_release_routine_name(app)] = st.parse('\n'.join(gen.start_release_logic(app)))
    import fraktal_ab_config as config
    if gen.editable_values(app):
        helpers[config.audit_routine_name(app)] = st.parse('\n'.join(config.audit_logic(app)))
    previous = c.calls.get('JSR')
    def jsr(plc, args):
        name = args[0][1][0][1]
        if name in helpers:
            return plc.run(helpers[name])
        if name != access.tag(app, 'Sha256'):
            if previous:
                return previous(plc, args)
            raise st.StError('unexpected JSR ' + name)
        if compiled is not None:
            plc.run(compiled)
        else:
            # Provider/control tests use an independent compression oracle.
            # Crypto tests below separately execute the emitted compression,
            # plus one complete 257-block login with no oracle substitution.
            w = plc.tags[access.tag(app, 'Work')]
            length = int.from_bytes(bytes(w['Buffer'][56:64]), 'big') // 8
            if w['HashPhase'] == 0:
                w['H'] = list(hashlib.sha256(bytes(w['Buffer'][:length])).digest()[:8])
                w['_oracle_digest'] = list(hashlib.sha256(bytes(w['Buffer'][:length])).digest())
                w['Buffer'][:] = [0] * 64
                w['HashDone'], w['HashPhase'], w['HashCursor'] = 0, 1, 0
            elif w['HashPhase'] == 1:
                if w['HashCursor'] not in range(0, 64, access.HASH_CHUNK):
                    w['LoginValid'], w['Remaining'], w['HashDone'] = 0, 0, 1
                else:
                    w['HashCursor'] += access.HASH_CHUNK
                    if w['HashCursor'] == 64:
                        w['HashPhase'] = 2
            elif w['HashPhase'] == 2:
                w['Digest'] = w.pop('_oracle_digest')
                w['Words'][:] = [0] * 64
                w['HashPhase'], w['HashDone'] = 0, 1
            else:
                w['LoginValid'], w['Remaining'], w['HashDone'] = 0, 0, 1
    c.calls['JSR'] = jsr


def controller(app=APP, real_sha=False):
    from test_fraktal_ab_manual import Bench
    bench = Bench()
    c = bench.plc
    add_access(c, app, real_sha)
    c.tags[f'FRK_{app.name}_NowDate'] = 20261002
    c.tags[f'FRK_{app.name}_NowTime'] = 120000000
    import fraktal_ab_sets as sets
    c.tags[mb.request_tag_name(app)]['ConfigSet'] = st.structure(sets.request_members())
    c.tags[sets.staged_tag(app)] = st.structure(sets.request_members())
    c.calls['CPS'] = st.cps_structure
    for name in sets.scratch_names(app):
        c.tags[name] = 0
    import fraktal_ab_config as config
    c.tags[config.candidate_tag(app)] = 0
    c.tags[config.audit_tag(app)] = st.structure(config.audit_members())
    c.tags[gen.model_cfg_tag(app)] = [st.structure(ms) for ms in gen.model_cfg_elements(app)]
    c.tags[gen.profiler_tag(app)] = st.structure(gen.profiler_members(app))
    c.tags[gen.alarm_ring_tag(app)] = st.structure(gen.alarm_ring_members())
    c.tags['FRK_Press_ForcePermitted'] = 1
    c.tags['FRK_Press_ForceOutputs'] = 1
    c.tags['FRK_Press_ForceMask'] = 0
    c.tags['FRK_Press_ForceValue'] = 0
    c.tags['FRK_Press_Unit']['Mode'] = app.manual_mode
    c.run('\n'.join(gen.start_release_logic(app)))
    return c


def string(text, width):
    return {'LEN': len(text), 'DATA': list(text.encode('ascii')) + [0] * (width - len(text))}


def request(c, kind, app=APP, **arguments):
    req = c.tags[mb.request_tag_name(app)]
    sequence = req['Sequence'] + 1
    for n, k, width, _ in mb.REQUEST_MEMBERS:
        req[n] = string(arguments.get(n, ''), width) if k == mb.STRING_MEMBER else arguments.get(n, 0)
    req.update(Kind=kind, Sequence=sequence)
    c.run(st.parse('\n'.join(mb.handler_logic(app))))
    return c.tags[mb.response_tag_name(app)]


def finish(c, app=APP):
    code = st.parse('\n'.join(mb.handler_logic(app)))
    for _ in range((access.PIN_HASH_ROUNDS + 1) * access.HASH_BLOCK_SCANS):
        c.run(code)
        if not c.tags[access.tag(app, 'State')]['LoginBusy']:
            break
    else:
        raise AssertionError('login exceeded its declared scan budget')
    return c.tags[access.tag(app, 'State')]


def compress(c, app=APP):
    code = st.parse('\n'.join(access.sha_logic(app)))
    for _ in range(access.HASH_BLOCK_SCANS):
        c.run(code)


def observe_hash_blocks(c, app=APP):
    blocks = []
    original_jsr = c.calls['JSR']
    def jsr(plc, args):
        is_hash = args[0][1][0][1] == access.tag(app, 'Sha256')
        result = original_jsr(plc, args)
        if is_hash and plc.tags[access.tag(app, 'Work')]['HashDone']:
            blocks.append(bytes(plc.tags[access.tag(app, 'Work')]['Digest']))
        return result
    c.calls['JSR'] = jsr
    return blocks


class ExactDint(st.Controller):
    """Reject overflow and non-exact divides instead of hiding Logix rounding."""
    def eval(self, node):
        if node[0] == 'bin' and node[1] in ('+', '-', '*', '/'):
            a, b = self.eval(node[2]), self.eval(node[3])
            if node[1] == '/':
                if not b or a % b:
                    raise AssertionError('SHA integer division is not exact')
            else:
                value = {'+': lambda: a + b, '-': lambda: a - b,
                         '*': lambda: a * b}[node[1]]()
                if not -2147483648 <= value <= 2147483647:
                    raise AssertionError('SHA signed intermediate overflow')
        return super().eval(node)


def login(c, app=APP, user='tester', pin=PIN.decode()):
    request(c, mb.LOGIN, app, User=user, Secret=pin)
    return finish(c, app)


class Cryptography(unittest.TestCase):
    def test_provisioning_hash_is_initial_salted_hash_plus_256_fixed_rounds(self):
        expected = hashlib.sha256(SALT + PIN).digest()
        for _ in range(256):
            expected = hashlib.sha256(expected + SALT).digest()
        self.assertEqual(access.pin_hash(SALT, PIN), expected)
        c = controller()
        request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        self.assertEqual(c.tags[access.tag(APP, 'Work')]['Remaining'], 257)

    def test_compression_does_not_overflow_signed_dint_at_any_intermediate(self):
        base = controller(real_sha=True)
        c = ExactDint(base.tags, base.calls)
        w = c.tags[access.tag(APP, 'Work')]
        for message in (b'abc', b'\xff' * 48, bytes(range(48))):
            w['Buffer'][:] = [0] * 64
            w['Buffer'][:len(message)] = message
            w['Length'] = len(message)
            c.run('\n'.join(access._pad(APP, access.tag(APP, 'Work') + '.Length')))
            compress(c)
            self.assertEqual(bytes(w['Digest']), hashlib.sha256(message).digest())

    def test_emitted_sha_against_hashlib_and_published_vectors(self):
        c = controller(real_sha=True)
        w = c.tags[access.tag(APP, 'Work')]
        for message in (b'', b'abc', b'\x00' * 48, bytes(range(48)), b'a' * 48, SALT + b'p', SALT + b'x' * 32):
            w['Buffer'][:] = [0] * 64
            w['Buffer'][:len(message)] = message
            w['Length'] = len(message)
            c.run('\n'.join(access._pad(APP, access.tag(APP, 'Work') + '.Length')))
            compress(c)
            self.assertEqual(bytes(w['Digest']), hashlib.sha256(message).digest(), message)
            self.assertEqual(w['Buffer'], [0] * 64)
            self.assertEqual(w['Words'], [0] * 64)

    def test_modular_add_never_uses_signed_overflow(self):
        base = controller()
        c = ExactDint(base.tags, base.calls)
        w = c.tags[access.tag(APP, 'Work')]
        rng = random.Random(1804)
        cases = [(-1, -1), (2147483647, 1), (-2147483648, -2147483648),
                 (-1, -1, -1, -1, -1), (123456789, -987654321),
                 (2147483647,) * 5, (-2147483648,) * 5]
        cases += [tuple(rng.randrange(-2147483648, 2147483648) for _ in range(rng.randrange(1, 6))) for _ in range(100)]
        for terms in cases:
            refs = []
            for i, value in enumerate(terms):
                w['Temp'][i] = value
                refs.append(access.tag(APP, 'Work') + f'.Temp[{i}]')
            dest = access.tag(APP, 'Work') + '.Digest[0]'
            c.run('\n'.join(access._add(APP, dest, refs)))
            self.assertEqual(w['Digest'][0], access._signed(sum(terms) & 0xffffffff))
        code = '\n'.join(access.sha_logic(APP))
        self.assertNotIn('SHR(', code)
        self.assertNotIn('BTD(', code)
        self.assertNotIn('BTDT(', code)
        self.assertNotIn('JSR(', code)

    def test_every_rotate_and_logical_shift_matches_unsigned_bit_oracle(self):
        base = controller()
        c = ExactDint(base.tags, base.calls)
        w = c.tags[access.tag(APP, 'Work')]
        source, dest = access.tag(APP, 'Work') + '.Temp[0]', access.tag(APP, 'Work') + '.Temp[1]'
        rng = random.Random(256)
        values = [0, -1, -2147483648, 2147483647]
        values += [access._signed(1 << bit) for bit in range(32)]
        values += [rng.randrange(-2147483648, 2147483648) for _ in range(40)]
        for amount in range(1, 32):
            for logical in (False, True):
                code = st.parse('\n'.join(access._rotate(APP, dest, source, amount, logical)))
                for value in values:
                    w['Temp'][0] = value
                    c.run(code)
                    unsigned = value & 0xffffffff
                    expected = unsigned >> amount
                    if not logical:
                        expected |= (unsigned << (32 - amount)) & 0xffffffff
                    self.assertEqual(w['Temp'][1], access._signed(expected), (value, amount, logical))

    def test_complete_257_hash_login_executes_the_real_compression(self):
        c = controller(real_sha=True)
        blocks = observe_hash_blocks(c)
        request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        code = st.parse('\n'.join(mb.handler_logic(APP)))
        for scan in range(257 * access.HASH_BLOCK_SCANS - 1):
            before = len(blocks)
            c.run(code)
            self.assertLessEqual(len(blocks) - before, 1)
        held = c.tags[access.tag(APP, 'State')]
        self.assertEqual((held['CurrentLevel'], held['LoginFailed'], held['LoginBusy']), (4, 0, 0))
        expected = [hashlib.sha256(SALT + PIN).digest()]
        for _ in range(256):
            expected.append(hashlib.sha256(expected[-1] + SALT).digest())
        self.assertEqual(blocks, expected)

    def test_hash_input_wiped_then_at_most_eight_rounds_per_scan(self):
        c = controller(real_sha=True)
        request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        w = c.tags[access.tag(APP, 'Work')]
        self.assertFalse(any(w['Buffer']))
        self.assertEqual(w['HashCursor'], 0)
        code = st.parse('\n'.join(mb.handler_logic(APP)))
        for cursor in range(8, 65, 8):
            c.run(code)
            self.assertEqual(w['HashCursor'], cursor)
            self.assertFalse(w['HashDone'])
        c.run(code)
        self.assertEqual(bytes(w['Digest']), hashlib.sha256(SALT + PIN).digest())
        self.assertFalse(any(w['Words']))
        self.assertEqual(w['Remaining'], 256)

    def test_corrupt_remaining_hash_count_fails_closed(self):
        for remaining in (-1, 0, 258, 2147483647):
            c = controller(real_sha=True)
            request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
            w = c.tags[access.tag(APP, 'Work')]
            w['Remaining'] = remaining
            c.run('\n'.join(mb.handler_logic(APP)))
            s = c.tags[access.tag(APP, 'State')]
            self.assertEqual((s['CurrentLevel'], s['LoginFailed'], s['LoginBusy']), (0, 1, 0))
            self.assertFalse(any(w['Words']))
            self.assertFalse(any(w['Buffer']))

    def test_request_on_completion_scan_cannot_double_the_hash_work(self):
        c = controller()
        blocks = observe_hash_blocks(c)
        request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        code = st.parse('\n'.join(mb.handler_logic(APP)))
        for _ in range(257 * access.HASH_BLOCK_SCANS - 2):
            c.run(code)
        before = len(blocks)
        answer = request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        self.assertEqual(len(blocks) - before, 1)
        self.assertEqual((answer['Accepted'], answer['DiagnosticKey']),
                         (0, mf.numeric_key(APP, access.BUSY)))
        held = c.tags[access.tag(APP, 'State')]
        self.assertEqual((held['CurrentLevel'], held['LoginFailed'], held['LoginBusy']), (4, 0, 0))
        self.assertFalse(any(c.tags[mb.request_tag_name(APP)]['Secret']['DATA']))
        # A following scan has a fresh budget and can consume another login.
        self.assertEqual(request(c, mb.LOGIN, User='tester', Secret=PIN.decode())['Accepted'], 1)

    def test_cancellation_wipes_private_work_between_hashes(self):
        for scans in (0, 1, 3, 255):
            c = controller(real_sha=True)
            request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
            code = st.parse('\n'.join(mb.handler_logic(APP)))
            for _ in range(scans):
                c.run(code)
            request(c, mb.LOGOUT)
            w = c.tags[access.tag(APP, 'Work')]
            self.assertEqual(w['Remaining'], 0)
            for name in ('Buffer', 'Words', 'Digest', 'Salt', 'User', 'H', 'V', 'Temp'):
                self.assertFalse(any(w[name]), name)


class AssistedLogin(unittest.TestCase):
    def writes(self, user='tester', pin=PIN.decode(), **extra):
        values = dict(Kind=mb.LOGIN, User=user, Secret=pin, IntValue=0, TextValue='', Sequence=17)
        values.update(extra)
        return [('Press/HmiRequest/' + n, 'string' if n in ('User', 'Secret', 'TextValue') else 'int32', v)
                for n, v in values.items() if n != 'Sequence'] + [('Press/HmiRequest/Sequence', 'int32', 17)]

    def assisted(self, c, user='tester', pin=PIN.decode()):
        writes = access.prepare_login(APP, self.writes(user, pin))
        values = {p.rsplit('/', 1)[-1]: v for p, _, v in writes}
        return request(c, mb.LOGIN, User=values['User'], Secret=values['Secret'],
                       IntValue=values['IntValue'], TextValue=values['TextValue'])

    def test_gateway_derives_preimage_and_never_sends_registration_hash_or_pin(self):
        writes = access.prepare_login(APP, self.writes())
        values = {p.rsplit('/', 1)[-1]: v for p, _, v in writes}
        self.assertEqual(writes[-1], self.writes()[-1])
        self.assertEqual(values['Secret'], '')
        self.assertEqual(values['IntValue'], access.LOGIN_PREHASH)
        preimage = bytes.fromhex(values['TextValue'])
        self.assertNotEqual(preimage.hex(), USER.pin_hash)
        self.assertEqual(hashlib.sha256(preimage + SALT).hexdigest(), USER.pin_hash)
        self.assertNotIn(PIN.decode(), str(writes))

    def test_fast_login_executes_one_real_bounded_block_and_matches_private_level(self):
        c = controller(real_sha=True)
        blocks = observe_hash_blocks(c)
        self.assertEqual(self.assisted(c)['Accepted'], 1)
        req = c.tags[mb.request_tag_name(APP)]
        for label in ('Secret', 'TextValue'):
            self.assertFalse(any(req[label]['DATA']))
            self.assertFalse(any(c.tags[access.tag(APP, 'LoginRequest')][label]['DATA']))
        code = st.parse('\n'.join(mb.handler_logic(APP)))
        for _ in range(access.HASH_BLOCK_SCANS - 1):
            c.run(code)
        held = c.tags[access.tag(APP, 'State')]
        self.assertEqual((held['CurrentLevel'], held['LoginFailed'], held['LoginBusy'], held['LoginResultSequence']), (4, 0, 0, 1))
        self.assertEqual(blocks, [bytes.fromhex(USER.pin_hash)])

    def test_fast_login_level_is_always_the_private_registration_level(self):
        for level in range(1, 5):
            app = dataclasses.replace(APP, access_users=(dataclasses.replace(USER, level=level),))
            c = controller(app, real_sha=True)
            self.assisted(c)
            held = finish(c, app)
            self.assertEqual(held['CurrentLevel'], level)

    def test_unknown_wrong_and_stored_hash_as_credential_fail_preserving_existing_session(self):
        for user, proof in (('tester', access.pin_prehash(SALT, b'wrong').hex()),
                            ('tester', USER.pin_hash), ('unknown', access.pin_prehash(bytes(16), PIN).hex()),
                            ('tester', 'g' * 64), ('tester', 'f' * 63)):
            c = controller(real_sha=True)
            self.assisted(c)
            finish(c)
            blocks = observe_hash_blocks(c)
            request(c, mb.LOGIN, User=user, Secret='', IntValue=access.LOGIN_PREHASH, TextValue=proof)
            held = finish(c)
            self.assertEqual((held['CurrentLevel'], held['LoginFailed'], held['LoginBusy']), (4, 1, 0))
            self.assertEqual(bytes(held['UserBytes'][:held['UserLength']]), b'tester')
            self.assertEqual(held['LoginResultSequence'], 2)
            self.assertEqual(len(blocks), 1)

    def test_web_client_cannot_supply_the_derived_profile_or_overlong_pin(self):
        for extra in ({'IntValue': 1}, {'Secret': 'x' * 33}, {'Secret': ''}, {'Secret': '\u00e9'}):
            with self.assertRaises(ValueError):
                access.prepare_login(APP, self.writes(**extra))

    def test_gateway_writer_uses_assistance_before_cip_commit(self):
        writer = gw.MailboxWriter('unused', 0, '7036B510', app=APP, set_store=object())
        comm = mock.Mock()
        comm.Write.return_value = mock.Mock(Status='Success')
        comm.Read.return_value = mock.Mock(Status='Success', Value=17)
        self.assertTrue(writer._write_base(comm, self.writes()))
        actual = comm.Write.call_args_list
        self.assertEqual(actual[-1].args, (mb.request_tag_name(APP) + '.Sequence', 17))
        self.assertNotIn(list(PIN), [call.args[1] for call in actual])
        import fraktal_ab_mailbox_frame as frame
        decoded = frame.decode(APP, actual[0].args[1])
        self.assertEqual(decoded['IntValue'], access.LOGIN_PREHASH)
        self.assertEqual(decoded['Secret'], '')

    def test_gateway_checks_live_provider_profile_before_any_credential_write(self):
        writer = gw.MailboxWriter('unused', 0, '7036B510', app=APP, set_store=object())
        comm = mock.Mock()
        for state in (None, {'SchemaVersion': 2, 'LoginPrehashRounds': 256},
                      {'SchemaVersion': 3, 'LoginPrehashRounds': 16}):
            with mock.patch('fraktal_ab_press_execute.read_layout', return_value=state):
                with self.assertRaises(gw.WriteRefused):
                    writer._verify_login_profile(comm, self.writes())
            comm.Write.assert_not_called()
        with mock.patch('fraktal_ab_press_execute.read_layout', return_value={
                'SchemaVersion': 3, 'LoginPrehashRounds': 256}) as reader:
            writer._verify_login_profile(comm, self.writes())
            reader.assert_called_once_with(comm, access.tag(APP, 'State'), access.state_members(APP))


class SessionAuthority(unittest.TestCase):
    def test_defaults_match_tc3(self):
        c = controller()
        s = c.tags[access.tag(APP, 'State')]
        self.assertEqual((s['CurrentLevel'], s['UserLength'], s['SessionTimeout'], s['Required']), (0, 0, 0, [0] * 12))
        self.assertEqual(template.application().access_users, ())

    def test_secret_wiped_and_consumption_acked_before_authentication(self):
        c = controller()
        previous = c.calls['JSR']
        def verify_sample_wipe(plc, args):
            # Observe the boundary, before the first SHA block runs. A later
            # mailbox cleanup cannot conceal plaintext left after sampling.
            if (args[0][1][0][1] == access.tag(APP, 'Sha256')
                    and plc.tags[access.tag(APP, 'Work')]['HashPhase'] == 0):
                for tag in (mb.request_tag_name(APP), access.tag(APP, 'LoginRequest')):
                    self.assertEqual(plc.tags[tag]['Secret'], string('', 32))
            return previous(plc, args)
        c.calls['JSR'] = verify_sample_wipe
        response = request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        req = c.tags[mb.request_tag_name(APP)]
        s = c.tags[access.tag(APP, 'State')]
        self.assertEqual(req['Secret'], {'LEN': 0, 'DATA': [0] * 32})
        self.assertEqual((response['AckSequence'], response['Accepted'], s['CurrentLevel'], s['LoginBusy']), (1, 1, 0, 1))
        seq = req['Sequence']
        finish(c)
        self.assertEqual((response['AckSequence'], response['Accepted'], s['CurrentLevel']), (seq, 1, 4))
        self.assertEqual(c.tags[access.tag(APP, 'Work')]['Digest'], [0] * 32)

    def test_other_requests_run_during_hashing_without_changing_login_or_ack(self):
        c = controller()
        request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        self.assertEqual(request(c, mb.STOP)['AckSequence'], 2)
        request(c, mb.SET_ACCESS_LEVEL, IntValue=-1, TextValue='5')
        response = c.tags[mb.response_tag_name(APP)]
        self.assertEqual(response['Accepted'], 0)
        finish(c)
        self.assertEqual(c.tags[access.tag(APP, 'State')]['CurrentLevel'], 4)
        self.assertEqual((response['AckSequence'], response['Accepted']), (3, 0))

    def test_second_login_refused_and_wiped_without_replacing_pending_identity(self):
        c = controller()
        request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        response = request(c, mb.LOGIN, User='other', Secret='wrong')
        self.assertEqual((response['Accepted'], response['DiagnosticKey']), (0, mf.numeric_key(APP, access.BUSY)))
        self.assertEqual(c.tags[mb.request_tag_name(APP)]['Secret'], string('', 32))
        finish(c)
        s = c.tags[access.tag(APP, 'State')]
        self.assertEqual((s['CurrentLevel'], bytes(s['UserBytes'][:s['UserLength']])), (4, b'tester'))
        self.assertEqual(c.tags[access.tag(APP, 'Audit')]['Count'], 2)

    def test_logout_cancels_pending_login_and_clears_all_hash_work(self):
        c = controller()
        request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        request(c, mb.LOGOUT)
        finish(c)
        s, w = c.tags[access.tag(APP, 'State')], c.tags[access.tag(APP, 'Work')]
        self.assertEqual((s['CurrentLevel'], s['LoginBusy'], w['Remaining']), (0, 0, 0))
        for name in ('Buffer', 'Words', 'Digest', 'Salt', 'User', 'H', 'V', 'Temp'):
            self.assertFalse(any(w[name]), name)

    def test_success_with_one_scan_timeout_rearms_before_idle_clock(self):
        c = controller()
        c.tags[access.tag(APP, 'State')]['SessionTimeout'] = APP.task_period_ms
        self.assertEqual(login(c)['CurrentLevel'], 4)
        c.run('\n'.join(mb.handler_logic(APP)))
        self.assertEqual(c.tags[access.tag(APP, 'State')]['CurrentLevel'], 0)

    def test_startup_clears_volatile_session_and_preserves_policy_and_users(self):
        c = controller()
        login(c)
        request(c, mb.SET_ACCESS_LEVEL, IntValue=8, TextValue='4')
        request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        c.tags['S:FS'] = True
        before = copy.deepcopy(c.tags[access.tag(APP, 'Users')])
        c.run('\n'.join(access.startup(APP)))
        s = c.tags[access.tag(APP, 'State')]
        self.assertEqual((s['CurrentLevel'], s['LoginBusy'], s['Required'][8]), (0, 0, 4))
        self.assertEqual(c.tags[access.tag(APP, 'Users')], before)

    def test_unknown_wrong_and_malformed_login_all_ack_consumption_without_privilege(self):
        for user, pin in (('unknown', PIN.decode()), ('tester', 'wrong'), ('', ''), ('tester', '')):
            c = controller()
            s = login(c, user=user, pin=pin)
            self.assertEqual((s['CurrentLevel'], s['LoginFailed'], s['LoginBusy']), (0, 1, 0))
            self.assertEqual(c.tags[mb.response_tag_name(APP)]['Accepted'], 1)
            self.assertEqual(c.tags[access.tag(APP, 'Work')]['Remaining'], 0)

    def test_failed_login_preserves_previous_authenticated_session(self):
        c = controller()
        login(c)
        s = login(c, user='someone-else', pin='wrong')
        self.assertEqual((s['CurrentLevel'], bytes(s['UserBytes'][:s['UserLength']])), (4, b'tester'))
        self.assertEqual(s['LoginFailed'], 1)

    def test_payload_rewrite_after_sampling_does_not_change_authenticated_identity(self):
        c = controller()
        request(c, mb.LOGIN, User='tester', Secret=PIN.decode())
        c.tags[mb.request_tag_name(APP)]['User'] = string('someone-else', 32)
        c.tags[mb.request_tag_name(APP)]['Secret'] = string('wrong', 32)
        held = finish(c)
        self.assertEqual(bytes(held['UserBytes'][:held['UserLength']]), b'tester')
        # A replay is not a second login and cannot consume its new payload.
        self.assertEqual(c.tags[access.tag(APP, 'Audit')]['Count'], 1)

    def test_logout_clears_session_and_records_authenticated_actor(self):
        c = controller()
        login(c)
        request(c, mb.LOGOUT, User='spoofed')
        s, a = c.tags[access.tag(APP, 'State')], c.tags[access.tag(APP, 'Audit')]
        self.assertEqual((s['CurrentLevel'], s['UserLength'], s['UserBytes']), (0, 0, [0] * 32))
        values = access.audit_status(APP, mf.content(APP), a, c.tags[gen.alarm_ring_tag(APP)])
        self.assertIn('tester', values['AlarmLog/Ring[2]/Description'])
        self.assertEqual(a['Key'][1], mf.numeric_key(APP, 'std.audit.logout'))

    def test_idle_timeout_counts_accepted_authenticated_activity_only(self):
        c = controller()
        login(c)
        request(c, mb.SET_SESSION_TIMEOUT, DurationMs=100)
        w, s = c.tags[access.tag(APP, 'Work')], c.tags[access.tag(APP, 'State')]
        w['IdleMs'] = 50
        request(c, mb.SET_MODE, IntValue=0)
        self.assertEqual(w['IdleMs'], 0)
        w['IdleMs'] = 50
        request(c, mb.QUERY_CONFIG)
        self.assertEqual(w['IdleMs'], 60)
        request(c, mb.RELEASE_START)
        self.assertEqual(w['IdleMs'], 70)
        request(c, mb.SET_MODE, IntValue=-99)
        self.assertEqual(w['IdleMs'], 80)
        request(c, mb.SET_MODE, IntValue=-99)
        request(c, mb.RELEASE_START)
        self.assertEqual((s['CurrentLevel'], s['UserLength']), (0, 0))
        a = c.tags[access.tag(APP, 'Audit')]
        self.assertEqual(a['Key'][a['Head'] - 1], mf.numeric_key(APP, 'std.audit.autoLogout'))

    def test_every_gate_blocks_a_native_mailbox_before_dispatch(self):
        for kind, gate in access.GATES.items():
            if kind == mb.QUERY_CONFIG:
                continue  # metadata is ungated; each value is blanked by its level
            c = controller()
            held = c.tags[access.tag(APP, 'State')]
            held['Required'][gate] = 1
            before = copy.deepcopy({r.name: c.tags[r.name + 'Tag'] for r in APP.records})
            response = request(c, kind, BoolValue=1, User='admin', TextValue='4', IntValue=1)
            self.assertEqual((response['Accepted'], response['DiagnosticKey']), (0, mf.numeric_key(APP, access.DENIED)), kind)
            self.assertEqual({r.name: c.tags[r.name + 'Tag'] for r in APP.records}, before)
            audit = c.tags[access.tag(APP, 'Audit')]
            self.assertEqual((audit['Kind'][0], audit['Gate'][0], audit['UserLength'][0]), (kind, gate, 0))

    def test_corrupt_policy_or_session_fails_closed(self):
        for level, required in ((0, -1), (0, 5), (-1, 0), (5, 0)):
            c = controller()
            s = c.tags[access.tag(APP, 'State')]
            s['CurrentLevel'], s['Required'][4] = level, required
            self.assertEqual(request(c, mb.SET_MODE, IntValue=0)['Accepted'], 0)

    def test_policy_edits_validate_action_level_timeout_and_self_lockout(self):
        for gate, text in ((-1, '0'), (12, '0'), (0, '-1'), (0, '5'), (0, '00'), (0, ''), (8, '1')):
            c = controller()
            self.assertEqual(request(c, mb.SET_ACCESS_LEVEL, IntValue=gate, TextValue=text)['Accepted'], 0, (gate, text))
            self.assertEqual(c.tags[access.tag(APP, 'State')]['Required'], [0] * 12)
        c = controller()
        for duration in (-1, access.TIMEOUT_MAX + 1):
            self.assertEqual(request(c, mb.SET_SESSION_TIMEOUT, DurationMs=duration)['Accepted'], 0)
        for duration in (0, access.TIMEOUT_MAX):
            self.assertEqual(request(c, mb.SET_SESSION_TIMEOUT, DurationMs=duration)['Accepted'], 1)
        login(c)
        self.assertEqual(request(c, mb.SET_ACCESS_LEVEL, IntValue=8, TextValue='4')['Accepted'], 1)
        request(c, mb.LOGOUT)
        self.assertEqual(request(c, mb.SET_ACCESS_LEVEL, IntValue=8, TextValue='0')['Accepted'], 0)

    def test_restore_ack_requires_engineer_even_with_open_policy(self):
        for level, accepted in ((0, 0), (2, 0), (3, 1), (4, 1), (5, 0)):
            c = controller()
            c.tags[gen.config_persist_tag(APP)]['RestoreLost'] = 1
            s = c.tags[access.tag(APP, 'State')]
            s['CurrentLevel'] = level
            s['Required'][1] = s['Required'][11] = 4
            self.assertEqual(request(c, mb.ACK_CONFIG_RESTORE)['Accepted'], accepted)

    def test_corrupt_user_count_and_native_string_lengths_never_index_out_of_bounds(self):
        for count, user_length, pin_length in ((17, 6, 14), (2, 6, 14), (-1, 6, 14), (1, 33, 14), (1, -1, 14), (1, 6, 33), (1, 6, -1)):
            c = controller()
            c.tags[access.tag(APP, 'Users')]['Count'] = count
            req = c.tags[mb.request_tag_name(APP)]
            req.update(Kind=mb.LOGIN, Sequence=1, User=string('tester', 32), Secret=string(PIN.decode(), 32))
            req['User']['LEN'], req['Secret']['LEN'] = user_length, pin_length
            c.run('\n'.join(mb.handler_logic(APP)))
            s = finish(c)
            self.assertEqual((s['CurrentLevel'], s['LoginFailed'], s['LoginBusy']), (0, 1, 0))
            self.assertEqual(req['Secret'], string('', 32))

    def test_held_release_withdraws_without_level_but_does_not_rearm(self):
        c = controller()
        s = c.tags[access.tag(APP, 'State')]
        s['Required'][5] = 4
        unit = c.tags['FRK_Press_Unit']
        unit.update(HoldRun=1)
        self.assertEqual(request(c, mb.SET_HOLD_RUN, BoolValue=0)['Accepted'], 1)
        self.assertEqual(unit['HoldRun'], 0)

    def test_release_reports_use_policy_without_activity_or_denial_events(self):
        c = controller()
        s, a = c.tags[access.tag(APP, 'State')], c.tags[access.tag(APP, 'Audit')]
        s['Required'][5] = 1
        c.run('\n'.join(gen.start_release_logic(APP)))
        report = c.tags[gen.start_release_tag(APP)]
        self.assertEqual(report['Key'][0], mf.numeric_key(APP, access.DENIED))
        for gate in (-1, 12, 5):
            request(c, mb.RELEASE_ACTION, IntValue=gate)
        self.assertEqual(a['Count'], 0)


class PublishedContract(unittest.TestCase):
    def test_provider_budget_is_derived_versioned_read_only_and_discovered(self):
        self.assertEqual(access.login_timeout_ms(APP), 35700)
        for period in (1, 10, 20):
            app = dataclasses.replace(APP, task_period_ms=period)
            state = st.structure(access.state_members(app))
            self.assertEqual(state['SchemaVersion'], access.STATE_SCHEMA)
            self.assertEqual(state['LoginTimeoutMs'], 257 * access.HASH_BLOCK_SCANS * period + 10000)
            self.assertEqual(access.status(app, state)['Access/LoginTimeoutMs'], state['LoginTimeoutMs'])
            root = ET.fromstring(gen.controller_tags(app))
            node = root.find(f"Tag[@Name='{access.tag(app, 'State')}']")
            self.assertEqual(node.get('DataType'), 'FRK_T_AccessStateV3')
            self.assertEqual(node.get('ExternalAccess'), 'Read Only')
            data = mf.content(app)
            fields = {data['Localization'][row['PathKey'] - 1]['PortableKey']: row for row in data['Fields'] if row['ModuleId'] == 1}
            self.assertIn('AccessState.LoginTimeoutMs', fields)
            self.assertEqual(fields['AccessState.LoginTimeoutMs']['WriteCapabilityIndex'], 0)
        self.assertIn('access provider login budget exceeds the HMI ten-minute limit',
                      decl.validate(dataclasses.replace(APP, task_period_ms=3000)))

    def test_private_user_storage_follows_registration_count_through_the_ceiling(self):
        for count in (0, 1, 3, 4):
            users = tuple(dataclasses.replace(USER, name='user' + str(i),
                salt=i.to_bytes(16, 'little').hex(),
                pin_hash=access.pin_hash(i.to_bytes(16, 'little'), PIN).hex()) for i in range(count))
            app = dataclasses.replace(APP, access_users=users)
            self.assertFalse(access.validate_users(users))
            root = ET.fromstring(gen.controller_tags(app))
            node = root.find(f"Tag[@Name='{access.tag(app, 'Users')}']/Data/Structure")
            capacity = max(1, count)
            self.assertEqual(node.find("ArrayMember[@Name='Level']").get('Dimension'), str(capacity))
            self.assertEqual(len(access.user_data(users)['Salt']), capacity * 16)
            c = controller(app)
            if count:
                # Exercise the final allocated row, including all four users.
                held = login(c, app, user=users[-1].name)
                self.assertEqual((held['CurrentLevel'], held['LoginFailed']), (4, 0))
            else:
                held = login(c, app)
                self.assertEqual((held['CurrentLevel'], held['LoginFailed']), (0, 1))
        salt = count.to_bytes(16, 'little')
        fifth = dataclasses.replace(USER, name='too-many', salt=salt.hex(),
                                    pin_hash=access.pin_hash(salt, PIN).hex())
        self.assertEqual(access.validate_users(users + (fifth,)), ['access provider exceeds MAX_USERS'])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'rejected.L5X'
            with self.assertRaisesRegex(ValueError, 'access provider exceeds MAX_USERS'):
                gen.generate(dataclasses.replace(APP, access_users=users + (fifth,)),
                             Path(directory) / 'unused-seed.L5X', output)
            self.assertFalse(output.exists())

    def test_packed_audit_preserves_every_actor_byte_and_clears_shorter_overwrites(self):
        c = controller()
        req = c.tags[mb.request_tag_name(APP)]
        w = c.tags[access.tag(APP, 'Work')]
        a = c.tags[access.tag(APP, 'Audit')]
        self.assertEqual(a['SchemaVersion'], 3)
        self.assertEqual(len(a['UserWords']), 64 * 8)
        # Native STRING DATA is signed SINT; retain all eight bits without
        # signed overflow when the high byte sets a DINT's sign bit.
        for base in range(0, 256, 32):
            actor = bytes(range(base, base + 32))
            req['User'] = {'LEN': 32, 'DATA': [n if n < 128 else n - 256 for n in actor]}
            c.run('\n'.join(access._audit(APP, 'std.audit.loginFailed', '1', '123', '0', '32', mb.request_tag_name(APP) + '.User.DATA')))
            slot = a['Head'] - 1
            packed = b''.join((n & 0xffffffff).to_bytes(4, 'little') for n in a['UserWords'][slot * 8:(slot + 1) * 8])
            self.assertEqual(packed, actor)
        c.tags[gen.alarm_active_tag(APP)]['RingHead'] = 7
        req['User'] = string('x', 32)
        c.run('\n'.join(access._audit(APP, 'std.audit.loginFailed', '1', '124', '0', '1', mb.request_tag_name(APP) + '.User.DATA')))
        self.assertEqual(a['UserWords'][7 * 8:8 * 8], [120] + [0] * 7)
        self.assertEqual(w['ActorLength'], 0)  # Audit arguments never replace a pending login.

    def test_32_character_attempt_name_survives_gateway_audit_projection(self):
        c = controller()
        actor = 'unknown-user-0123456789012345678'
        self.assertEqual(len(actor), 32)
        login(c, user=actor, pin='wrong')
        a = c.tags[access.tag(APP, 'Audit')]
        values = access.audit_status(APP, mf.content(APP), a, c.tags[gen.alarm_ring_tag(APP)])
        self.assertIn(actor, values['AlarmLog/Ring[1]/Description'])
        a['SchemaVersion'] = 1
        self.assertEqual(access.audit_status(APP, mf.content(APP), a, c.tags[gen.alarm_ring_tag(APP)]), {})

    def test_private_records_excluded_and_native_bit_scratch_removed(self):
        root = ET.fromstring(gen.controller_tags(APP))
        tags = {n.get('Name'): n for n in root}
        for name in ('Users', 'Work', 'LoginRequest', 'RoundConstants'):
            key = access.tag(APP, name)
            self.assertEqual(tags[key].get('ExternalAccess'), 'None')
            self.assertNotIn(key, gen.publishable_tags(APP))
        self.assertNotIn(access.tag(APP, 'Bits'), tags)
        self.assertEqual(tags[access.tag(APP, 'Work')].get('DataType'), 'FRK_T_AccessWorkV6')
        constants = tags[access.tag(APP, 'RoundConstants')]
        self.assertEqual(constants.get('Constant'), 'true')
        self.assertEqual([int(n.get('Value')) for n in constants.find('Data/Array')], [access._signed(n) for n in access.K])
        data = mf.content(APP)
        fields = {data['Localization'][r['PathKey'] - 1]['PortableKey'] for r in data['Fields'] if r['ModuleId'] == 0}
        self.assertFalse(any('AccessUsers' in p or 'AccessWork' in p for p in fields))
        self.assertIn(access.tag(APP, 'State'), gen.publishable_tags(APP))

    def test_projection_uses_plc_session_and_fails_closed_if_missing(self):
        s = st.structure(access.state_members(APP))
        self.assertEqual(projection.access_status(APP, 4, s)['Access/CurrentLevel'], 0)
        self.assertEqual(projection.access_status(APP, 4), {})
        s.update(CurrentLevel=2, UserLength=6, UserBytes=list(b'tester') + [0] * 26)
        s['Required'][4] = 3
        held = projection.access_status(APP, 0, s)
        self.assertEqual((held['Access/CurrentLevel'], held['Access/CurrentUser'], held['Access/Policy/Required[5]']), (2, 'tester', 3))

    def test_access_audit_is_generic_message_history_and_never_carries_secret(self):
        c = controller()
        login(c)
        request(c, mb.SET_MODE, IntValue=0, User='spoofed')
        a = c.tags[access.tag(APP, 'Audit')]
        values = access.audit_status(APP, mf.content(APP), a, c.tags[gen.alarm_ring_tag(APP)])
        description = [v for k, v in values.items() if k.endswith('/Description') and v]
        self.assertTrue(any('tester' in d and 'kind=3' in d for d in description))
        self.assertNotIn(PIN.decode(), json.dumps(values))
        self.assertNotIn('spoofed', json.dumps(values))
        ring = c.tags[gen.alarm_ring_tag(APP)]
        self.assertEqual((ring['RingState'][0], ring['RingSeverity'][0]), (0, 0))
        ring['RingState'][0] = 2
        values = access.audit_status(APP, mf.content(APP), a, ring)
        self.assertNotIn('AlarmLog/Ring[1]/Description', values)

    def test_audits_use_the_existing_64_slot_ring_and_wrap_without_expanding_it(self):
        c = controller()
        login(c)
        for _ in range(70):
            request(c, mb.SET_MODE, IntValue=0)
        a = c.tags[access.tag(APP, 'Audit')]
        active = c.tags[gen.alarm_active_tag(APP)]
        self.assertEqual((a['Count'], a['Head']), (64, active['RingHead']))
        values = access.audit_status(APP, mf.content(APP), a, c.tags[gen.alarm_ring_tag(APP)])
        self.assertEqual(sum(k.endswith('/Description') for k in values), 64)
        self.assertFalse(any('Ring[65]' in k for k in values))

    def test_declaration_refuses_bad_registrations(self):
        for user in (dataclasses.replace(USER, level=0), dataclasses.replace(USER, salt='00'),
                     dataclasses.replace(USER, pin_hash='00'), dataclasses.replace(USER, name='')):
            self.assertTrue(access.validate_users((user,)))
        self.assertTrue(access.validate_users((USER, USER)))
        self.assertFalse(access.validate_users((USER,)))


if __name__ == '__main__':
    unittest.main()
