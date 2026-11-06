"""WP6.6 C1 (R3): each type AOI publishes its own canonical leaf.

The proof is behavioural. Each library type's legacy body and its collapsed
body run side by side, scan by scan, under the same seeded random inputs.
After every scan the collapsed leaf must hold exactly what the copy layer
would have published from the legacy context, and every context member both
keep must agree. The emitted image is checked too: the collapsed AOIs take
their leaf, the publication no longer copies, and the legacy branch every
other declaration uses is byte for byte what it was.
"""

import dataclasses
import hashlib
import random
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_collapse as collapse
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s6_collapse_demo as collapsed_demo
import fraktal_ab_genealogy_s6_host_demo as host_demo
import fraktal_ab_library as library
import fraktal_ab_owner_read_bindings as owner
import fraktal_ab_press_canonical_echo38 as press_candidate
import fraktal_ab_press_s6_collapse_echo38 as collapsed_press
import fraktal_ab_st_model as st
from test_fraktal_ab_generate import SEED_38

APP = collapsed_demo.application()
SCANS, SEEDS = 400, (1, 2, 3)
COLUMNS = (('TimCount', 'Count'), ('TimLast', 'Last'), ('TimMin', 'Minimum'), ('TimMax', 'Maximum'),
           ('TimAvg', 'Avg'))
# The legacy branch as WP6.6 C0b (b10934f18) emitted it into SEED_38.
LEGACY_PINS = {
    'fraktal_ab_genealogy_s6_host_demo': 'C3720C153F19C17893A6E27B0429E9A779370E9FECB8B3D7E2D8A52682A168F5',
    'fraktal_ab_press_canonical_echo38': '5DCAF972DD52CB04B3CF14BD345837329E40408CD1E01326BDDEB4B74EF906C2',
}


def generate(app):
    with tempfile.TemporaryDirectory() as folder:
        seed, out = Path(folder) / 'seed.L5X', Path(folder) / 'out.L5X'
        seed.write_text(SEED_38, encoding='utf-8')
        gen.generate(app, seed, out)
        return out.read_bytes()


def inputs(mtype):
    """The context members the type body only reads: what the world writes."""
    text = '\n'.join(gen.type_logic(mtype))
    written = set(re.findall(r'Ctx\.(\w+)(?:\[[^\]]*\])?\s*:=', text))
    return [m for m in gen.module_context_members(mtype, True)
            if m.name not in written and not m.name.startswith('Par_') and m.name != 'SchemaVersion'
            and not m.dimension]


def leaf():
    rows = [dict(Count=0, Last=0, Minimum=0, Maximum=0, Avg=0) for _ in range(gen.CMD_STATS)]
    return dict(Status=dict(State=0, FaultActive=False), Timing=dict(Rows=rows))


class Parity(unittest.TestCase):
    """The collapsed body publishes what the copy layer published, every scan."""

    def run_type(self, mtype, seed):
        legacy_code = st.parse('\n'.join(gen.type_logic(mtype)))
        collapsed_code = st.parse('\n'.join(gen.type_aoi_logic(mtype, APP)))
        old = st.structure(gen.module_context_members(mtype))
        new = st.structure(gen.module_context_members(mtype, True))
        for ctx in (old, new):
            if 'Par_TaskPeriodMs' in ctx:
                ctx['Par_TaskPeriodMs'] = APP.task_period_ms
        published = leaf()
        tags = {'Ctx': new, 'Leaf': published, 'Scan': 0, 'ExecState': 0, 'S:FS': True, 'Revision': 0}
        rows = collapse.catalogued_rows(APP, mtype) if 'TimSlot' in old else 0
        rng, members, seen = random.Random(seed), inputs(mtype), set()
        for scan in range(1, SCANS + 1):
            for member in members:
                if rng.random() < 0.08:
                    value = rng.choice((0, 1)) if member.kind == 'boolean' else rng.choice((0, 1, 2, 3))
                    old[member.name] = new[member.name] = value
            st.Controller({'Ctx': old, 'Scan': scan}).run(legacy_code)
            tags['Scan'], tags['S:FS'] = scan, scan == 1
            st.Controller(tags).run(collapsed_code)
            if tags['Revision'] % 2:
                tags['Revision'] += 1  # the publication closes it once per scan
            with self.subTest(type=mtype.type_key, seed=seed, scan=scan):
                self.assertEqual(published['Status']['State'], old['OutImm_ExecState'])
                self.assertEqual(bool(published['Status']['FaultActive']), old['Error'] != 0)
                self.assertEqual({k: v for k, v in old.items() if k in new}, new)
                for r in range(rows):
                    self.assertEqual(tuple(published['Timing']['Rows'][r][c] for _, c in COLUMNS),
                                     tuple(old[s][r] for s, _ in COLUMNS))
            seen.add(old['OutImm_ExecState'])
        return seen, published

    def test_every_type_publishes_what_the_copy_layer_published(self):
        for mtype in library.types_used(APP):
            states, timed = set(), 0
            for seed in SEEDS:
                seen, published = self.run_type(mtype, seed)
                states |= seen
                timed += sum(row['Count'] for row in published['Timing']['Rows'])
            with self.subTest(type=mtype.type_key):
                # Not vacuous: the scenario reaches READY and a terminal state at least.
                self.assertGreaterEqual(len(states), 2, states)
                if 'TimSlot' in {m.name for m in gen.module_context_members(mtype)}:
                    self.assertGreater(timed, 0, 'no command was ever timed')

    def test_the_revision_opens_on_the_first_scan_and_on_each_change_only(self):
        mtype = library.CYLINDER
        code = st.parse('\n'.join(gen.type_aoi_logic(mtype, APP)))
        ctx = st.structure(gen.module_context_members(mtype, True))
        ctx['Par_TaskPeriodMs'] = APP.task_period_ms
        tags = {'Ctx': ctx, 'Leaf': leaf(), 'Scan': 1, 'ExecState': 0, 'S:FS': True, 'Revision': 0}
        st.Controller(tags).run(code)
        self.assertEqual(tags['Revision'], 1, 'opened on the first scan, as the publication did')
        tags['Revision'] += 1
        for scan in range(2, 6):
            tags.update(Scan=scan, **{'S:FS': False})
            st.Controller(tags).run(code)
        self.assertEqual(tags['Revision'], 2, 'nothing changed, nothing opened')
        ctx.update(ParCmd_Command=1, ParCmd_Target=0, Execute=1)
        tags['Scan'] = 6
        st.Controller(tags).run(code)
        self.assertNotEqual(tags['Leaf']['Status']['State'], gen.STATE_READY, 'the command changed the state')
        self.assertEqual(tags['Revision'], 3, 'opened once for the change')


