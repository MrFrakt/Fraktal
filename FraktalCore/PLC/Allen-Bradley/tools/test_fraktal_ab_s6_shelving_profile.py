"""Exercise the real health/alarm/shelving owners for the S6-Q test profile.

These execute generated service ST before the collapse storage-name lowering;
the whole-image schema/token and compiler gates check the emitted image.
Nothing injects an alarm slot or relaxes the existing fixture preflight.
"""
from dataclasses import replace
import unittest
from unittest.mock import patch

import fraktal_ab_access as access
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_phase6_shelving_execute as fixture
import fraktal_ab_press_s6_collapse_echo38 as base
import fraktal_ab_press_s6_shelving_echo38 as profile
import fraktal_ab_reasons as reasons
import fraktal_ab_shelving as shelf
import fraktal_ab_st_model as st
from test_fraktal_ab_access import add_access, string


class Bench:
    def __init__(self, app=None):
        self.app = app or profile.application()
        app = self.app
        tags = {
            f'FRK_{app.name}_Unit': st.structure(gen.unit_context_members(app)),
            gen.alarm_active_tag(app): st.structure(gen.alarm_active_members()),
            gen.alarm_ring_tag(app): st.structure(gen.alarm_ring_members()),
            gen.profiler_tag(app): st.structure(gen.profiler_members(app)),
            **{gen.ctx_tag_for(app, m.name): st.structure(gen.module_members(m)) for m in app.modules},
            **{name: [0] * n if n else 0 for name, n in gen.alarm_scratch_tags(app).items()},
            f'FRK_{app.name}_NowDate': 20261106, f'FRK_{app.name}_NowTime': 120000000,
            f'FRK_{app.name}_ScanCount': 0, f'FRK_{app.name}_ResetRequest': 0,
            f'FRK_{app.name}_HmiLastSequence': 1,
            mb.request_tag_name(app): {name: string('', width) if kind == mb.STRING_MEMBER else 0
                                       for name, kind, width, _ in mb.REQUEST_MEMBERS},
            mb.response_tag_name(app): {name: 0 for name, *_ in mb.RESPONSE_MEMBERS},
        }
        self.c = st.Controller(tags, routines=dict(gen.alarm_service_routines(app)))
        # add_access installs its audit helper; preserve the alarm JSRs too.
        self.c.calls['JSR'] = lambda plc, args: plc.run(plc.routines[args[0][1][0][1]])
        add_access(self.c, app)
        self.active = self.c.tags[gen.alarm_active_tag(app)]
        self.ring = self.c.tags[gen.alarm_ring_tag(app)]
        self.session = self.c.tags[access.tag(app, 'State')]
        self.health = st.structure(gen.system_health_members())
        self.probe = st.structure(gen.health_probe_members())
        self.c.tags.update({gen.system_health_tag(app): self.health,
                            gen.health_probe_tag(app): self.probe,
                            gen.health_cfg_tag(app): st.structure(gen.health_cfg_members(app))})
        self.health_logic = st.parse('\n'.join(gen.system_health_logic(app)))
        self.alarm_logic = st.parse('\n'.join(gen.alarm_log_logic(app)))

    def scan(self):
        self.c.tags[f'FRK_{self.app.name}_ScanCount'] += 1
        self.probe.update(Samples=self.probe['Samples'] + 1,
                          IntervalUs=self.app.task_period_ms * 1000, JitterUs=0)
        self.c.run(self.health_logic)
        self.c.run(self.alarm_logic)

    def preflight(self):
        with patch.object(fixture, 'APP', self.app), \
             patch.object(fixture, 'read_alarm_log', return_value=(self.active, self.ring)), \
             patch.object(fixture.users, 'read_access', return_value=self.session):
            return fixture.read_rows(self.c)

    def command(self, kind, **args):
        # Invoke the generated service, not a model of the typed wire ingress.
        supplied = dict(Kind=kind, TargetPath=self.app.name,
                        TextValue=mf.reason_key(self.app, 'CONTROLLER_METRICS_UNAVAILABLE'), **args)
        q = self.c.tags[mb.request_tag_name(self.app)]
        for name, member_kind, width, _ in mb.REQUEST_MEMBERS:
            q[name] = string(supplied.get(name, ''), width) if member_kind == mb.STRING_MEMBER else supplied.get(name, 0)
        response = self.c.tags[mb.response_tag_name(self.app)]
        response.update(Accepted=0, DiagnosticKey=0)
        self.c.run('\n'.join(shelf.handler(self.app)))
        return dict(response)

    def slot(self):
        return next(i for i, code in enumerate(self.active['ActReasonCode'])
                    if code == self.app.reasons['CONTROLLER_METRICS_UNAVAILABLE']
                    and self.active['ActState'][i] != gen.ALARM_CLOSED)


