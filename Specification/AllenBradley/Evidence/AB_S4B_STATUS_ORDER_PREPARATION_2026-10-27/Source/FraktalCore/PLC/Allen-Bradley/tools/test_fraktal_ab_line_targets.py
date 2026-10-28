"""Five-slot calendars and immutable good-part targets on generated Logix ST."""
import copy
import dataclasses
from datetime import datetime, timezone
import unittest
import fraktal_ab_line as line
import test_fraktal_ab_line as line_tests
import fraktal_ab_declaration as decl
import fraktal_ab_initial_config as initial_cfg
import fraktal_ab_manifest as mf
import fraktal_ab_mailbox as mb
from test_fraktal_ab_line import APP, W, S, STATE, CFG, UNIT, scheduled
from test_fraktal_ab_capture import controller, execute
from test_fraktal_ab_sets import controller as set_controller, document, run as run_set
from test_fraktal_ab_initial_config import expanded_image

ROWS = ((0, 480, 31), (480, 480, 31), (960, 480, 31), (0, 720, 96), (720, 720, 96))

class Targets(unittest.TestCase):
    def test_five_slot_calendar_and_append_only_capabilities(self):
        app = scheduled(ROWS)
        self.assertFalse(decl.validate(app))
        self.assertEqual(len([m for m in line.cfg(app).members if m.write_key]), 21)
        self.assertEqual(mf.content(app)['OptionalProfiles'][0]['ProfileVersion'], 3)
        for row in mf.content(app)['WriteCapabilities'][-5:]:
            self.assertEqual(row['UnitCode'], 30)
        self.assertEqual([m.write_key for m in line.cfg(app).members[1:14]],
            ['line.shift.utcOffsetMin'] + [f'line.shift.{i}.{name}' for i in range(1, 5)
            for name in ('startMin', 'durationMin', 'activeDays')])
        for targets in ((0,) * 4, (-1,) * 5, (2147483648,) * 5, (True,) * 5):
            with self.assertRaises(ValueError):
                line.record(dataclasses.replace(app.line, production_targets=targets))

    def test_explicit_weekly_image_migration_preserves_all_other_records_and_catalog(self):
        image = expanded_image()
        new = image['records'].pop(line.cfg(APP).name)
        old = {k: v for k, v in new.items() if k in {'SchemaVersion', 'UtcOffsetMin'}
               or k in {f'{n}{i}' for i in range(1, 5) for n in ('StartMin', 'DurationMin', 'ActiveDays')}}
        old.update(SchemaVersion=2, StartMin1=1200, DurationMin1=720, ActiveDays1=64)
        image['records']['FRK_T_LineCfgV2'] = old
        before = copy.deepcopy(image)
        result = initial_cfg.migrate_line_v2(APP, image)
        self.assertEqual(image, before)
        self.assertEqual(result['models'], before['models'])
        self.assertEqual(result['modelCodes'], before['modelCodes'])
        new = result['records'].pop(line.cfg(APP).name)
        self.assertEqual({k: v for k, v in new.items() if k in old and k != 'SchemaVersion'},
                         {k: v for k, v in old.items() if k != 'SchemaVersion'})
        self.assertEqual(new['SchemaVersion'], 3)
        self.assertEqual((new['StartMin5'], new['ActiveDays5']), (-1, 0))
        self.assertEqual([new[f'ProductionTarget{i}'] for i in range(1, 6)], [0]*5)
        self.assertEqual(result['records'], {k: v for k, v in before['records'].items() if k != 'FRK_T_LineCfgV2'})
        for change in ({'Execute': 1}, {'SchemaVersion': 1}, {'ActiveDays1': 128}):
            bad = copy.deepcopy(before)
            bad['records']['FRK_T_LineCfgV2'].update(change)
            with self.assertRaises(ValueError): initial_cfg.migrate_line_v2(APP, bad)

    def test_target_is_bounded_and_in_whole_line_sets(self):
        c = controller()
        key = mb.config_ordinal(APP, 'line.shift.5.productionTarget')
        self.assertEqual(execute(c, Kind=mb.WRITE_CONFIG, IntValue=key, BoolValue=1200)['Accepted'], 1)
        self.assertEqual(c.tags[CFG]['ProductionTarget5'], 1200)
        import fraktal_ab_access as access
        import fraktal_ab_data_access as data
        c.tags[access.tag(APP, 'State')]['CurrentLevel'] = 1
        c.run('\n'.join(data.refresh(APP)))
        self.assertEqual(execute(c, Kind=mb.WRITE_CONFIG, IntValue=key, BoolValue=1300)['Accepted'], 0)
        self.assertEqual(c.tags[CFG]['ProductionTarget5'], 1200)
        self.assertEqual(execute(c, Kind=mb.WRITE_CONFIG, IntValue=key, BoolValue=-1)['Accepted'], 0)
        self.assertEqual(c.tags[CFG]['ProductionTarget5'], 1200)
        c = set_controller()
        doc = document(kind=2)
        for row in doc[1:]:
            if row['key'] == 'line.shift.5.productionTarget': row['value'] = '2400'
        self.assertEqual(run_set(c, doc=doc)['Accepted'], 1)
        self.assertEqual(c.tags[CFG]['ProductionTarget5'], 2400)

    def test_native_weekday_three_weekend_two_and_target_snapshots(self):
        declaration = line.Line('PRESS-LINE-1', 'Press', shifts=ROWS,
                                production_targets=(800, 900, 1000, 1200, 1300))
        app = dataclasses.replace(APP, line=declaration, records=tuple(
            line.record(declaration) if r.line_cfg else r for r in APP.records))
        schedule = line_tests.Schedule()
        c = schedule.bench(app)
        for day, hour, index, target in ((2, 0, 1, 800), (2, 8, 2, 900),
                (2, 16, 3, 1000), (3, 0, 4, 1200), (3, 12, 5, 1300),
                (4, 0, 4, 1200), (4, 12, 5, 1300), (5, 0, 1, 800)):
            schedule.tick(c, datetime(2026, 10, day, hour, tzinfo=timezone.utc), app)
            self.assertEqual((c.tags[S]['Current'], c.tags[S]['ProductionTarget']), (index, target))
        c.tags[CFG]['ProductionTarget2'] = 950
        c.tags[CFG]['ProductionTarget1'] = 1600
        c.tags[STATE]['Revision'] += 1
        c.tags[UNIT]['GoodCount'] = 850
        schedule.tick(c, datetime(2026, 10, 5, 7, 59, tzinfo=timezone.utc), app)
        self.assertEqual(c.tags[S]['ProductionTarget'], 800)
        schedule.tick(c, datetime(2026, 10, 5, 8, tzinfo=timezone.utc), app)
        out = line.projection(app, c.tags[STATE], c.tags[S])
        self.assertEqual(out['ShiftProductionTarget'], 950)
        self.assertEqual(out['ShiftHistory[1]/ProductionTarget'], 800)
        self.assertEqual(out['ShiftHistory[1]/GoodCount'], 850)
        c.tags[CFG]['ProductionTarget1'] = 2000
        self.assertEqual(c.tags[S]['HistoryProductionTarget'][0], 800)
        c.tags[W]['CandidateTarget'][4] = -1
        c.run('\n'.join(line.validation_logic(app)))
        self.assertEqual(c.tags[W]['Valid'], 0)

if __name__ == '__main__': unittest.main()
