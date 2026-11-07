"""O10 (WP6.6 C4): the acceptance-only fixture observation."""

import dataclasses
import random
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_declaration as decl
import fraktal_ab_fixture_observation as fixture
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s6_collapse_demo as genealogy
import fraktal_ab_press_canonical_echo38 as candidate
import fraktal_ab_press_s6_collapse_echo38 as press
import fraktal_ab_st_model as st
from test_fraktal_ab_generate import SEED_38

APP = press.application()


def generate(app):
    with tempfile.TemporaryDirectory() as folder:
        seed, out = Path(folder) / 'seed.L5X', Path(folder) / 'out.L5X'
        seed.write_text(SEED_38, encoding='utf-8')
        gen.generate(app, seed, out)
        return ET.parse(out).getroot()


class Declaration(unittest.TestCase):
    def test_the_press_declares_its_harnesses_facts(self):
        self.assertEqual(decl.validate(APP), [])
        self.assertEqual(len(fixture.facts(APP)), 141)

    def test_only_a_collapsed_acceptance_image_observes(self):
        uncollapsed = dataclasses.replace(candidate.application(), fixture_observation=press.FIXTURE)
        self.assertTrue(any('canonical_collapse' in f for f in fixture.validate(uncollapsed)))
        self.assertEqual(fixture.records(candidate.application()), [])
        self.assertEqual(fixture.logic(candidate.application()), [])

    def test_an_unknown_surface_member_or_repeat_is_refused(self):
        for facts, expected in (((('Nowhere', ('Error',)),), 'no surface'),
                                ((('Unit', ('NoSuchMember',)),), 'no private member'),
                                ((('Unit', ('Mode',)),), 'no private member'),  # C2: canonical now
                                ((('Unit', ('Error', 'Error')),), 'named twice')):
            with self.subTest(facts=facts):
                findings = fixture.validate(dataclasses.replace(APP, fixture_observation=facts))
                self.assertTrue(any(expected in f for f in findings), findings)


class Copy(unittest.TestCase):
    def test_each_scan_copies_every_declared_fact_from_its_source(self):
        rng = random.Random(7)
        sources = {}
        for surface, member, _, source in fixture.facts(APP):
            sources.setdefault(source, {})
        tags = {source: {} for source in sources}
        for _, member, _, source in fixture.facts(APP):
            tags[source][member.name] = ([rng.randint(-5, 500) for _ in range(member.dimension)]
                                         if member.dimension else rng.randint(-5, 500))
        observed = {name: [0] * m.dimension if m.dimension else 0 for _, m, name, _ in fixture.facts(APP)}
        tags.update({fixture.tag(APP): observed, fixture.index_tag(APP): 0})
        st.Controller(tags).run('\n'.join(fixture.logic(APP)))
        for _, member, name, source in fixture.facts(APP):
            with self.subTest(name):
                self.assertEqual(observed[name], tags[source][member.name])