class Declaration(unittest.TestCase):
    def test_only_the_s3k_publication_collapses(self):
        self.assertEqual(decl.validate(APP), [])
        early = dataclasses.replace(APP, canonical_publication_stage=12)
        self.assertTrue(any('canonical_collapse' in f for f in collapse.validate(early)))

    def test_the_collapsed_context_drops_exactly_the_published_facts(self):
        for mtype in library.types_used(APP):
            full = {m.name for m in gen.module_context_members(mtype)}
            kept = {m.name for m in gen.module_context_members(mtype, True)}
            self.assertEqual(full - kept, set(collapse.R3_REMOVED) & full)
            self.assertNotEqual(gen.module_context_name(mtype, True), gen.module_context_name(mtype))


class Image(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.fromstring(generate(APP))

    def lines(self, routine):
        return [l.text or '' for r in self.root.iter('Routine') if r.get('Name') == routine for l in r.iter('Line')]

    def test_each_collapsed_aoi_takes_its_leaf_and_header_revision(self):
        aois = {a.get('Name'): a for a in self.root.iter('AddOnInstructionDefinition')}
        for mtype in library.types_used(APP):
            name = gen.module_aoi_name(APP, next(m for m in APP.modules if library.type_of(m) == mtype))
            params = {p.get('Name'): p.get('DataType') for p in aois[name].iter('Parameter')}
            self.assertEqual(params['Leaf'], collapse.leaf_type(APP, mtype))
            self.assertEqual(params['Revision'], 'DINT')
            self.assertEqual(params['Ctx'], gen.module_context_name(mtype, True))
        # The emitted call is formatted; compare it without whitespace.
        calls = re.sub(r'\s+', '', ''.join(self.lines(f'FRK_{APP.name}_ScanModules')))
        for module in APP.modules:
            self.assertIn(f'{gen.ctx_tag_for(APP, module.name)},{APP.name}.{module.name},'
                          f'{owner.header_revision(APP, APP.modules.index(module) + 1)},', calls)

    def test_the_publication_no_longer_copies_module_state_or_timing(self):
        body = '\n'.join(self.lines(f'FRK_{APP.name}_ScanCanonical'))
        self.assertNotIn('OutImm_ExecState', body)
        self.assertNotIn('.TimCount', body)
        self.assertIsNone(re.search(r'Press\.\w+\.Status\.FaultActive :=', body))

    def test_no_routine_reads_a_module_leaf_before_its_aoi_wrote_it(self):
        """Publishing at the AOI rather than at the end of the scan is invisible
        only if nothing else in the scan reads those leaf members."""
        names = '|'.join(m.name for m in APP.modules)
        pattern = re.compile(rf'{APP.name}\.({names})\.(Status\.(State|FaultActive)|Timing)')
        found = [t.text for t in self.root.iter() if t.tag in ('Line', 'Text') and t.text and pattern.search(t.text)]
        self.assertEqual(found, [])


class LegacyBranch(unittest.TestCase):
    """Until WP6.7 every other declaration emits exactly what it did."""

    def test_the_pre_collapse_images_are_unchanged(self):
        for module in (host_demo, press_candidate):
            with self.subTest(module.__name__):
                digest = hashlib.sha256(generate(module.application())).hexdigest().upper()
                self.assertEqual(digest, LEGACY_PINS[module.__name__])

    def test_the_press_collapses_the_same_way(self):
        self.assertEqual(decl.validate(collapsed_press.application()), [])


if __name__ == '__main__':
    unittest.main()
