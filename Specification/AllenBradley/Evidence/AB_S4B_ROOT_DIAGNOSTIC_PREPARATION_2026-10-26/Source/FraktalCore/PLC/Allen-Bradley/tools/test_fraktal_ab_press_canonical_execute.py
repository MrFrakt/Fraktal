"""The press walk's machine core, against a scripted Unit; no controller."""
from pathlib import Path
import unittest
from unittest.mock import patch

import fraktal_ab_mailbox as mb
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_canonical_echo38 as candidate
import fraktal_ab_press_canonical_execute as walk
import fraktal_ab_press_execute as px


class ScriptedRun(walk.PressRun):
    """Just enough Unit behaviour for the six cases: cycles, scrap decision, hold, abort, fault."""

    def __init__(self):
        self.app, self.rows, self.comm = candidate.application(), [], None
        self.stimuli = {}
        self.state = dict(Mode=0, Running=0, Complete=0, Error=0, ErrorID=0, Aborted=0, DecisionId=0,
                          GoodCount=0, ScrapCount=0, ReworkCount=0, CycleCount=0, Step=0)
        self.scrap = False

    def unit(self):
        return dict(self.state)

    def home(self):
        self.state.update(Running=0, Error=0, Aborted=0, DecisionId=0)

    def set(self, tag, value):
        self.stimuli[tag] = value

    def begin(self):
        s = self.state
        s.update(Running=1, Step=100)
        if self.stimuli.get(px.FAULT['PartSlide']):
            s.update(Running=0, Error=1, ErrorID=12345)
        elif self.stimuli.get(px.FAULT['PressRam']):
            s['DecisionId'] = 7

    def command(self, kind, **arguments):
        s = self.state
        if kind == mb.DECISION_ANSWER:
            self.scrap, s['DecisionId'] = True, 0
        elif kind == mb.STOP:
            s.update(Running=0, Aborted=1)
        elif kind == mb.SET_MODE:
            # Like the generated Unit: the chain stands down, the run level keeps Running.
            s.update(Step=0, Mode=arguments['IntValue'])
        elif kind == mb.OPERATOR_RESET:
            s.update(Error=0, ErrorID=0, Aborted=0)

    def complete(self, baseline):
        s = self.state
        if s['Running'] and not self.stimuli.get(px.HOLD['PressRam']):
            s['CycleCount'] += 1
            s['ScrapCount' if self.scrap else 'GoodCount'] += 1
            s['Running'], self.scrap = 0, False
        self.check(s['CycleCount'] > baseline['CycleCount'], 'cycle finish')

    def wait(self, test, label, timeout=8):
        value = test()
        self.check(bool(value), label+' did not settle')
        return value


class WalkTests(unittest.TestCase):
    def test_six_cases_record_the_capture_layer_case_names_and_pass_their_checks(self):
        run = ScriptedRun()
        held = lambda comm, module: {'OutImm_Held': bool(run.stimuli.get(px.HOLD['PressRam']))}
        with patch.object(px, 'read_module', side_effect=held), patch.object(walk.time, 'sleep'):
            for operation in (run.happy, run.nok, run.held, lambda lang: run.held(lang, 'abort'),
                              lambda lang: run.held(lang, 'mode'), run.adopted_fault):
                operation('LD')
        self.assertEqual([r['case'] for r in run.rows],
                         ['OK', 'handled_NOK', 'HELD_resume', 'abort', 'mode_change', 'adopted_fault', 'single_reset_restart'])
        self.assertEqual(run.rows[1]['counters']['ScrapCount'], 1)
        self.assertEqual(run.rows[5]['firstOut'], 12345)
        self.assertEqual(run.rows[4]['unit']['Mode'], run.app.manual_mode)

    def test_a_case_that_counts_wrongly_is_refused(self):
        run = ScriptedRun()
        run.complete = lambda baseline: run.state.update(CycleCount=run.state['CycleCount']+1, ScrapCount=run.state['ScrapCount']+1)
        with self.assertRaisesRegex(fixture.FixtureRefused, 'OK verdict count'):
            run.happy('ST')

    def test_assembled_run_stacks_every_capture_layer_on_the_press_base_only(self):
        names = [c.__name__ for c in walk.paired_run(Path('unused.json')).__mro__]
        for layer in ('TypedRun', 'ConfigRun', 'AccessRun', 'AlarmRun', 'SequenceRun', 'PairedRun', 'PressRun', 'Run'):
            self.assertIn(layer, names)
        for genealogy_only in ('GenealogyRun', 'TextResourceRun', 'ResourceRun'):
            self.assertNotIn(genealogy_only, names)


class MediumTests(unittest.TestCase):
    """The press is commissioned from its own image's documents, never the genealogy medium."""

    def held(self, app):
        import fraktal_ab_generate as gen
        import fraktal_ab_live as live
        records = {}
        for unused, record, member in gen.editable_values(app):
            records.setdefault(record.name, {})[member.name] = member.minimum
        models = [m.code for m in app.models]
        banks = [{member.name: member.minimum for record in app.records for member in record.members}
                 for _ in models]
        return live.Capture(restoring=True, records=records, banks=banks, codes=models, model_ordinal=1)

    def test_seeding_writes_exactly_the_image_documents_and_refuses_a_used_medium(self):
        import os, tempfile
        import fraktal_ab_live as live
        import fraktal_ab_medium as medium
        run = ScriptedRun(); run.evidence = dict(serial='601FC87B')
        held = self.held(run.app)
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {medium.SET_DIR_ENV: directory}), \
             patch('fraktal_ab_projection.read_document', return_value={'liveConfig': held}):
            walk.seed_medium(run)
            store = live.FileMedium(live.live_directory(run.app, '601FC87B'))
            wanted = live.documents(run.app, held, 0)
            self.assertEqual({k: live.content(store.read(k)) for k in wanted}, {k: live.content(d) for k, d in wanted.items()})
            self.assertEqual(run.evidence['pressMedium']['seeded'], sorted(wanted))
            with self.assertRaisesRegex(fixture.FixtureRefused, 'must start empty'):
                walk.seed_medium(run)

    def test_seeding_refuses_without_an_isolated_medium(self):
        import os
        import fraktal_ab_medium as medium
        run = ScriptedRun(); run.evidence = dict(serial='601FC87B')
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(medium.SET_DIR_ENV, None)
            with self.assertRaisesRegex(fixture.FixtureRefused, 'not selected'):
                walk.seed_medium(run)

    def test_main_isolates_the_medium_beside_the_output_and_passes_it_on(self):
        import os, tempfile
        import fraktal_ab_medium as medium
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}):
            output = Path(directory)/'request_cases.json'
            with patch.object(walk.typed, 'authorize'), patch.object(walk.live, 'main', return_value=0) as selected:
                walk.main(['--authorization-file', 'a.json', '--expect-acd-sha256', 'A'*64, '--output', str(output),
                           '--execute-fixture'])
            isolated = Path(directory)/'request_cases_press_medium'
            self.assertTrue(isolated.is_dir())
            self.assertEqual(os.environ[medium.SET_DIR_ENV], str(isolated))
            self.assertEqual(selected.call_args.args[0][-2:], ['--output', str(output)])
            self.assertEqual(selected.call_args.kwargs['expected_declaration'], walk.DECLARATION)
            with self.assertRaisesRegex(fixture.FixtureRefused, 'already exists'):
                walk.isolate_medium(output)


if __name__ == '__main__': unittest.main()
