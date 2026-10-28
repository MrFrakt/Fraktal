"""The press S3 exit candidate is the press declaration plus only accepted choices."""
from dataclasses import fields, replace
import re
import sys
import unittest
from unittest.mock import patch

import fraktal_ab_declaration as decl
import fraktal_ab_genealogy_s3k_demo as genealogy
import fraktal_ab_press_canonical_echo38 as candidate
import fraktal_ab_press_demo as press
import fraktal_ab_press_echo38 as echo
import fraktal_ab_press_rendition_echo38 as oracle
import fraktal_ab_s3k_equivalence as equivalence

CANONICAL = ('canonical_publication_stage', 'canonical_observation_period_ms', 'canonical_table_driven',
             'canonical_type_manifest', 'canonical_io_fixture')


def changed(a, b):
    return {f.name for f in fields(a) if getattr(a, f.name) != getattr(b, f.name)}


def contract(app):
    return equivalence.subset_paths(app, [m.code for m in app.models], canonical=True, count=0, shift_count=0)


class DeclarationTests(unittest.TestCase):
    def test_candidate_adds_only_the_accepted_s3k_choices_and_validates(self):
        app, base = candidate.application(), oracle.application()
        self.assertFalse(decl.validate(app))
        self.assertEqual(changed(app, base), {*CANONICAL, 'io_modules'})
        self.assertEqual({n: getattr(app, n) for n in CANONICAL}, {n: getattr(genealogy.application(), n) for n in CANONICAL})
        self.assertEqual([m.sample_tag for m in app.io_modules], ['FRK_Press_SimIo'])

    def test_oracle_changes_only_auto_renditions_and_contains_the_shipped_selection(self):
        app, base = oracle.application(), echo.application()
        self.assertEqual(changed(app, base), {'chains'})
        mine, theirs = ({c.name: c for c in a.chains} for a in (app, base))
        self.assertEqual(mine['AUTO'].renditions, decl.RENDITIONS)
        self.assertEqual(replace(mine['AUTO'], renditions=theirs['AUTO'].renditions), theirs['AUTO'])
        self.assertTrue(all(mine[n] == theirs[n] for n in mine if n != 'AUTO'))
        shipped = next(c for c in press.application().chains if c.name == 'AUTO').renditions
        self.assertTrue(set(shipped) <= set(mine['AUTO'].renditions))


class ContractTests(unittest.TestCase):
    def test_press_contract_is_the_genealogy_contract_minus_undeclared_or_smaller_surfaces(self):
        press_paths, genealogy_paths = contract(candidate.application()), contract(genealogy.application())
        self.assertFalse(press_paths - genealogy_paths)
        self.assertEqual(equivalence.mailbox_paths(candidate.application(), canonical=True),
                         equivalence.mailbox_paths(genealogy.application(), canonical=True))
        families = {re.sub(r'\[\d+\]', '[*]', p).split('/')[1] for p in genealogy_paths - press_paths}
        self.assertEqual(families, {'AlarmLog', 'Part', 'SequenceSteps[*]', 'HostEvents',
                                    'SequenceAnnotations[*]', 'Nameplate', 'SignalTower'})
        for owner in ('Part', 'HostEvents', 'Nameplate', 'SignalTower'):
            # The trailing slash keeps the PartSlide module out of the Part owner.
            self.assertFalse(any(p.startswith('Press/'+owner+'/') for p in press_paths), owner)
        self.assertTrue(equivalence.logical_types(candidate.application(), press_paths))


class InputTests(unittest.TestCase):
    def test_undeclared_part_and_tower_owners_are_never_read(self):
        import fraktal_ab_s3h_equivalence as s3h
        app = candidate.application()
        with patch.object(s3h.previous, 'additional_inputs', return_value={}), \
             patch('fraktal_ab_projection.APP', app), \
             patch.object(s3h.part, 'read', side_effect=AssertionError('part read')), \
             patch('fraktal_ab_press_execute.read_layout', side_effect=AssertionError('tower read')), \
             patch('fraktal_ab_models.read', return_value=()):
            result = s3h.additional_inputs(object())
        self.assertEqual((result['part'], result['host'], result['tower']), (None, None, None))

    def test_towerless_oracle_classifies_machine_state_like_the_plc(self):
        import fraktal_ab_machine_state as machine
        import fraktal_ab_s3h_equivalence as s3h
        app = candidate.application()
        unit = dict(Error=0, Mode=app.manual_mode, Running=1, Aborted=0, Step=0)
        additional = dict(part=None, host=None, tower=None, alarmActive=dict(Blocking=0))
        with patch.object(s3h.previous, 'extra_values', return_value={}), patch('fraktal_ab_projection.APP', app):
            values = s3h.extra_values(app, unit, additional)
        self.assertEqual(values['Press/MachineState'], machine.classify(app, unit, 0))

    def test_press_oracle_produces_every_contract_path_from_recorded_native_inputs(self):
        """The accepted genealogy idle capture's inputs, with the press's absent owners and keys."""
        import gzip, json
        from pathlib import Path
        import fraktal_ab_genealogy_s3k_demo as genealogy
        import fraktal_ab_manifest as manifest
        import fraktal_ab_projection as projection
        capture = Path(__file__).resolve().parents[4]/'Specification/AllenBradley/Evidence/AB_S3K_CANONICAL_RUNTIME_2026-10-25/Runtime/idle_equivalence.json.gz'
        held = json.loads(gzip.decompress(capture.read_bytes()))['pair']['legacyInputs']
        app = candidate.application()
        portable = {r['NumericKey']: r['PortableKey'] for r in manifest.content(genealogy.application())['Localization']}
        numeric = {r['PortableKey']: r['NumericKey'] for r in manifest.content(app)['Localization']}
        def remap(value, name=''):
            # The catalogues number keys differently; translate only fields that hold a key.
            if isinstance(value, dict): return {k: remap(v, k) for k, v in value.items()}
            if isinstance(value, list): return [remap(v, name) for v in value]
            if name.endswith('Key') and type(value) is int and portable.get(value) in numeric: return numeric[portable[value]]
            return value
        additional = remap(dict(held['additional'], part=None, host=None, tower=None))
        expected = equivalence.subset_paths(app, held['codes'], canonical=False, count=0,
                                            shift_count=additional['line_shift']['Count'])
        extra = lambda a, u: equivalence.extra_values(a, u, additional, page=0, model=0, provider_state={})
        import fraktal_ab_s2_equivalence as shared
        with patch.object(projection, 'APP', app):
            result = shared.oracle(app, manifest.content(app), held['unit'], held['contexts'], held['codes'],
                                   expected=expected, extra=extra, logical_types=equivalence.logical_types)
        self.assertEqual(set(result['values']), expected)

    def test_shared_runner_refuses_an_oracle_bound_to_another_declaration(self):
        import fraktal_ab_s2_equivalence as shared
        def attempt(bound_app):
            bound = type(sys)('fraktal_ab_projection'); bound.APP = bound_app
            with patch.dict(sys.modules, {'fraktal_ab_projection': bound}), patch.dict('os.environ', {}):
                shared.run(object(), application_factory=candidate.application,
                           oracle_declaration='fraktal_ab_press_rendition_echo38')
        with self.assertRaisesRegex(ValueError, 'already bound'):
            attempt(echo.application())
        # The oracle declaration itself, or the walk's candidate, proceed to the controller.
        for bound_app in (oracle.application(), candidate.application()):
            with self.assertRaises(AttributeError):
                attempt(bound_app)


if __name__ == '__main__': unittest.main()
