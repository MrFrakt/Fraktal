"""Readable emitted ST must retain its executable tokens and call boundaries."""
import unittest

import fraktal_ab_config as config
import fraktal_ab_generate as gen
import fraktal_ab_line as line
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as press
import fraktal_ab_sets as sets
import fraktal_ab_station_template as template
from fraktal_ab_st_format import FormatError, format_lines, tokens
from fraktal_ab_st_model import parse
from test_fraktal_ab_generate import emit


def source(node):
    return '\n'.join(n.text or '' for n in node.findall('./Line'))


def expand_tokens(text, helpers, stack=()):
    """Inline only explicitly extracted, zero-argument program services.

    Keep every pre-existing JSR intact: this proves the relocation rather
    than assuming that arbitrary subroutines are interchangeable.
    """
    items, output, index = tokens(text), [], 0
    while index < len(items):
        call = items[index:index + 7]
        if (len(call) == 7 and call[0] == ('name', 'JSR')
                and call[2][1] in helpers):
            name = call[2][1]
            if call != tokens(f'JSR({name},0);') or name in stack:
                raise ValueError(f'non-inlineable service call: {name}')
            output.extend(expand_tokens(helpers[name], helpers, (*stack, name)))
            index += 7
        else:
            output.append(items[index])
            index += 1
    return output


class Layout(unittest.TestCase):
    def test_nested_blocks_labels_and_inline_statements(self):
        text = '''CASE (Kind) OF
        -1, 2..4: IF Ready<>0 THEN FOR Idx:=0 TO 2 DO Data[Idx].Value:=-1; END_FOR; ELSE Value:=0; END_IF;
        5: Value:=Data[Offset-1].Value+1;
        ELSE Value:=0;
        END_CASE;'''
        expected = '''CASE (Kind) OF
    -1, 2 .. 4:
        IF Ready <> 0 THEN
            FOR Idx := 0 TO 2 DO
                Data[Idx].Value := -1;
            END_FOR;
        ELSE
            Value := 0;
        END_IF;

    5:
        Value := Data[Offset - 1].Value + 1;
    ELSE
        Value := 0;
END_CASE;'''
        self.assertEqual('\n'.join(format_lines(text)), expected)
        self.assertEqual(parse(text), parse(expected))

    def test_literals_comments_and_line_wrapping_do_not_change_tokens(self):
        text = """(* Instruction names in comments are inert: IF THEN END_IF *)
        IF (* condition explanation *) Ready<>0 AND NextReady<>0 OR LastReady<>0 THEN
        COP(Source[Offset-1],Target[Offset],5); Text:='x;$\' IF THEN'; Hex:=16#00_FF;
        (* Wrapped explanation
             continues here

             closes here *)
        END_IF;"""
        formatted = format_lines(text, width=50)
        self.assertEqual(tokens(text), tokens('\n'.join(formatted)))
        self.assertIn("    Text := 'x;$\' IF THEN';", formatted)
        self.assertIn('    Hex := 16#00_FF;', formatted)
        self.assertIn('    COP(Source[Offset - 1], Target[Offset], 5);', formatted)
        self.assertEqual(format_lines(formatted, width=50), formatted)
        self.assertTrue(all(not s.endswith(' ') for s in formatted))
        self.assertGreater(len(formatted), 10)

    def test_sfc_condition_and_empty_arguments(self):
        for text in ('Ready<>0 AND (Result=1 OR Result=2)',
                     'GSV(WallClockTime,,CurrentValue,Clock[0]);',
                     'IF X=1 THEN Y:=1; ELSIF X=2 THEN Y:=2; ELSE Y:=-1; END_IF;'):
            formatted = format_lines(text, width=25)
            self.assertEqual(tokens(text), tokens('\n'.join(formatted)))
            self.assertEqual(format_lines(formatted, width=25), formatted)

    def test_bad_structure_is_refused(self):
        for text in ('END_IF;', 'IF X<>0 THEN X:=1;', 'ELSE X:=0;',
                     'FOR Idx:=0 TO 2 DO END_IF;', 'CASE X OF 1: X:=2;',
                     'X:=Y[(2];', 'X:=Y@;'):
            with self.subTest(text=text), self.assertRaises(FormatError):
                format_lines(text)


