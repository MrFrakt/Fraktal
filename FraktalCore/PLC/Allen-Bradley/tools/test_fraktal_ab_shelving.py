"""Execute generated shelving ST: identities, authority, expiry and control."""
import dataclasses
import re
import unittest
from pathlib import Path
from unittest import mock

import fraktal_ab_access as access
import fraktal_ab_generate as gen
import fraktal_ab_generated_size as size
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_projection as projection
import fraktal_ab_reasons as reasons
import fraktal_ab_shelving as shelf
import fraktal_ab_st_model as st
import fraktal_ab_station_template as template
import test_fraktal_ab_access as users

APP = users.APP
SHELVABLE = APP.reasons['STEP_STALLED']
SOURCE = APP.name + '.' + APP.modules[0].name


class Bench:
    def __init__(self, app=APP):
        self.app = app
        self.c = users.controller(app)
        self.active = self.c.tags[gen.alarm_active_tag(app)]
        self.ring = self.c.tags[gen.alarm_ring_tag(app)]
        self.work = self.c.tags[shelf.tag(app)]
        self.session = self.c.tags[access.tag(app, 'State')]

    def open(self, slot=0, reason=SHELVABLE, module=2, state=gen.ALARM_OPEN):
        for key, value in dict(State=state, ReasonCode=reason, SourceModuleId=module,
                               ResetClass=gen.RESET_MANUAL, ComeDate=20261003,
                               ComeTime=120000000).items():
            self.active['Act' + key][slot] = value
        self.active['Blocking'] = 1
        self.active['NActive'] += 1

    def request(self, kind=mb.SHELVE_ALARM, **args):
        supplied = dict(TargetPath=SOURCE, TextValue=projection.reason_description(self.app, SHELVABLE), DurationMs=10000)
        supplied.update(args)
        return dict(users.request(self.c, kind, self.app, **supplied))

    def tick(self, n=1):
        code = st.parse('\n'.join(shelf.cyclic(self.app)))
        for _ in range(n):
            self.c.run(code)

    def events(self, key):
        audit = self.c.tags[access.tag(self.app, 'Audit')]
        return [i for i, k in enumerate(audit['Key']) if k == mf.numeric_key(self.app, key)]