class AcceptanceProfile(unittest.TestCase):
    def test_only_the_explicit_health_requirement_changes(self):
        app, parent = profile.application(), base.application()
        self.assertEqual(replace(app, system_health=parent.system_health), parent)
        self.assertEqual(app.system_health, replace(parent.system_health, require_controller_metrics=True))
        self.assertFalse(base.application().system_health.require_controller_metrics)
        self.assertEqual(decl.validate(app), [])

    def test_event_is_the_existing_nonblocking_registry_warning(self):
        app = profile.application()
        self.assertEqual(app.reasons['CONTROLLER_METRICS_UNAVAILABLE'], fixture.STANDING)
        rationale = reasons.of(app, 'CONTROLLER_METRICS_UNAVAILABLE')
        self.assertTrue(rationale.shelvable)
        self.assertEqual(rationale.priority, 0)
        self.assertNotEqual(rationale.category, reasons.CATEGORY['SAFETY'])

    def test_first_sample_is_not_eligible_then_the_health_owner_opens_one_event(self):
        b = Bench()
        b.scan()
        self.assertFalse(b.preflight()[0]['passed'])
        b.scan()
        self.assertTrue(all(row['passed'] for row in b.preflight()))
        for _ in range(4):
            b.scan()
        slot = b.slot()
        self.assertEqual((b.active['NActive'], b.active['ActResetClass'][slot],
                          b.active['ActSourceModuleId'][slot], b.active['Blocking']),
                         (1, gen.RESET_AUTO, 1, 0))
        self.assertEqual(b.health['Healthy'], 0)

    def test_base_press_keeps_its_exclusion_and_preflight_refusal(self):
        b = Bench(base.application())
        b.scan()
        b.scan()
        self.assertEqual([row['passed'] for row in b.preflight()], [False, True])
        self.assertEqual((b.health['Healthy'], b.active['NActive']), (1, 0))

    def test_active_shelf_still_refuses_preflight(self):
        b = Bench()
        b.scan()
        b.scan()
        self.assertEqual(b.command(mb.SHELVE_ALARM, DurationMs=3000)['Accepted'], 1)
        self.assertFalse(b.preflight()[0]['passed'])

    def test_unknown_session_still_refuses_preflight(self):
        b = Bench()
        b.scan()
        b.scan()
        b.session.update(CurrentLevel=4, UserLength=7, UserBytes=list(b'unknown') + [0] * 25)
        self.assertEqual([row['passed'] for row in b.preflight()], [True, False])

    def test_shelf_unshelf_and_logged_out_expiry_leave_the_condition_open(self):
        b = Bench()
        b.scan()
        b.scan()
        slot = b.slot()
        self.assertEqual(b.command(mb.SHELVE_ALARM, DurationMs=3000)['Accepted'], 1)
        b.scan()
        self.assertEqual((b.active['ActShelved'][slot], b.active['Blocking']), (1, 0))
        self.assertEqual(b.command(mb.UNSHELVE_ALARM)['Accepted'], 1)
        self.assertEqual(b.active['ActShelved'][slot], 0)
        self.assertEqual(b.command(mb.SHELVE_ALARM, DurationMs=1000)['Accepted'], 1)
        self.assertEqual(b.session['CurrentLevel'], 0)
        for _ in range(1000 // b.app.task_period_ms):
            b.scan()
        self.assertEqual((b.active['ActShelved'][slot], b.active['ActState'][slot],
                          b.active['NActive'], b.active['Blocking']), (0, gen.ALARM_OPEN, 1, 0))
        audit = b.c.tags[access.tag(b.app, 'Audit')]
        expired = [i for i, key in enumerate(audit['Key'])
                   if key == mf.numeric_key(b.app, shelf.UNSHELVED)
                   and audit['Sequence'][i] == 0 and audit['UserLength'][i] == 0]
        self.assertEqual(len(expired), 1)
        self.assertTrue(all(row['passed'] for row in b.preflight()))

    def test_access_owner_refuses_claimed_admin_without_an_authenticated_session(self):
        b = Bench()
        b.scan()
        b.scan()
        b.session['Required'][9] = 4
        q = b.c.tags[mb.request_tag_name(b.app)]
        q.update(Kind=mb.SHELVE_ALARM, User=string('echo_admin', access.WIDTH))
        b.c.run('\n'.join(access.check(b.app)))
        self.assertEqual(b.c.tags[access.tag(b.app, 'Work')]['Permitted'], 0)
        self.assertEqual(b.active['ActShelved'][b.slot()], 0)


if __name__ == '__main__':
    unittest.main()
