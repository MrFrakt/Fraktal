"""S3 exit walk for the press declaration on Echo; separate current approval required.

The press declares no Part carrier, host-event ring, nameplate or signal tower, so
its machine core is the Part fixture's six cases proven by the Unit's own counters
and state, in all three AUTO renditions. The S3a-S3k capture layers, configuration
and set-store vectors and the typed request vectors run unchanged on top. Every
changed value is restored by the shared owner; credentials are never recorded.
"""
import argparse
import os
from pathlib import Path
import time

import fraktal_ab_genealogy_execute as live
import fraktal_ab_mailbox as mb
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_canonical_echo38 as candidate
import fraktal_ab_press_execute as px
import fraktal_ab_press_s3k_equivalence as equivalence
import fraktal_ab_s3k_fixture_execute as typed
import fraktal_ab_tower_execute as tower

DECLARATION = 'fraktal_ab_press_canonical_echo38'
COUNTERS = ('GoodCount', 'ScrapCount', 'ReworkCount', 'CycleCount')
STATE = ('Mode', 'Running', 'Complete', 'Error', 'ErrorID', 'Aborted')


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
        self.wait(lambda: (px.read_module(self.comm, 'PressRam') or {}).get('OutImm_Held'), 'recoverable hold')
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
    import fraktal_ab_live as live
    import fraktal_ab_medium as medium
    import fraktal_ab_projection as projection
    run.check(bool(os.environ.get(medium.SET_DIR_ENV)), 'isolated press medium not selected')
    directory = live.live_directory(run.app, run.evidence['serial'])
    store = live.FileMedium(directory)
    held = projection.read_document(run.comm)['liveConfig']
    wanted = live.documents(run.app, held, 0)
    run.check(all(store.read(key) is None for key in wanted), 'isolated press medium must start empty')
    for key, document in wanted.items():
        store.write(key, document)
    run.evidence['pressMedium'] = dict(directory=str(directory), seeded=sorted(wanted),
                                       source='live configuration of the downloaded press image')


def press_rows(run):
    """Commission the press medium, then the declaration-neutral rows; no tower rows."""
    seed_medium(run)
    tower.exercise_common(run)


def isolate_medium(output):
    import fraktal_ab_medium as medium
    directory = output.with_name(output.stem + '_press_medium')
    if directory.exists():
        raise fixture.FixtureRefused('isolated press medium already exists')
    directory.mkdir()
    os.environ[medium.SET_DIR_ENV] = str(directory)
    return directory


def paired_run(destination):
    return typed.paired_run(destination, candidate_factory=candidate.application,
                            equivalence_gate=equivalence.run, base=PressRun)


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--authorization-file', type=Path, required=True)
    parser.add_argument('--expect-acd-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    known, rest = parser.parse_known_args(argv)
    typed.authorize(known.authorization_file, known.expect_acd_sha256)
    if known.output.exists():
        raise fixture.FixtureRefused('refusing existing evidence output')
    isolate_medium(known.output)
    return live.main([*rest, '--output', str(known.output)], run_type_factory=paired_run, schema='fraktal.ab.press-s3k-fixture',
                     expected_declaration=DECLARATION, exercise_rows=press_rows)


if __name__ == '__main__': raise SystemExit(main())
