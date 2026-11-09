"""S3 exit walk for the press declaration on Echo; separate current approval required.

The press declares no Part carrier, host-event ring, nameplate or signal tower, so
its machine core is the Part fixture's six cases proven by the Unit's own counters
and state, in all three AUTO renditions. The S3a-S3k capture layers, configuration
and set-store vectors and the typed request vectors run unchanged on top. Every
changed value is restored by the shared owner; credentials are never recorded.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time

import fraktal_ab_fixture_reads as views
import fraktal_ab_genealogy_execute as live
import fraktal_ab_harness_documents as host_docs
import fraktal_ab_harness_seed as harness_seed
from fraktal_ab_live_medium import FileMedium
import fraktal_ab_mailbox as mb
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_canonical_echo38 as candidate
import fraktal_ab_press_execute as px
import fraktal_ab_set_documents as set_docs
import fraktal_ab_station as station
import fraktal_ab_tower_execute as tower

SERIAL = '601FC87B'
DECLARATION = 'fraktal_ab_press_canonical_echo38'
COLLAPSED_DECLARATIONS = ('fraktal_ab_press_s6_collapse_echo38', 'fraktal_ab_press_s6_shelving_echo38')
ACCEPTED_DECLARATIONS = (DECLARATION, *COLLAPSED_DECLARATIONS)
ISOLATED_SEED_ENV = 'FRAKTAL_AB_PRESS_SEED_DIR'
COUNTERS = ('GoodCount', 'ScrapCount', 'ReworkCount', 'CycleCount')
STATE = ('Mode', 'Running', 'Complete', 'Error', 'ErrorID', 'Aborted')


def authorize(path, pin):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if (not re.fullmatch(r'[A-F0-9]{64}', pin)
            or value.get('CurrentOwnerApproved') is not True
            or value.get('MailboxOrTagWritesAuthorized') is not True
            or value.get('Serial') != SERIAL
            or value.get('CanonicalSha256') != pin
            or value.get('FaultClearAuthorized') is not False
            or value.get('ClockSetAuthorized') is not False):
        raise fixture.FixtureRefused('current exact-image press authorization required')
    return value


class PressRun(fixture.Run):
    """The machine core without Part or host-event owners: counters and Unit state decide."""

    def boundary(self):
        return None, self.unit()

    def record(self, language, case, before, counters, **extra):
        u = self.unit()
        row = dict(language=language, case=case, passed=False,
                   counters={n: u[n]-counters[n] for n in COUNTERS}, unit={k: u[k] for k in STATE}, **extra)
        self.rows.append(row)
        return row

    def happy(self, language, case='OK'):
        self.home()
        unused, baseline = self.boundary()
        self.begin()
        self.complete(baseline)
        row = self.record(language, case, None, baseline)
        self.check(row['counters']['GoodCount'] == 1 and row['counters']['ScrapCount'] == 0
                   and row['counters']['CycleCount'] == 1, 'OK verdict count')
        return row

    def nok(self, language):
        self.home()
        unused, baseline = self.boundary()
        self.set(px.FAULT['PressRam'], 1)
        self.begin()
        self.wait(lambda: self.unit()['DecisionId'] != 0, 'handled ram fault decision')
        self.command(mb.DECISION_ANSWER, IntValue=1)
        self.set(px.FAULT['PressRam'], 0)
        self.complete(baseline)
        row = self.record(language, 'handled_NOK', None, baseline)
        self.check(row['counters']['GoodCount'] == 0 and row['counters']['ScrapCount'] == 1, 'NOK must not count good')

    def held(self, language, ending='resume'):
        self.home()
        unused, baseline = self.boundary()
        self.set(px.HOLD['PressRam'], 1)
        self.begin()
        self.wait(lambda: (px.module_surface(self.comm, 'PressRam') or {}).get('OutImm_Held'), 'recoverable hold')
        if ending == 'resume':
            time.sleep(.75)  # exceeds the cylinder command's 500 ms timeout
            self.check(self.unit()['Error'] == 0 and self.unit()['Running'] == 1, 'held timeout must not accrue')
            self.set(px.HOLD['PressRam'], 0)
            self.complete(baseline)
            row = self.record(language, 'HELD_resume', None, baseline)
            self.check(row['counters']['GoodCount'] == 1, 'HELD resumes and counts once')
        else:
            self.command(mb.STOP if ending == 'abort' else mb.SET_MODE,
                         **({} if ending == 'abort' else dict(IntValue=self.app.manual_mode)))
            if ending == 'abort':
                self.wait(lambda: not self.unit()['Running'], 'held abort')
            else:
                # A mode change stands the chain down (Step 0); Running follows the
                # run level, which only STOP lowers, so it is not the observable.
                self.wait(lambda: self.unit()['Mode'] == self.app.manual_mode and self.unit()['Step'] == 0,
                          'held mode change')
            self.set(px.HOLD['PressRam'], 0)
            row = self.record(language, 'abort' if ending == 'abort' else 'mode_change', None, baseline)
            self.check(row['counters']['GoodCount'] == row['counters']['ScrapCount'] == 0, 'aborted cycle must not count')
            if ending != 'abort':
                self.check(row['unit']['Mode'] == self.app.manual_mode, 'mode change must leave AUTO')

    def adopted_fault(self, language):
        self.home()
        unused, baseline = self.boundary()
        self.set(px.FAULT['PartSlide'], 1)
        self.begin()
        failed = self.wait(lambda: self.unit() if self.unit()['Error'] else None, 'adopted slide fault')
        row = self.record(language, 'adopted_fault', None, baseline, firstOut=failed['ErrorID'])
        self.check(failed['ErrorID'] != 0 and row['counters']['GoodCount'] == 0, 'adopted fault keeps its first-out')
        self.set(px.FAULT['PartSlide'], 0)
        self.command(mb.OPERATOR_RESET)
        self.wait(lambda: self.unit()['Error'] == self.unit()['Aborted'] == self.unit()['Running'] == 0, 'one-reset readiness')
        unused, fresh = self.boundary()
        self.begin()
        self.complete(fresh)
        resumed = self.record(language, 'single_reset_restart', None, fresh)
        self.check(resumed['counters']['GoodCount'] == 1, 'single-reset restart must process normally')


def seed_medium(run):
    """First commissioning of the press on this host: its own documents, from its image.

    The host medium is keyed by serial and root name, which the genealogy bench
    shares; its documents carry the genealogy revision and the press rightly
    refuses them. The walk therefore uses an isolated, initially empty medium
    seeded with what the downloaded press image holds, at the press revision.
    """
    if run.app.canonical_collapse:
        selected = os.environ.get(ISOLATED_SEED_ENV)
        run.check(bool(selected), 'isolated press medium not selected')
        run.check(not os.environ.get('FRAKTAL_HARNESS_HOST_SEED')
                  and not os.environ.get('FRAKTAL_HARNESS_HOST_SEED_SHA256'),
                  'isolated press medium must start empty')
        directory = Path(selected).resolve()
        manifest_path = directory.with_name(directory.name + '_seed.json')
        live_dir = directory / 'live'
        store = FileMedium(live_dir)
        run.check(not manifest_path.exists() and not store.index(), 'isolated press medium must start empty')
        session = views._session(run.comm, run.app)
        expected, epoch = host_docs.expected_documents(session.reader, session.root)
        run.check(views.revision(run.comm, app=run.app) == epoch, 'configuration changed while seeding press medium')
        run.check(all(store.read(key) is None for key in expected), 'isolated press medium must start empty')
        live_dir.mkdir(parents=True, exist_ok=True)
        for key, wanted in expected.items():
            document = set_docs.checked_document([
                {**wanted['header'], 'schema': 1, 'created': 0, 'clock': 0},
                *wanted['records'].values(),
            ])
            store.write(key, document)
        recorded = harness_seed.record(directory, manifest_path,
                                       serial=run.evidence['serial'], root=run.app.name)
        digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper()
        os.environ['FRAKTAL_HARNESS_HOST_SEED'] = str(manifest_path)
        os.environ['FRAKTAL_HARNESS_HOST_SEED_SHA256'] = digest
        run.evidence['pressMedium'] = dict(
            directory=str(live_dir),
            seedManifest=str(manifest_path),
            seedManifestSha256=digest,
            seeded=sorted(expected),
            files=len(recorded['files']),
            source='published configuration view of the downloaded press image',
        )
        return
    raise ValueError('canonical collapsed profile required')


def press_rows(run):
    """Commission the press medium, then the declaration-neutral rows; no tower rows."""
    seed_medium(run)
    tower.exercise_common(run)


def isolate_medium(output, *, canonical_collapse=None):
    if canonical_collapse is None:
        canonical_collapse = station.module_name() in COLLAPSED_DECLARATIONS
    if not canonical_collapse:
        raise ValueError('canonical collapsed profile required')
    directory = output.with_name(output.stem + '_press_medium')
    manifest_path = directory.with_name(directory.name + '_seed.json')
    if os.environ.get('FRAKTAL_HARNESS_HOST_SEED') or os.environ.get('FRAKTAL_HARNESS_HOST_SEED_SHA256'):
        raise fixture.FixtureRefused('host seed environment already set')
    if directory.exists() or manifest_path.exists():
        raise fixture.FixtureRefused('isolated press medium already exists')
    directory.mkdir()
    (directory / 'live').mkdir()
    os.environ[ISOLATED_SEED_ENV] = str(directory)
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--authorization-file', type=Path, required=True)
    parser.add_argument('--expect-acd-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    known, rest = parser.parse_known_args(argv)
    collapsed = station.module_name() in COLLAPSED_DECLARATIONS
    if not collapsed:
        raise fixture.FixtureRefused('canonical collapsed declaration required')
    authorize(known.authorization_file, known.expect_acd_sha256)
    if known.output.exists():
        raise fixture.FixtureRefused('refusing existing evidence output')
    isolate_medium(known.output, canonical_collapse=True)
    try:
        return live.main([*rest, '--output', str(known.output)],
                         run_type_factory=lambda _out: PressRun,
                         schema='fraktal.ab.press-collapse-fixture',
                         expected_declaration=COLLAPSED_DECLARATIONS,
                         exercise_rows=press_rows)
    finally:
        for key in (ISOLATED_SEED_ENV, 'FRAKTAL_HARNESS_HOST_SEED', 'FRAKTAL_HARNESS_HOST_SEED_SHA256'):
            os.environ.pop(key, None)


if __name__ == '__main__': raise SystemExit(main())
