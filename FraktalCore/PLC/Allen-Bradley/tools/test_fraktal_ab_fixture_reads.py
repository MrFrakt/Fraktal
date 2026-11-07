"""C4b apparatus views: unchanged predicates and sealed native press values.

The C4 fixture is synthesized from each paired native legacy state. Counter
metadata is a replay seam, not new native proof. C4a separately pins its writer
and C2/C3 pin the storage moves. Live workload proof remains S6-Q.
"""
import ast
from copy import deepcopy
from dataclasses import replace
import gzip
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_live as live
import fraktal_ab_canonical_reader as reader
import fraktal_ab_fixture_reads as views
import fraktal_ab_fixture_observation as observation
import fraktal_ab_press_s6_collapse_echo38 as profile
import fraktal_ab_press_execute as px
import fraktal_ab_press_canonical_execute as press
from test_fraktal_ab_canonical_live import Clock, Replay

# The old accepted capture has no ConfigAudit bytes. Its new writer is tested
# separately; native audit/capture acceptance remains S6-Q, never synthesized.
APP = replace(profile.application(), fixture_observation=tuple(
    (surface, names) for surface, names in profile.FIXTURE if surface != 'ConfigAudit'))
ROOT = Path(__file__).resolve().parents[4]
SESSION = ROOT/'Specification/AllenBradley/Evidence/AB_PRESS_S3_EXIT_RUNTIME_2026-10-25/Session'


def pairs():
    result = []
    for path in sorted(SESSION.glob('*.json.gz')):
        if not (path.name.startswith('request_cases_') or path.name == 'idle_equivalence.json.gz'):
            continue
        data = reader.load_json(path)
        pair = data.get('pair')
        if isinstance(pair, dict) and 'legacyInputs' in pair:
            if not pair['sameStateVerified'] or not data['comparison']['equal']:
                raise ValueError('native reference pair is not accepted')
            result.append((path.name, pair))
    if len(result) != 86:
        raise ValueError('sealed native press pair set changed')
    return result


def legacy_surface(pair, name):
    inputs = pair['legacyInputs']
    if name == 'Unit':
        return inputs['unit']
    if name == 'Chart':
        return inputs['additional']['chart']
    if name == 'Mailbox':
        return inputs['additional']['mailbox_response']
    if name.startswith('Cfg') and name[3:].isdigit():
        return inputs['additional']['records'][APP.records[int(name[3:])].name]
    if name == 'SetState':
        return inputs['additional']['sets']
    if name == 'Persist':
        return inputs['additional']['persist']
    if name == 'Profiler':
        return inputs['additional']['profiler']
    policy = dict(AccessState='accessState', AccessAudit='accessAudit', AlarmActive='alarmActive',
                  AlarmRing='alarmRing', ReleaseStart='release_report')
    if name in policy:
        return inputs['additional'][policy[name]]
    return inputs['contexts'][name]