class Shelving(unittest.TestCase):
    def test_valid_shelf_changes_annunciation_and_keeps_blocking(self):
        b = Bench(); b.open()
        b.session.update(CurrentLevel=4, UserLength=6, UserBytes=list(b'actual') + [0] * 26)
        answer = b.request(User='forged')
        self.assertEqual(answer['Accepted'], 1)
        self.assertEqual((b.active['ActShelved'][0], b.active['Blocking']), (1, 1))
        self.assertEqual(b.active['ActState'][0], gen.ALARM_OPEN)
        out = projection.alarm_log_status(APP, b.active, b.ring)
        self.assertTrue(out['AlarmLog/Active[1]/Shelved'])
        audit = access.audit_status(APP, mf.content(APP), b.c.tags[access.tag(APP, 'Audit')], b.ring)
        slot = b.events(shelf.SHELVED)[0]
        self.assertEqual(audit[f'AlarmLog/Ring[{slot + 1}]/SourcePath'], SOURCE)
        self.assertIn('actual', audit[f'AlarmLog/Ring[{slot + 1}]/Description'])
        self.assertNotIn('forged', audit[f'AlarmLog/Ring[{slot + 1}]/Description'])
        self.assertEqual(b.ring['RingResetClass'][slot], gen.RESET_AUTO)

    def test_wait_reset_is_shelvable_and_still_refuses_start_with_report(self):
        b = Bench(); b.open(state=gen.ALARM_WAIT_RESET)
        self.assertEqual(b.request()['Accepted'], 1)
        answer = b.request(mb.START)
        self.assertEqual(answer['Accepted'], 0)
        report = b.c.tags[gen.release_report_tag(APP)]
        self.assertIn(mf.numeric_key(APP, gen.MANUAL_RESET_KEY), report['Key'][:report['Count']])
        self.assertEqual(b.active['ActState'][0], gen.ALARM_WAIT_RESET)

    def test_native_claimed_admin_cannot_bypass_shelve_or_unshelve_gate(self):
        for kind in (mb.SHELVE_ALARM, mb.UNSHELVE_ALARM):
            b = Bench(); b.open(); b.active['ActShelved'][0] = 1
            b.work['RemainingMs'][0] = 10000
            b.session['Required'][9] = 4
            for level in (0, 1, 2, 3):
                b.session['CurrentLevel'] = level
                answer = b.request(kind, User='tester')
                self.assertEqual(answer['Accepted'], 0)
                self.assertEqual(answer['DiagnosticKey'], mf.numeric_key(APP, access.DENIED))
                self.assertEqual((b.active['ActShelved'][0], b.work['RemainingMs'][0]), (1, 10000))

    def test_missing_foreign_and_ambiguous_identities_refuse(self):
        for args in (dict(TargetPath='Other'), dict(TargetPath=''), dict(TextValue=''),
                     dict(TextValue='std.reason.9999'), dict(TargetPath=SOURCE + 'X')):
            b = Bench(); b.open()
            answer = b.request(**args)
            self.assertEqual(answer['DiagnosticKey'], mf.numeric_key(APP, shelf.IDENTITY))
            self.assertEqual(b.active['ActShelved'][0], 0)
        b = Bench(); b.open(0); b.open(1)
        self.assertEqual(b.request()['DiagnosticKey'], mf.numeric_key(APP, shelf.IDENTITY))
        self.assertEqual(sum(b.active['ActShelved']), 0)

    def test_closed_identity_is_never_addressable(self):
        b = Bench(); b.open(state=gen.ALARM_CLOSED)
        self.assertEqual(b.request()['DiagnosticKey'], mf.numeric_key(APP, shelf.IDENTITY))

    def test_registry_flag_and_safety_category_both_refuse(self):
        for name, code in APP.reasons.items():
            rationale = reasons.of(APP, name)
            if rationale.shelvable and rationale.category != reasons.CATEGORY['SAFETY']:
                continue
            b = Bench(); b.open(reason=code)
            answer = b.request(TextValue=mf.reason_key(APP, name))
            self.assertEqual(answer['Accepted'], 0, name)
            self.assertEqual(b.active['ActShelved'][0], 0)
        # SAFETY wins even if a registry flag were erroneously True.
        original = reasons.of
        def safety(app, name):
            rationale = original(app, name)
            return dataclasses.replace(rationale, category=1, shelvable=True) if app.reasons[name] == SHELVABLE else rationale
        with mock.patch.object(reasons, 'of', side_effect=safety):
            b = Bench(); b.open()
            answer = b.request()
            self.assertEqual(answer['Accepted'], 0)
            self.assertEqual(answer['DiagnosticKey'], mf.numeric_key(APP, shelf.REJECTED))

    def test_unknown_reason_with_no_rationalization_refuses(self):
        b = Bench(); b.open(reason=4242)
        self.assertEqual(b.request()['Accepted'], 0)
        self.assertEqual(b.active['ActShelved'][0], 0)

    def test_zero_negative_and_subsecond_duration_refuse(self):
        for ms in (-2147483648, -1, 0, 1, 999):
            b = Bench(); b.open()
            self.assertEqual(b.request(DurationMs=ms)['Accepted'], 0, ms)
            self.assertFalse(b.events(shelf.SHELVED))

    def test_duration_is_whole_seconds_and_capped_at_eight_hours(self):
        for ms, expected in ((1499, 1000), (1999, 1000), (2000, 2000), (2147483647, 28800000)):
            b = Bench(); b.open()
            self.assertEqual(b.request(DurationMs=ms)['Accepted'], 1)
            self.assertEqual(b.work['RemainingMs'][0], expected)

    def test_expiry_logs_once_without_session_or_wall_clock_dependency(self):
        b = Bench(); b.open(); b.request(DurationMs=1000)
        b.c.tags['FRK_Press_NowDate'] = 19991231
        b.c.tags['FRK_Press_NowTime'] = 230000000
        b.session['Required'][9] = 4  # expiration is not an operator request
        b.tick(99)
        self.assertEqual(b.active['ActShelved'][0], 1)
        b.tick()
        self.assertEqual((b.active['ActShelved'][0], b.work['RemainingMs'][0]), (0, 0))
        slots = b.events(shelf.UNSHELVED)
        self.assertEqual(len(slots), 1)
        audit = b.c.tags[access.tag(APP, 'Audit')]
        self.assertEqual((audit['Sequence'][slots[0]], audit['UserLength'][slots[0]], audit['Gate'][slots[0]]), (0, 0, 9))
        b.tick(200)
        self.assertEqual(b.events(shelf.UNSHELVED), slots)
        self.assertEqual(b.active['Blocking'], 1)

    def test_manual_unshelve_logs_and_repeat_refuses(self):
        b = Bench(); b.open(); b.request()
        self.assertEqual(b.request(mb.UNSHELVE_ALARM)['Accepted'], 1)
        self.assertEqual(b.active['ActShelved'][0], 0)
        self.assertEqual(len(b.events(shelf.UNSHELVED)), 1)
        self.assertEqual(b.request(mb.UNSHELVE_ALARM)['Accepted'], 0)
        b.tick(1001)
        self.assertEqual(len(b.events(shelf.UNSHELVED)), 1)

    def test_closed_slot_countdown_expires_until_reuse_like_tc3(self):
        b = Bench(); b.open(); b.request(DurationMs=1000)
        b.active['ActState'][0] = gen.ALARM_CLOSED
        b.tick(100)
        self.assertEqual(b.active['ActShelved'][0], 0)
        self.assertEqual(len(b.events(shelf.UNSHELVED)), 1)

    def test_reshelve_restarts_countdown(self):
        b = Bench(); b.open(); b.request(DurationMs=1000); b.tick(80)
        b.request(DurationMs=2000); b.tick(120)
        self.assertEqual(b.active['ActShelved'][0], 1)
        b.tick(80)
        self.assertEqual(b.active['ActShelved'][0], 0)

    def test_consumed_sequence_cannot_reshelve(self):
        b = Bench(); b.open(); b.request(DurationMs=1000); b.tick(50)
        b.c.run(st.parse('\n'.join(mb.handler_logic(APP))))
        self.assertEqual(b.work['RemainingMs'][0], 500)
        self.assertEqual(len(b.events(shelf.SHELVED)), 1)

    def test_reset_closes_shelved_event_and_reused_slot_has_no_shelf(self):
        b = Bench(); b.open(); b.request()
        for name, dimension in gen.alarm_scratch_tags(APP).items():
            b.c.tags[name] = [0] * dimension if dimension else 0
        b.c.tags[gen.system_health_tag(APP)] = st.structure(gen.system_health_members())
        b.c.tags['FRK_Press_ResetRequest'] = 1
        log = st.parse('\n'.join(gen.alarm_log_logic(APP)))
        b.c.routines.update({name: st.parse('\n'.join(body))
                             for name, body in gen.alarm_service_routines(APP)})
        b.c.run(log)
        closed = b.active['RingHead'] - 1
        self.assertEqual(b.ring['RingShelved'][closed], 1)
        self.assertEqual(b.active['Blocking'], 0)
        b.c.tags['FRK_Press_ResetRequest'] = 0
        b.c.tags['FRK_Press_Unit'].update(Error=1, ErrorID=SHELVABLE, ErrorSource=1)
        b.c.run(log)
        self.assertEqual(b.active['ActShelved'][0], 0)
        self.assertEqual(b.work['RemainingMs'][0], 0)

    def test_ring_reuse_clears_old_shelf_columns(self):
        b = Bench(); b.open(); b.ring['RingShelved'][0] = 1
        b.request()
        self.assertEqual(b.ring['RingShelved'][0], 0)

    def test_new_schema_keeps_v1_prefix_and_private_countdown(self):
        for members in (gen.alarm_active_members(), gen.alarm_ring_members()):
            self.assertEqual(members[0].initial, 2)
            self.assertTrue(members[-2].name.endswith('IoRoles'))
        self.assertNotIn(shelf.tag(APP), '\n'.join(str(r) for r in gen.root_field_records(APP)))

    def test_template_inherits_routes_and_native_identity(self):
        app = template.application()
        self.assertNotIn(mb.SHELVE_ALARM, mb.refused_for(app))
        self.assertNotIn(mb.UNSHELVE_ALARM, mb.refused_for(app))
        st.parse('\n'.join(mb.handler_logic(app)))
        st.parse('\n'.join(gen.alarm_log_logic(app)))

    def test_cap_is_pinned_to_tc3_oracle(self):
        core = Path(__file__).resolve().parents[2] / 'TwinCAT/Framework/Fraktal_Core/Params/PL_Fraktal.TcGVL'
        match = re.search(r'MAX_SHELF_S\s*:\s*UDINT\s*:=\s*(\d+)', core.read_text(encoding='utf-8'))
        self.assertEqual(int(match[1]), shelf.MAX_SHELF_S)

    def test_lookup_resolves_every_declared_source_and_reason_from_manifest(self):
        b = Bench(); b.open()
        q = b.c.tags[mb.request_tag_name(APP)]
        lookup = st.parse('\n'.join(shelf._identity(APP)))
        for module, path in enumerate((APP.name, *(APP.name + '.' + m.name for m in APP.modules)), 1):
            for name, code in APP.reasons.items():
                b.active['ActSourceModuleId'][0] = module
                b.active['ActReasonCode'][0] = code
                q.update(TargetPath=users.string(path, mb.TARGET_PATH_LENGTH),
                         TextValue=users.string(mf.reason_key(APP, name), mb.TEXT_VALUE_LENGTH))
                b.c.run(lookup)
                self.assertEqual((b.work['ModuleId'], b.work['Reason'], b.work['Slot'], b.work['Matches']),
                                 (module, code, 0, 1), (path, name))

    def test_lookup_bounds_native_lengths_keys_and_manifest_counts(self):
        b = Bench(); b.open()
        b.request()  # populate a valid native request, then exercise corrupt input
        q = b.c.tags[mb.request_tag_name(APP)]
        body = st.parse('\n'.join(shelf.handler(APP)))
        def refused():
            response = b.c.tags[mb.response_tag_name(APP)]
            response.update(Accepted=0, DiagnosticKey=0)  # mailbox owns response initialization
            b.c.run(body)
            self.assertEqual(response['DiagnosticKey'], mf.numeric_key(APP, shelf.IDENTITY))
            self.assertEqual(response['Accepted'], 0)
        for member in ('TargetPath', 'TextValue'):
            original = q[member]['LEN']
            for length in (-2147483648, -1, 0, 256, 2147483647):
                q[member]['LEN'] = length
                refused()
            q[member]['LEN'] = original
        header = b.c.tags[mf.header_tag(APP)]
        for member, bad in (('Valid', 0), ('Truncated', 1), ('ModulesCount', 999),
                            ('RationalizationCount', -1), ('LocalizationCount', 2147483647)):
            original = header[member]; header[member] = bad
            refused()
            header[member] = original
        source = b.c.tags[f'FRK_{APP.name}_MfModules'][1]
        reason = next(r for r in b.c.tags[f'FRK_{APP.name}_MfRationalization'] if r['ReasonCode'] == SHELVABLE)
        for row, member in ((source, 'CanonicalPathKey'), (reason, 'ActionKey')):
            original = row[member]
            for bad in (-2147483648, -1, 0, header['LocalizationCount'] + 1, 2147483647):
                row[member] = bad
                refused()
            row[member] = original
        for key in (source['CanonicalPathKey'], reason['ActionKey']):
            locale = b.c.tags[f'FRK_{APP.name}_MfLocalization'][key - 1]['PortableKey']
            original = locale['LEN']
            for bad in (-1, 0, mf.key_string_length(APP) + 1, 2147483647):
                locale['LEN'] = bad
                refused()
            locale['LEN'] = original

    def test_permission_is_read_from_controller_rationalization_and_unknown_fails_closed(self):
        b = Bench(); b.open()
        row = next(r for r in b.c.tags[f'FRK_{APP.name}_MfRationalization'] if r['ReasonCode'] == SHELVABLE)
        for flag, category in ((0, 0), (1, 1), (1, 99), (2, 0), (-1, 0)):
            row.update(Shelvable=flag, Category=category)
            self.assertEqual(b.request()['Accepted'], 0)
        row.update(Shelvable=1, Category=0)
        self.assertEqual(b.request()['Accepted'], 1)

    def test_shelving_code_size_is_constant_as_declaration_grows(self):
        bigger = dataclasses.replace(APP, modules=APP.modules + tuple(
            dataclasses.replace(APP.modules[0], name=f'Extra{i}') for i in range(12)),
            reasons={**APP.reasons, **{f'EXTRA_{i}': 16000 + i for i in range(9)}})
        small, large = (size.st_size('\n'.join(shelf.handler(app))) for app in (APP, bigger))
        self.assertEqual(small['StStatementTerminators'], large['StStatementTerminators'])
        self.assertLess(small['StStatementTerminators'], 150)
        self.assertEqual(size.st_size('\n'.join(shelf.dispatch(bigger)))['StStatementTerminators'], 1)
        # The old expansion needed over 1,200 mailbox terminators for this feature.
        self.assertNotIn('TargetPath.DATA[0]', '\n'.join(shelf.handler(APP)))


if __name__ == '__main__':
    unittest.main()