class Image(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.press, cls.genealogy = generate(APP), generate(genealogy.application())

    def tags(self, root):
        return {t.get('Name'): t for t in root.find('Controller').find('Tags')}

    def test_the_structure_is_read_only_and_never_in_the_manifest(self):
        tags = self.tags(self.press)
        self.assertEqual(tags[fixture.tag(APP)].get('ExternalAccess'), 'Read Only')
        manifest = ET.tostring(tags['FRK_Press_CanonicalManifest'], encoding='unicode')
        self.assertNotIn('FixtureObservation', manifest)

    def test_the_press_emits_the_scan_bindings_its_live_reader_requires(self):
        import fraktal_ab_canonical_manifest as wire
        import fraktal_ab_canonical_publication as pub
        import fraktal_ab_schema_identity as schema
        from test_fraktal_ab_read_coherence import physical
        tag = self.tags(self.press)[pub.header_tag(APP)]
        record = schema._value(tag.find('./Data[@Format="Decorated"]/Structure'))
        self.assertEqual(record['SchemaMinor'], '11')
        # Decorated values are textual, not the S1 wire decoder's typed
        # StringFamily objects. These two identifier fields have no escapes.
        def identifier(value):
            literal = value['DATA'].strip()
            self.assertRegex(literal, r"^'[A-Za-z0-9_/]+'$")
            self.assertEqual(int(value['LEN']), len(literal) - 2)
            return literal[1:-1]
        bindings = [dict(CanonicalPrefix=identifier(row['CanonicalPrefix']),
                         RevisionSymbol=identifier(row['RevisionSymbol']),
                         Protocol=int(row['Protocol']), MutationPeriodUs=int(row['MutationPeriodUs']))
                    for row in record['ReadCoherenceBindings']]
        self.assertEqual(int(record['ReadCoherenceBindingsCount']), len(bindings))
        header = wire.normalize(physical(pub.manifest_values(APP)))
        self.assertEqual(header['schemaMinor'], 11)
        prefixes = {APP.name, *(p['CanonicalRoot'] for p in header['dataProducts'])}
        self.assertEqual(bindings, header['readCoherenceBindings'])
        self.assertEqual({b['CanonicalPrefix'] for b in bindings}, prefixes)
        self.assertEqual({b['RevisionSymbol'] for b in bindings}, {pub.generation_tag(APP)})
        self.assertEqual({b['MutationPeriodUs'] for b in bindings}, {APP.task_period_ms * 1000})

    def test_the_s3h_frame_is_gone_from_both_collapsed_images(self):
        for root in (self.press, self.genealogy):
            self.assertFalse([n for n in self.tags(root) if 'ObservationFrame' in n or 'ObservationGeneration' in n])

    def test_the_genealogy_joins_only_with_its_accounted_mailbox_key(self):
        app = genealogy.application()
        self.assertEqual([(surface, member.name) for surface, member, _, _ in fixture.facts(app)],
                         [("Mailbox", "DiagnosticKey")])
        tags = self.tags(self.genealogy)
        self.assertEqual(tags[fixture.tag(app)].get("ExternalAccess"), "Read Only")
        self.assertNotEqual(fixture.type_name(app), fixture.type_name(APP))

    def routines(self, root):
        return {r.get('Name'): '\n'.join(e.text or '' for e in r.iter() if e.tag in ('Line', 'Text'))
                for r in root.iter('Routine')}

    def test_the_copy_lies_inside_the_generations_odd_window(self):
        """One even generation before and after a read proves the fixture with the rows.

        The generation opens (odd) at the start of the scan and closes (even)
        at the end of the canonical publication. The copy is called there,
        before that close, and from nowhere else; nothing else writes it.
        """
        generation = f'FRK_{APP.name}_CanonicalGeneration'
        call = f'JSR({fixture.routine_name(APP)}, 0);'  # as the ST formatter emits it
        routines = self.routines(self.press)
        self.assertIn(fixture.routine_name(APP), routines)
        callers = [name for name, text in routines.items() if fixture.routine_name(APP) + ',' in text]
        self.assertEqual(callers, [f'FRK_{APP.name}_ScanCanonical'])
        lines = [line.strip() for line in routines[callers[0]].splitlines()]
        self.assertEqual(lines.count(call), 1)
        close = [i for i, line in enumerate(lines) if line == f'{generation} := {generation} + 1;']
        self.assertEqual(len(close), 1)
        self.assertEqual(lines.index(call), close[0] - 1)
        writers = [name for name, text in routines.items()
                   if any(line.strip().startswith(fixture.tag(APP) + '.') for line in text.splitlines())]
        self.assertEqual(writers, [fixture.routine_name(APP)])
        opened = [name for name, text in routines.items()
                  if f'{generation} := {generation} + 1;' in text and name != callers[0]]
        self.assertEqual(opened, [f'FRK_{APP.name}_ScanCanonicalBegin'])


if __name__ == '__main__':
    unittest.main()
