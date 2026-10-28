"""Execute weekly scheduling, atomic writes/sets and closure on generated ST."""
import copy
import dataclasses
from datetime import datetime, timezone
import itertools
import random
import unittest

import fraktal_ab_line as line
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_press_demo as press
import fraktal_ab_station_template as template
import fraktal_ab_st_model as st
from test_fraktal_ab_capture import controller, execute, initial
from test_fraktal_ab_sets import controller as set_controller, document, run as run_set, configurations

APP = press.application()
W, S, STATE = (line.tag(APP, n) for n in ('Work', 'Shift', 'State'))
CFG = line.cfg(APP).name + 'Tag'
UNIT, OEE = f'FRK_{APP.name}_Unit', gen.oee_tag(APP)
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def minute(value):
    return int((value - EPOCH).total_seconds() // 60)


def scheduled(rows, offset=0):
    declaration = line.Line('PRESS-LINE-1', 'Press', offset, rows)
    return dataclasses.replace(APP, line=declaration,
        records=tuple(line.record(declaration) if r.line_cfg else r for r in APP.records))


class Calendar(unittest.TestCase):
    def test_weekend_only_and_adjacent_wrap_are_valid_but_overlap_is_not(self):
        inactive = (-1, 480, 0)
        line.validate_calendar(-300, ((480, 720, 96), inactive, inactive, inactive, inactive))
        line.validate_calendar(0, ((1200, 720, 64), (480, 720, 1), inactive, inactive, inactive))
        for rows in (((1200, 720, 64), (479, 720, 1), inactive, inactive, inactive),
                     ((480, 720, 96), (1199, 60, 32), inactive, inactive, inactive)):
            with self.assertRaisesRegex(ValueError, 'overlap'):
                line.validate_calendar(0, rows)

    def test_daily_migration_preserves_next_start_durations_and_unused_rows(self):
        self.assertEqual(line.migrate_daily(-300, (480, 960, 0, -1)),
            ((480, 480, 127), (960, 480, 127), (0, 480, 127), (-1, 480, 0), (-1, 480, 0)))
        self.assertEqual(line.migrate_daily(0, (120, -1, -1, -1))[0], (120, 1440, 127))
        self.assertEqual(line.migrate_daily(0, (-1,) * 4), ((-1, 480, 0),) * line.MAX_SHIFTS)
        for starts in ((0, 0, -1, -1), (-2, -1, -1, -1), (1440, -1, -1, -1)):
            with self.assertRaises(ValueError):
                line.migrate_daily(0, starts)

    def test_bad_ranges_types_and_partial_profiles_refuse(self):
        for row in ((480, 0, 96), (1440, 720, 96), (480, 720, 128), (480, True, 96)):
            with self.assertRaises(ValueError):
                line.validate_calendar(0, (row,) + ((-1, 480, 0),) * (line.MAX_SHIFTS - 1))
        self.assertTrue(decl.validate(dataclasses.replace(APP, line=None)))
        self.assertTrue(decl.validate(dataclasses.replace(APP, access_users=None)))
        self.assertFalse(decl.validate(template.application(line=line.Line('LINE', 'Cell'))))

    def test_line_never_becomes_a_module_or_an_external_write_surface(self):
        rows = mf.content(APP)
        self.assertEqual(len(rows['Modules']), 1 + len(APP.modules))
        self.assertNotIn(W, gen.publishable_tags(APP))
        self.assertIn('ExternalAccess="None"', line.tags(APP)[2])
        self.assertTrue(all(row['ConfigKind'] == 2 for row in rows['WriteCapabilities'][9:]))

    def test_expanded_derived_arrays_use_new_types_and_refuse_old_level_images(self):
        import fraktal_ab_data_access as data
        import fraktal_ab_sets as sets
        prior = dataclasses.replace(APP,line=None,records=tuple(r for r in APP.records if not r.line_cfg))
        self.assertEqual(data.record_name(prior,'Levels'),'FRK_T_DataLevelsV1')
        self.assertEqual(data.record_name(APP,'Levels'),'FRK_T_DataLevelsV3')
        self.assertEqual(sets.state_name(prior),'FRK_T_ConfigSetStateV1')
        self.assertEqual(sets.state_name(APP),'FRK_T_ConfigSetStateV3')
        self.assertEqual(data.entry_levels({'SchemaVersion':1,'Count':22,
            'ReadLevel':[0]*22,'WriteLevel':[0]*22,'Readable':[1]*22},1,app=APP),(4,4,False))

    def test_native_validation_matches_weekly_intervals_including_sunday_wrap(self):
        c = controller()
        cases = [((480, 720, 96), (-1, 480, 0), (-1, 480, 0), (-1, 480, 0)),
                 ((1200, 720, 64), (480, 720, 1), (-1, 480, 0), (-1, 480, 0)),
                 ((1200, 720, 64), (479, 720, 1), (-1, 480, 0), (-1, 480, 0)),
                 ((0, 1440, 127), (-1, 480, 0), (-1, 480, 0), (-1, 480, 0)),
                 ((1439, 1, 127), (0, 1, 127), (-1, 480, 0), (-1, 480, 0))]
        for rows in (r + ((-1, 480, 0),) for r in cases):
            c.tags[W].update(CandidateOffset=0, CandidateStart=[r[0] for r in rows],
                CandidateDuration=[r[1] for r in rows], CandidateDays=[r[2] for r in rows])
            try:
                line.validate_calendar(0, rows)
                expected = 1
            except ValueError:
                expected = 0
            c.run('\n'.join(line.validation_logic(APP)))
            self.assertEqual(c.tags[W]['Valid'], expected, rows)

    def test_native_overlap_matches_interval_oracle_for_all_weekday_pairs_and_row_positions(self):
        c = controller()
        program = st.parse('\n'.join(line.validation_logic(APP)))
        inactive = (-1, 480, 0)
        calendars = []
        # Same-day overlap, whole days, exact overnight adjacency, one-minute
        # overlap and reversed midnight crossing, in all ten row positions.
        for a, b in itertools.combinations(range(line.MAX_SHIFTS), 2):
            for day, other in itertools.product(range(7), repeat=2):
                for first, second in (((100,120),(100,120)), ((0,1440),(0,1440)),
                        ((1200,720),(480,720)), ((1200,721),(480,720)),
                        ((1439,1),(0,1)), ((0,1),(1439,2))):
                    rows = [inactive] * line.MAX_SHIFTS
                    rows[a], rows[b] = (*first, 1 << day), (*second, 1 << other)
                    calendars.append(rows)
        rng = random.Random(72)
        calendars += [tuple((rng.randrange(-1,1440), rng.randrange(1,1441), rng.randrange(128))
                            for _ in range(line.MAX_SHIFTS)) for _ in range(256)]
        for rows in calendars:
            c.tags[W].update(CandidateOffset=0, CandidateStart=[r[0] for r in rows],
                CandidateDuration=[r[1] for r in rows], CandidateDays=[r[2] for r in rows])
            try:
                line.validate_calendar(0, rows)
                expected = 1
            except ValueError:
                expected = 0
            c.run(program)
            self.assertEqual(c.tags[W]['Valid'], expected, rows)

    def test_native_validation_rejects_invalid_bounds_before_mask_overlap(self):
        c = controller()
        program = st.parse('\n'.join(line.validation_logic(APP)))
        for field, value in (('CandidateOffset',-841), ('CandidateOffset',841),
                ('CandidateStart',-2), ('CandidateStart',1440),
                ('CandidateDuration',0), ('CandidateDuration',1441),
                ('CandidateDays',-1), ('CandidateDays',128)):
            c.tags[W].update(CandidateOffset=0, CandidateStart=[-1]*line.MAX_SHIFTS,
                CandidateDuration=[480]*line.MAX_SHIFTS, CandidateDays=[0]*line.MAX_SHIFTS)
            if field == 'CandidateOffset':
                c.tags[W][field] = value
            else:
                c.tags[W][field][line.MAX_SHIFTS - 1] = value
            c.run(program)
            self.assertEqual(c.tags[W]['Valid'], 0, (field,value))


class Writes(unittest.TestCase):
    def test_same_named_recipe_and_line_values_keep_their_own_storage_and_audit(self):
        import fraktal_ab_config as config
        import fraktal_ab_projection as projection
        import fraktal_ab_data_access as data
        app = dataclasses.replace(APP, baseline_work_member='StartMin1',
            records=tuple(dataclasses.replace(r, members=tuple(
                dataclasses.replace(m, name='StartMin1') if m.name == 'BaselineWorkMs' else m
                for m in r.members)) if r.par_cfg else r for r in APP.records),
            models=tuple(dataclasses.replace(model, values={
                'StartMin1' if k == 'BaselineWorkMs' else k: v for k, v in model.values.items()})
                for model in APP.models))
        self.assertFalse(decl.validate(app))
        c = controller(app)
        bank = c.tags[gen.model_cfg_tag(app)][1]
        old_recipe = bank['StartMin1']
        ordinal = mb.config_ordinal(app, 'line.shift.1.startMin')
        self.assertEqual(execute(c, app, Kind=mb.WRITE_CONFIG, IntValue=ordinal,
            BoolValue=480, DurationMs=2)['Accepted'], 1)
        self.assertEqual(c.tags[CFG]['StartMin1'], 480)
        self.assertEqual(bank['StartMin1'], old_recipe)
        audit = c.tags[config.audit_tag(app)]
        self.assertEqual(audit['ModelOrdinal'][audit['Head'] - 1], 0)
        page = projection.config_page(app, mf.content(app),
            {r.name: c.tags[r.name + 'Tag'] for r in app.records},
            c.tags[gen.model_cfg_tag(app)], model=2, data_levels=c.tags[data.tag(app, 'Levels')])
        prefix = next(k.rsplit('/', 1)[0] for k, v in page.items()
                      if k.endswith('/WriteKey') and v == 'line.shift.1.startMin')
        self.assertEqual(page[prefix + '/ValueText'], '480')
        self.assertFalse(page[prefix + '/ModelScoped'])
        self.assertEqual(execute(c, app, Kind=mb.WRITE_CONFIG,
            IntValue=mb.config_ordinal(app, 'press.recipe.baselineWorkMs'),
            BoolValue=1000, DurationMs=2)['Accepted'], 1)
        self.assertEqual(bank['StartMin1'], 1000)
        self.assertEqual(c.tags[CFG]['StartMin1'], 480)
        self.assertEqual(audit['ModelOrdinal'][audit['Head'] - 1], 2)

    def test_pre_line_station_set_revision_is_compatible_but_foreign_is_not(self):
        # The historical pre-line press, which also predates live documents.
        prior = dataclasses.replace(APP, line=None, config_medium=None,
                                    records=tuple(r for r in APP.records if not r.line_cfg))
        self.assertEqual(mf.content_hash(prior), '66C4A00ABDB4FCC3')
        self.assertEqual([(o, m.write_key) for o, r, m in gen.editable_values(prior)],
                         [(o, m.write_key) for o, r, m in gen.editable_values(APP) if not r.line_cfg])
        for revision in (mf.config_revision(prior), 123456):
            c, doc = set_controller(), document(prior)
            doc[0]['configRev'] = revision
            for item in doc[1:]: item['rev'] = revision
            before = configurations(c)
            result = run_set(c, doc=doc)
            self.assertEqual(result['Accepted'], int(revision == mf.config_revision(prior)))
            self.assertEqual(c.tags[STATE]['Revision'], 1)
            if revision == 123456: self.assertEqual(configurations(c), before)

    def test_line_write_rejects_whole_calendar_overlap_without_revision_or_audit(self):
        c = controller()
        c.tags[CFG].update(StartMin1=480, DurationMin1=720, ActiveDays1=96,
                           StartMin2=479, DurationMin2=60, ActiveDays2=0)
        before = copy.deepcopy(c.tags[CFG])
        answer = execute(c, Kind=mb.WRITE_CONFIG,
            IntValue=mb.config_ordinal(APP, 'line.shift.2.activeDays'), BoolValue=96, DurationMs=0)
        self.assertEqual(answer['Accepted'], 0)
        self.assertEqual(answer['DiagnosticKey'], mf.numeric_key(APP, line.INVALID_KEY))
        self.assertEqual(c.tags[CFG], before)
        self.assertEqual(c.tags[STATE]['Revision'], 1)

    def test_line_edit_while_running_is_authorized_but_operator_cannot_edit(self):
        import fraktal_ab_access as access
        import fraktal_ab_data_access as data
        c = controller()
        c.tags[UNIT]['Running'] = 1
        self.assertEqual(execute(c, Kind=mb.WRITE_CONFIG,
            IntValue=mb.config_ordinal(APP, 'line.shift.1.activeDays'), BoolValue=96, DurationMs=0)['Accepted'], 1)
        self.assertEqual(c.tags[STATE]['Revision'], 2)
        c.tags[access.tag(APP, 'State')]['CurrentLevel'] = 1
        c.run('\n'.join(data.refresh(APP)))
        self.assertEqual(execute(c, Kind=mb.WRITE_CONFIG, BoolValue=0)['Accepted'], 0)
        self.assertEqual(c.tags[CFG]['ActiveDays1'], 96)

    def test_line_set_is_complete_and_atomic_and_cannot_mix_station_values(self):
        for kind in ('overlap', 'missing', 'mixed', 'valid'):
            c = set_controller()
            doc = document(kind=2)
            for item in doc[1:]:
                if item['key'] == 'line.shift.1.startMin': item['value'] = '480'
                if item['key'] == 'line.shift.1.durationMin': item['value'] = '720'
                if item['key'] == 'line.shift.1.activeDays': item['value'] = '96'
                if kind == 'overlap' and item['key'] == 'line.shift.2.startMin': item['value'] = '479'
                if kind == 'overlap' and item['key'] == 'line.shift.2.activeDays': item['value'] = '96'
            if kind == 'missing':
                doc.pop(); doc[0]['records'] -= 1
            if kind == 'mixed':
                doc[-1] = document(kind=1)[1]
            before = configurations(c)
            result = run_set(c, doc=doc)
            self.assertEqual(result['Accepted'], int(kind == 'valid'), kind)
            if kind != 'valid':
                self.assertEqual(configurations(c), before, kind)
                self.assertEqual(c.tags[STATE]['Revision'], 1)
            else:
                self.assertEqual(c.tags[STATE]['Revision'], 2)
                self.assertEqual(c.tags[CFG]['ActiveDays1'], 96)


class Schedule(unittest.TestCase):
    def bench(self, app=APP):
        c = controller(app)
        c.tags[gen.oee_tag(app)] = initial(gen.oee_members())
        c.tags[f'FRK_{app.name}_Clock'] = [2026, 10, 3, 8, 0, 0, 0]
        c.tags[f'FRK_{app.name}_ScanCount'] = 1
        c.tags[gen.health_probe_tag(app)]['TimeIsSynchronized'] = 1
        c.tags[line.tag(app, 'State')].update(LineIdKey=mf.numeric_key(app,app.line.line_id),
                                            OwnerIdKey=mf.numeric_key(app,app.line.owner_id))
        prior = c.calls['JSR']
        bodies = {line.routine(app, n): st.parse('\n'.join(f(app))) for n, f in
            (('Search', line.search_logic), ('Close', line.close_logic), ('Apply', line.apply_calendar))}
        def jsr(plc, args):
            name = args[0][1][0][1]
            if name in bodies: return plc.run(bodies[name])
            if name.endswith('_AccessRecordAudit'):
                import fraktal_ab_access as access
                return plc.run('\n'.join(access.audit_logic(app)))
            return prior(plc, args)
        c.calls['JSR'] = jsr
        return c

    def tick(self, c, when, app=APP):
        c.tags[f'FRK_{app.name}_Clock'] = [when.year, when.month, when.day, when.hour, when.minute, when.second, 0]
        c.tags[f'FRK_{app.name}_NowDate'] = when.year * 10000 + when.month * 100 + when.day
        c.tags[f'FRK_{app.name}_NowTime'] = when.hour * 10000000 + when.minute * 100000 + when.second * 1000 + when.microsecond // 1000
        c.run('\n'.join(line.cyclic(app)))

    def test_empty_and_future_calendar_edits_preserve_unscheduled_production(self):
        c = self.bench()
        started = datetime(2026,10,2,12,tzinfo=timezone.utc)
        self.tick(c, started)
        c.tags[UNIT]['GoodCount'] = 9
        c.tags[CFG]['DurationMin1'] = 720
        c.tags[STATE]['Revision'] += 1
        self.tick(c, datetime(2026,10,2,13,tzinfo=timezone.utc))
        c.tags[CFG].update(StartMin1=480,ActiveDays1=96)
        c.tags[STATE]['Revision'] += 1
        self.tick(c, datetime(2026,10,2,14,tzinfo=timezone.utc))
        self.assertEqual(c.tags[S]['Count'], 0)
        self.assertEqual(c.tags[S]['StartedMinute'], minute(started))
        self.assertEqual(c.tags[UNIT]['GoodCount'],9)
        self.assertEqual(c.tags[S]['EndsMinute'], minute(datetime(2026,10,3,8,tzinfo=timezone.utc)))
        self.tick(c, datetime(2026,10,3,8,tzinfo=timezone.utc))
        self.assertEqual((c.tags[S]['HistoryIndex'][0],c.tags[S]['HistoryGood'][0]), (0,9))

    def test_boundary_snapshot_keeps_subminute_precision_and_all_raw_factors(self):
        app = scheduled(((480,720,96),) + ((-1,480,0),)*(line.MAX_SHIFTS - 1))
        c = self.bench(app)
        self.tick(c,datetime(2026,10,3,8,0,5,123000,tzinfo=timezone.utc),app)
        c.tags[UNIT].update(GoodCount=100,ScrapCount=10)
        c.tags[OEE].update(RunS=400,RunMs=123,DownS=20,DownMs=456,IdleS=30,IdleMs=789)
        ended = datetime(2026,10,3,20,0,9,456000,tzinfo=timezone.utc)
        self.tick(c,ended,app)
        out = line.projection(app,c.tags[STATE],c.tags[S],rows=mf.content(app))
        self.assertEqual(out['ShiftHistory[1]/StartAt'],'2026-10-03T08:00:05.123000+00:00')
        self.assertEqual(out['ShiftHistory[1]/EndAt'],ended.isoformat())
        self.assertEqual(out['ShiftHistory[1]/RunMs'],400123)
        self.assertEqual(out['ShiftHistory[1]/DownMs'],20456)
        self.assertEqual(out['ShiftHistory[1]/IdleMs'],30789)
        self.assertEqual(out['ShiftHistory[1]/GoodCount'],100)
        self.assertEqual(out['ShiftHistory[1]/NokCount'],10)
        self.assertAlmostEqual(out['ShiftHistory[1]/Availability'],400123/420579)
        self.assertAlmostEqual(out['ShiftHistory[1]/Quality'],100/110)
        self.assertTrue(out['ShiftHistory[1]/PerfValid'])
        self.assertEqual(out['Line/LineId'],app.line.line_id)

    def test_manual_oee_reset_keeps_full_counts_and_the_reset_window_factors(self):
        app = scheduled(((480,720,96),) + ((-1,480,0),)*(line.MAX_SHIFTS - 1))
        c = self.bench(app)
        self.tick(c,datetime(2026,10,3,8,tzinfo=timezone.utc),app)
        c.tags[UNIT].update(GoodCount=30,ScrapCount=5)
        c.run('\n'.join(gen.oee_reset_lines(app)))
        c.tags[S]['ManualReset'] = 1
        c.tags[UNIT].update(GoodCount=100,ScrapCount=10)
        c.tags[OEE].update(RunS=400,DownS=20)
        self.tick(c,datetime(2026,10,3,20,tzinfo=timezone.utc),app)
        out = line.projection(app,c.tags[STATE],c.tags[S])
        self.assertEqual(out['ShiftHistory[1]/GoodCount'],100)
        self.assertEqual(out['ShiftHistory[1]/NokCount'],10)
        self.assertAlmostEqual(out['ShiftHistory[1]/Quality'],70/75)
        self.assertTrue(out['ShiftHistory[1]/ManualReset'])

    def test_weekend_12_hour_boundaries_and_unscheduled_accounting(self):
        app = scheduled(((480, 720, 96),) + ((-1, 480, 0),) * (line.MAX_SHIFTS - 1))
        c = self.bench(app)
        self.tick(c, datetime(2026, 10, 3, 7, 59, tzinfo=timezone.utc), app)
        self.assertEqual(c.tags[S]['Current'], 0)
        self.tick(c, datetime(2026, 10, 3, 8, tzinfo=timezone.utc), app)
        self.assertEqual(c.tags[S]['Current'], 1)
        c.tags[UNIT].update(GoodCount=10, ScrapCount=2, ReworkCount=1)
        c.tags[OEE].update(RunS=400, DownS=20, IdleS=30, Head=7)
        self.tick(c, datetime(2026, 10, 3, 20, tzinfo=timezone.utc), app)
        self.assertEqual(c.tags[S]['Current'], 0)
        self.assertEqual(c.tags[S]['HistoryGood'][0], 10)
        self.assertEqual(c.tags[S]['HistoryRework'][0], 1)
        self.assertEqual(c.tags[UNIT]['GoodCount'], 0)
        self.assertEqual(c.tags[OEE]['Head'], 7)  # closure keeps the trend
        self.assertEqual(c.tags[S]['EndsMinute'], minute(datetime(2026,10,4,8,tzinfo=timezone.utc)))
        c.tags[UNIT]['GoodCount'] = 3
        self.tick(c, datetime(2026, 10, 4, 8, tzinfo=timezone.utc), app)
        self.assertEqual((c.tags[S]['HistoryIndex'][0], c.tags[S]['HistoryGood'][0]), (0, 3))
        self.tick(c, datetime(2026,10,4,20,tzinfo=timezone.utc),app)
        self.assertEqual(c.tags[S]['EndsMinute'], minute(datetime(2026,10,10,8,tzinfo=timezone.utc)))

    def test_sunday_overnight_applies_to_start_day_with_offset(self):
        app = scheduled(((1200, 720, 64),) + ((-1, 480, 0),) * (line.MAX_SHIFTS - 1), offset=-300)
        c = self.bench(app)
        self.tick(c, datetime(2026,10,5,7,tzinfo=timezone.utc),app)  # Monday 02 local
        self.assertEqual(c.tags[S]['Current'], 1)
        self.assertEqual(c.tags[S]['EndsMinute'], minute(datetime(2026,10,5,13,tzinfo=timezone.utc)))

    def test_edits_wait_until_boundary_and_do_not_rewrite_history(self):
        app = scheduled(line.migrate_daily(0, (0,480,960,-1)))
        c = self.bench(app)
        self.tick(c, datetime(2026,10,3,7,tzinfo=timezone.utc),app)
        c.tags[CFG].update(StartMin1=-1, StartMin2=-1, StartMin3=-1)
        c.tags[STATE]['Revision'] += 1
        self.tick(c, datetime(2026,10,3,7,59,tzinfo=timezone.utc),app)
        self.assertEqual(c.tags[S]['Current'], 1)
        self.assertEqual(c.tags[S]['AppliedRevision'], 1)
        self.tick(c, datetime(2026,10,3,8,tzinfo=timezone.utc),app)
        self.assertEqual(c.tags[S]['Current'], 0)
        self.assertEqual(c.tags[S]['AppliedRevision'], 2)
        self.assertEqual(c.tags[S]['HistoryIndex'][0], 1)

    def test_history_bounds_quality_manual_reset_and_raw_snapshot_projection(self):
        app = scheduled(line.migrate_daily(0, (0,480,960,-1)))
        c = self.bench(app)
        start = datetime(2026,10,3,0,tzinfo=timezone.utc)
        self.tick(c, start, app)
        from datetime import timedelta
        for i in range(1, 11):
            c.tags[UNIT]['GoodCount'] = i
            c.tags[S]['ManualReset'] = int(i == 10)
            c.tags[gen.health_probe_tag(app)]['TimeIsSynchronized'] = int(i != 10)
            self.tick(c, start + timedelta(hours=8*i), app)
        self.assertEqual((c.tags[S]['Count'],c.tags[S]['Truncated']), (8,1))
        self.assertEqual(c.tags[S]['HistoryGood'], list(range(10,2,-1)))
        self.assertEqual(c.tags[S]['HistoryTimeSynchronized'][0], 0)
        out = line.projection(app,c.tags[STATE],c.tags[S])
        self.assertEqual(out['ShiftHistory[1]/GoodCount'],10)
        self.assertTrue(out['ShiftHistory[1]/ManualReset'])
        self.assertTrue(out['ShiftHistory[1]/OeeValid'])  # quality factor is valid

    def test_epoch_minutes_match_independent_clock_across_leap_and_year_boundaries(self):
        c = self.bench()
        for when in (datetime(1970,1,1,tzinfo=timezone.utc), datetime(2000,2,29,23,59,tzinfo=timezone.utc),
                     datetime(2024,3,1,tzinfo=timezone.utc), datetime(2099,12,31,23,59,tzinfo=timezone.utc)):
            c.tags['FRK_Press_Clock'] = [when.year,when.month,when.day,when.hour,when.minute,0,0]
            c.run('\n'.join(line.clock_logic(APP)))
            self.assertEqual(c.tags[W]['NowMinute'],minute(when))

    def test_forward_jump_closes_once_with_quality_false_and_backward_jump_preserves_history(self):
        app = scheduled(line.migrate_daily(0, (0,480,960,-1)))
        c = self.bench(app)
        self.tick(c,datetime(2026,10,3,7,tzinfo=timezone.utc),app)
        self.tick(c,datetime(2026,10,4,9,tzinfo=timezone.utc),app)
        self.assertEqual(c.tags[S]['Count'],1)
        self.assertEqual(c.tags[S]['HistoryTimeSynchronized'][0],0)
        history = copy.deepcopy(c.tags[S])
        self.tick(c,datetime(2026,10,3,6,tzinfo=timezone.utc),app)
        self.assertEqual(c.tags[S]['HistoryGood'],history['HistoryGood'])
        self.assertEqual(c.tags[S]['Count'],1)
        self.assertEqual(c.tags[S]['TimeSynchronized'],0)


if __name__ == '__main__':
    unittest.main()
