"""Table-driven canonical text (capacity plan R2) against the unchanged independent oracles."""
from dataclasses import replace
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_access as access
import fraktal_ab_canonical_config as config
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_text as text
import fraktal_ab_genealogy_s3i_demo as s3i
import fraktal_ab_st_model as st
import test_fraktal_ab_canonical_access as access_suite
import test_fraktal_ab_canonical_config as config_suite


def table_driven(factory):
    return lambda: replace(factory(), canonical_table_driven=True)


class TableDrivenConfigurationTests(config_suite.ConfigurationTests):
    """Every inherited page/revision/durability case, on the table-driven page."""

    def setUp(self):
        with patch.object(config_suite.demo, 'application', table_driven(config_suite.demo.application)):
            super().setUp()
        app = self.app
        self.assertTrue(text.enabled(app))
        self.controller.tags.update(text.model_tags(app))
        self.controller.tags[config.defs_tag(app)] = [self.value(config.DEF, row) for row in config.def_rows(app)]
        self.assertEqual(self.controller.routines[config.page_routine(app)], st.parse('\n'.join(config.table_page_logic(app))))


class TableDrivenAccessTests(access_suite.AccessTests):
    """Every inherited session/policy/audit case, on the table-driven audit."""

    def setUp(self):
        with patch.object(access_suite.demo, 'application', table_driven(access_suite.demo.application)):
            super().setUp()
        app, fixture = self.app, self.fixture
        self.assertTrue(text.enabled(app))
        fixture.controller.tags.update(text.model_tags(app))
        for name, (unused, rows) in access.tables(app).items():
            fixture.controller.tags[name] = [fixture.make_value(text.SLICE, row) for row in rows]
        self.assertEqual(fixture.controller.routines[access.audit_routine(app)],
                         st.parse('\n'.join(access.table_audit_logic(app))))
        self.assertIn(access.append_routine(app), fixture.controller.routines)


class PoolTests(unittest.TestCase):
    def setUp(self):
        self.app = replace(s3i.application(), canonical_table_driven=True)

    def controller(self, render_len=0):
        tags = dict(text.model_tags(self.app), Target=dict(LEN=7, DATA=[9] * 255), Render=dict(LEN=render_len, DATA=[5] * 255),
                    Header=dict(Valid=1))
        routines = {'Append': text.append_routine_lines(self.app, 'Render', 'Header.Valid')}
        return st.Controller(tags, routines=routines)

    def test_every_literal_is_stored_once_and_found_exactly(self):
        pool, where = text.layout(self.app)
        for literal in text.texts(self.app):
            offset, length = where[literal]
            self.assertEqual(pool[offset:offset + length], literal.encode('utf-8'))
        self.assertLess(len(pool), sum(len(t.encode('utf-8')) for t in set(text.texts(self.app))))

    def test_put_replaces_length_and_writes_only_the_text_bytes(self):
        plc = self.controller()
        literal = 'std.audit.loginFailed'
        plc.run('\n'.join(text.put_text(self.app, 'Target', literal, 255)))
        target = plc.tags['Target']
        self.assertEqual(bytes(b & 255 for b in target['DATA'][:target['LEN']]).decode(), literal)
        self.assertEqual(target['DATA'][target['LEN']:], [9] * (255 - target['LEN']))
        plc.run('\n'.join(text.put(self.app, 'Target', 0, 0)))
        self.assertEqual(plc.tags['Target']['LEN'], 0)
        with self.assertRaises(ValueError):text.put_text(self.app, 'Target', literal, 5)

    def test_append_fits_exactly_or_refuses_without_writing(self):
        literal = ' [automatic]'
        size = len(literal)
        for start, fits in ((255 - size, True), (256 - size, False), (0, True)):
            with self.subTest(start=start):
                plc = self.controller(render_len=start)
                plc.run('\n'.join(text.append_text(self.app, 'Append', literal)))
                render = plc.tags['Render']
                if fits:
                    self.assertEqual(render['LEN'], start + size)
                    self.assertEqual(bytes(render['DATA'][start:start + size]).decode(), literal)
                    self.assertEqual(plc.tags['Header']['Valid'], 1)
                else:
                    self.assertEqual((render['LEN'], render['DATA'], plc.tags['Header']['Valid']), (start, [5] * 255, 0))
        self.assertEqual(text.append_text(self.app, 'Append', ''), [])

    def test_keyed_tables_leave_gaps_empty_and_bound_their_range(self):
        base, rows = text.keyed_table(self.app, {3: 'Press', 5: 'Press.Door'})
        self.assertEqual(base, 3)
        self.assertEqual([r['Length'] for r in rows], [5, 0, 10])
        self.assertEqual(text.keyed_table(self.app, {}), (0, []))

    def test_no_array_reference_inside_a_subscript(self):
        # Logix rejects it (RxCMP_E_OPERAND_INVALIDDIMSPEC); the ST model does not.
        def nested(line):
            depth = 0
            for char in line:
                if char == '[':
                    if depth:return True
                    depth += 1
                elif char == ']':depth -= 1
            return False
        lines = [*config.table_page_logic(self.app), *access.table_audit_logic(self.app),
                 *text.append_routine_lines(self.app, 'Render', 'Header.Valid')]
        self.assertEqual([line for line in lines if nested(line)], [])

    def test_disabled_declarations_emit_no_table_text(self):
        app = s3i.application()
        self.assertFalse(text.enabled(app))
        emitted = '\n'.join([*pub.data_types(app), *pub.tags(app)])
        for name in (text.pool_tag(app), text.work_tag(app), config.defs_tag(app), access.key_table_tag(app)):
            self.assertNotIn(name, emitted)
        self.assertEqual(text.validate(replace(app, canonical_table_driven=True, canonical_publication_stage=6)),
                         ['table-driven canonical text requires the S3e access audit'])


if __name__ == '__main__':
    unittest.main()