class EmittedServices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projects = []
        for app in (press.application(), template.application()):
            root, _, evidence = emit(app)
            cls.projects.append((app, root, evidence))

    def test_emission_census_counts_types_and_native_routines(self):
        for app, root, evidence in self.projects:
            for key, path in (
                    ('AoiDefinitions', './Controller/AddOnInstructionDefinitions/AddOnInstructionDefinition'),
                    ('Programs', './Controller/Programs/Program'),
                    ('Routines', './Controller/Programs/Program/Routines/Routine'),
                    ('Tasks', './Controller/Tasks/Task')):
                self.assertEqual(evidence[key], len(root.findall(path)), (app.name, key))

    def test_every_runtime_st_surface_uses_one_idempotent_layout(self):
        for app, root, _ in self.projects:
            for node in root.findall('.//STContent'):
                with self.subTest(station=app.name, first=source(node)[:80]):
                    lines = tuple(n.text or '' for n in node.findall('./Line'))
                    self.assertEqual(format_lines(lines), lines)
                    self.assertEqual([int(n.get('Number')) for n in node.findall('./Line')],
                                     list(range(len(lines))))
                    self.assertFalse(any('\t' in n or n.endswith(' ') for n in lines))

    def test_services_expand_to_the_original_inline_scan_and_mailbox(self):
        for app, root, _ in self.projects:
            program = root.find('./Controller/Programs/Program')
            routines = {r.get('Name'): source(r.find('STContent'))
                        for r in program.findall('./Routines/Routine') if r.get('Type') == 'ST'}
            helper_names = {name for name, _ in gen.scan_sections(app) if name}
            helper_names.add(config.write_routine_name(app))
            if app.config_sets:
                helper_names.add(sets.routine_name(app))
            if app.line is not None:
                helper_names.add(line.routine(app, 'Stage'))
            helpers = {name: routines[name] for name in helper_names}
            for name, inline in ((app.routine, gen.routine_logic(app)),
                                 (mailbox.routine_name(app), mailbox.handler_logic(app))):
                with self.subTest(station=app.name, caller=name):
                    self.assertEqual(expand_tokens(routines[name], helpers),
                                     expand_tokens('\n'.join(inline), helpers))
            # The single shared staging body cannot alter the surrounding
            # candidate transaction or early-return semantics.
            if app.line is not None:
                self.assertEqual(tokens(helpers[line.routine(app, 'Stage')]),
                                 tokens('\n'.join(line.candidate_copy(app))))
            for body in helpers.values():
                parse(body)  # complete executable blocks, not a CASE/header fragment
                self.assertFalse({'RETURN', 'RTN', 'EXIT'} & {v for _, v in tokens(body)})
            for aoi in root.findall('.//AddOnInstructionDefinition'):
                self.assertFalse(any(name in source(n) for name in helper_names
                                     for n in aoi.findall('.//STContent')))
            for name in helper_names:
                self.assertEqual(len(program.findall(f'./Routines/Routine[@Name="{name}"]')), 1)
                self.assertTrue(any(('name', name) in tokens(body)
                                    for other, body in routines.items() if other != name), name)

    def test_nonzero_arguments_and_recursive_extraction_are_rejected(self):
        for call, helpers in (('JSR(Service,1);', {'Service': 'X:=1;'}),
                              ('JSR(Service,0);', {'Service': 'JSR(Service,0);'})):
            with self.assertRaises(ValueError):
                expand_tokens(call, helpers)


if __name__ == '__main__':
    unittest.main()