def from_pair(pair):
    capture = deepcopy(pair['capture'])
    # V6.6 native values with the later scan-binding protocol overlaid solely
    # for replay. This does not claim the old controller published that table.
    capture['manifest']['schemaMinor'] = 7
    generation = 'FRK_Press_CanonicalGeneration'
    prefixes = ['Press', *(p['CanonicalRoot'] for p in capture['manifest']['dataProducts'])]
    capture['manifest']['readCoherenceBindings'] = [dict(CanonicalPrefix=p, RevisionSymbol=generation,
        Protocol=1, MutationPeriodUs=10000) for p in prefixes]
    if generation not in {s['name'] for s in capture['symbols']}:
        capture['symbols'].append(dict(name=generation, atomic=0xc4, arrayRank=0))
    handle = max(set(range(1, 4096)) - {t['handle'] for t in capture['templates']})
    fields, words, offset = [], [], 0
    for surface, member, name, unused in observation.facts(APP):
        count = member.dimension
        fields.append(dict(name=name, info=count, code=0x20c4 if count else 0xc4,
                           offset=offset, atomic=0xc4, struct=False, handle=0xc4,
                           array=int(bool(count)), typeName='DINT'))
        value = legacy_surface(pair, surface)[member.name]
        if count:
            if len(value) != count:
                raise ValueError('fixture array extent differs from the native reference')
            words.extend(value)
        else:
            words.append(value)
        offset += (count or 1) * 4
    capture['templates'].append(dict(handle=handle, name=observation.type_name(APP),
                                     byteSize=offset, members=fields))
    capture['symbols'].append(dict(name=observation.tag(APP), handle=handle, arrayRank=0))
    fixture = struct.pack(f'<{len(words)}i', *words)
    replay, clock = Replay(capture), Clock()
    counters = []
    def counter(unused):
        counters.append(1)
        return 0 if len(counters) % 3 == 1 else 2
    def raw(location):
        return fixture[location.offset:location.offset+location.width] if location.source == observation.tag(APP) else replay.raw(location)
    row_reader = live.CanonicalRowReader(capture, live.LeafBody(raw), counter,
                                        clock_ns=clock, sleep=clock.sleep)
    return views.FixtureReads(APP, row_reader)


def predicates():
    """Read-site provenance for the 15-row press walk and its wait predicates."""
    tree = ast.parse(Path(px.__file__).read_text(encoding='utf-8'))
    run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    surfaces = {}
    for node in ast.walk(run):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Name):
            continue
        kind = call.func.id
        if kind not in ('read_unit', 'read_chart', 'read_module', 'await_unit', 'await_chart', 'await_module'):
            continue
        surface = 'Unit' if kind.endswith('unit') else 'Chart' if kind.endswith('chart') else call.args[1].value
        target = node.targets[0]
        if isinstance(target, ast.Tuple):
            target = target.elts[0]
        surfaces[target.id] = surface
    checks = []
    for node in ast.walk(run):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == 'row':
                checks.append((node.args[0].value, node.args[-1], None, None))
            elif node.func.id in ('await_unit', 'await_chart', 'await_module'):
                index = 2 if node.func.id == 'await_module' else 1
                if isinstance(node.args[index], ast.Lambda):
                    lam = node.args[index]
                    surface = ('Unit' if node.func.id == 'await_unit' else 'Chart'
                               if node.func.id == 'await_chart' else node.args[1].value)
                    checks.append((f'wait:{node.lineno}', lam.body, lam.args.args[0].arg, surface))
    return run, surfaces, checks


class NativeViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = pairs()

    def test_every_accounted_fact_and_exact_alias_matches_all_native_pairs(self):
        for label, pair in self.pairs:
            session = from_pair(pair)
            for surface, names in APP.fixture_observation:
                with self.subTest(capture=label, surface=surface):
                    actual, expected = session.surface(surface), legacy_surface(pair, surface)
                    for name in names:
                        self.assertEqual(actual[name], expected[name])
                    public = views.public_aliases(surface)
                    for name in public:
                        self.assertEqual(actual[name], expected[name])

    def test_policy_public_text_and_annunciation_equal_the_native_projection(self):
        import fraktal_ab_access as access
        import fraktal_ab_manifest as manifest
        frozen = profile.previous.application()
        rows = manifest.content(frozen)
        checked = 0
        for label, pair in self.pairs:
            session = from_pair(pair)
            extra = pair['legacyInputs']['additional']
            expected = access.audit_status(frozen, rows, extra['accessAudit'], extra['alarmRing'])
            for path, value in expected.items():
                if not path.endswith('/Description'):
                    continue
                full = APP.name + '/' + path
                self.assertEqual(session.reader.read_row((full,))['values'][full], value, (label, path))
                checked += 1
            for slot, value in enumerate(extra['alarmActive']['ActShelved'], 1):
                full = f'{APP.name}/AlarmLog/Active[{slot}]/Shelved'
                self.assertEqual(session.reader.read_row((full,))['values'][full], bool(value), (label, slot))
        self.assertGreater(checked, 0)

    def test_canonical_press_record_is_identical_on_native_before_after_states(self):
        for (label, before), (unused, after) in zip(self.pairs, self.pairs[1:]):
            old, new = object.__new__(press.PressRun), object.__new__(press.PressRun)
            old.rows, new.rows = [], []
            old.unit = lambda after=after: legacy_surface(after, 'Unit')
            current = from_pair(after).surface('Unit')
            new.unit = lambda current=current: current
            a = old.record('ST', label, None, legacy_surface(before, 'Unit'))
            b = new.record('ST', label, None, from_pair(before).surface('Unit'))
            self.assertEqual(a, b)

    def test_all_press_row_and_wait_predicates_keep_their_native_verdicts(self):
        unused, surfaces, checks = predicates()
        self.assertEqual(sum(not label.startswith('wait:') for label, *_ in checks), 15)
        checked = 0
        for index, (capture, pair) in enumerate(self.pairs):
            previous = self.pairs[max(0, index-1)][1]
            sessions = {False: from_pair(pair), True: from_pair(previous)}
            for accepted in (False, True):
                old, new = {}, {}
                for name, surface in surfaces.items():
                    earlier = name == 'base' or name.startswith('before_')
                    old[name] = legacy_surface(previous if earlier else pair, surface)
                    new[name] = sessions[earlier].surface(surface)
                for env in (old, new):
                    env['answer'] = dict(accepted=accepted)
                    env['slide_index'] = [m.name for m in APP.modules].index('PartSlide') + 1
                    env['index_of'] = lambda number: px.gen.ordered_steps(APP).index(number)
                    chart = env['chart_final']
                    env.update(visited=sum(bool(v) for v in chart['Visited']),
                               durations=sum(v > 0 for v in chart['LastMs']),
                               order_fail=env['blocked']['OrderFail'])
                for label, expression, argument, surface in checks:
                    a, b = dict(old), dict(new)
                    if argument:
                        a[argument], b[argument] = legacy_surface(pair, surface), sessions[False].surface(surface)
                    code = compile(ast.Expression(expression), str(Path(px.__file__)), 'eval')
                    with self.subTest(capture=capture, predicate=label, accepted=accepted):
                        self.assertEqual(bool(eval(code, vars(px), a)), bool(eval(code, vars(px), b)))
                    checked += 1
        self.assertGreater(checked, 5000)

    def test_press_walk_and_canonical_case_predicates_are_unchanged_from_c3(self):
        baseline = json.loads((Path(__file__).parent / 'fixtures/press_predicates_c3.json').read_bytes())
        self.assertEqual(baseline['commit'], '8e74160c6')
        for module, names in ((px, {'run'}), (press, {'record','happy','nok','held','adopted_fault'})):
            before = '\n\n'.join(baseline['modules'][Path(module.__file__).name]['functions'].values())
            a, b = ast.parse(before), ast.parse(Path(module.__file__).read_text(encoding='utf-8'))
            def selected(tree):
                return {n.name: ast.dump(n, include_attributes=False) for n in ast.walk(tree)
                        if isinstance(n,ast.FunctionDef) and n.name in names}
            self.assertEqual(selected(a), selected(b))


class Boundaries(unittest.TestCase):
    def test_missing_serial_or_fixture_refuses_before_state_reads(self):
        class Comm:
            def Read(self, tag):
                raise AssertionError('unexpected unguarded state read')
        with self.assertRaises(ValueError):
            views.bind(Comm(), APP, None)
        with patch.object(views, 'open_row_reader', return_value=None):
            with self.assertRaises(ValueError):
                views.bind(Comm(), APP, '601FC87B')

    def test_missing_asserted_fact_is_not_defaulted(self):
        class Reader:
            def read_row(self, paths, private):
                return dict(values={p:0 for p in paths}, private={next(iter(private)):{}})
        subject = views.FixtureReads(APP, Reader())
        with self.assertRaises(KeyError):
            subject.surface('Unit')


if __name__ == '__main__':
    unittest.main()
