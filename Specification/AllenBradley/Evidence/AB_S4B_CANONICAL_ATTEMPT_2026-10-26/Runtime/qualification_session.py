"""One exact-image S4b retry, with genealogy rollback after any download attempt.

No controller access occurs before authorization, immutable gate/source checks
and an append-only single-use record. Stops candidate work at its first failure.
Rollback retains exact-target, fault, idle and active-session guards.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'
PRIOR = Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
SDK = D / 'session/bin/Debug/net8.0/win-x86/S4bSession.exe'
PY = sys.executable
DUMPS = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
CREDENTIAL = 'C:/work/fraktal_echo38_access_fixture.json'
PIN = '7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF'
SOURCE = 'C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F'
FLAGS = ('BackupUploadAuthorized', 'DownloadAuthorized', 'MailboxOrTagWritesAuthorized',
         'ManualNormalizationAuthorized', 'RestoreGenealogyAuthorized', 'BaselineRegressionWritesAuthorized', 'DartReadQualificationAuthorized')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def authorize(value):
    if value.get('CurrentOwnerApproved') is not True or value.get('Serial') != '601FC87B' \
            or value.get('CanonicalSha256') != PIN or value.get('SourceSha256') != SOURCE \
            or not isinstance(value.get('OwnerInstruction'), str) or not value['OwnerInstruction'].strip() \
            or any(value.get(k) is not True for k in FLAGS) \
            or any(value.get(k) is not False for k in ('FaultClearAuthorized', 'ClockSetAuthorized', 'PowerOperationsAuthorized', 'VendorStateEditsAuthorized')):
        raise ValueError('current exact-image approval for the complete qualification/rollback scope required')


def save(name, value):
    with (D / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def dumps():
    return [dict(path=p.relative_to(DUMPS).as_posix(), bytes=p.stat().st_size)
            for p in sorted(DUMPS.rglob('*.dmp'))]


def main():
    approval = json.loads((D / 'authorization.json').read_bytes())
    authorize(approval)
    assert digest(D / 's4b_read_view.ACD') == PIN == (D / 'canonical.sha256').read_text().strip()
    assert digest(D / 's4b_read_view.L5X') == SOURCE
    bindings = json.loads((D / 'source_bindings.json').read_bytes())
    for path, expected in bindings['sha256'].items():
        assert digest(path) == expected.upper(), 'prepared source/gate changed: ' + path
    assert bindings['gatesPassed'] is True
    save('session_started.json', dict(approvalSha256=digest(D / 'authorization.json'),
         canonicalSha256=PIN, sourceSha256=SOURCE, utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    stages, candidate_error, rollback_error = [], None, None
    rollback_ok = False

    def run(label, *args):
        print(json.dumps(dict(stage=label, status='started')), flush=True)
        stages.append(label)
        subprocess.run([PY, str(D / 'run_logged.py'), label, *map(str, args)], cwd=ROOT, check=True)

    def audit(label, *operations):
        arguments = [PY, T / 'fraktal_ab_sdk_log_gate.py', D / (label + '.log')]
        for operation in operations:
            arguments.extend(['--require', operation])
        run(label + '_audit', *arguments)

    try:
        os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
        run('guard_initial', PY, D / 'scripts/guard_echo.py')
        save('dumps_initial.json', dict(readOnly=True, dumpFiles=dumps()))
        if dumps():
            raise RuntimeError('controller dump present; no change permitted')
        run('manual_initial', PY, D / 'ensure_manual_baseline.py', '--output', D / 'manual_initial.json')
        run('preflight_initial', PY, D / 'scripts/preflight.py')
        run('backup', SDK, 'backup')
        audit('backup', 'Save As')
        run('backup_access', PY, PRIOR / 'audit_baseline_access.py', D / 'echo_before_s4b.L5X',
            '--output', D / 'backup_access.json')
        run('deploy', SDK, 'deploy-canonical')
        audit('deploy', 'Open project', 'Download', 'Save', 'Save As')
        run('deploy_readback', PY, T / 'fraktal_ab_readback.py', D / 's4b_read_view.L5X', D / 'canonical_downloaded.L5X')
        run('deploy_access', PY, D / 'audit_access.py', D / 'canonical_downloaded.L5X', D / 'deploy_access.json')
        os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_s4b_demo'
        run('guard_candidate', PY, D / 'scripts/guard_echo.py')
        run('candidate_regressions', PY, D / 'candidate_regressions.py', '--execute-fixture',
            '--expect-serial', '601FC87B', '--credential-file', CREDENTIAL,
            '--output', D / 'candidate_regressions.json')
        run('idle_equivalence', PY, D / 'candidate_equivalence.py', '--expect-serial', '601FC87B',
            '--output', D / 'idle_equivalence.json.gz')
        run('generic_acquire', PY, T / 'fraktal_ab_canonical_acquire.py', '--expect-serial', '601FC87B',
            '--output', D / 'generic_snapshot.json.gz', '--capture-output', D / 'generic_capture.json.gz')
        run('candidate_timing', PY, PRIOR / 'measure_timing.py', D / 'candidate_timing.json', '--candidate')
    except Exception as error:
        candidate_error = f'{type(error).__name__}: {error}'
        print(json.dumps(dict(candidateError=candidate_error)), flush=True)
    finally:
        if (D / 'deploy_attempt.json').exists():
            try:
                if dumps():
                    raise RuntimeError('controller dump present; rollback stopped before any further change')
                os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_s4b_demo'
                run('guard_rollback', PY, D / 'scripts/guard_echo.py')
                run('manual_rollback', PY, D / 'ensure_manual_candidate.py', '--output', D / 'manual_rollback.json')
                run('restore_genealogy', SDK, 'restore-genealogy')
                audit('restore_genealogy', 'Open project', 'Download', 'Save', 'Save As')
                run('restore_access', PY, PRIOR / 'audit_baseline_access.py', D / 'genealogy_restored.L5X',
                    '--output', D / 'restore_access.json')
                os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
                run('guard_baseline', PY, D / 'scripts/guard_echo.py')
                run('restore_original_medium', PY, D / 'restore_original_medium.py')
                run('baseline_regressions', PY, T / 'fraktal_ab_genealogy_execute.py', '--execute-fixture',
                    '--expect-serial', '601FC87B', '--credential-file', CREDENTIAL,
                    '--output', D / 'baseline_regressions.json')
                run('manual_final', PY, D / 'ensure_manual_baseline.py', '--output', D / 'manual_final.json')
                run('final_checks', PY, PRIOR / 'final_checks.py', D / 'final_checks.json')
                run('preflight_final', PY, D / 'scripts/preflight.py', '--verify-only')
                run('baseline_timing', PY, PRIOR / 'measure_timing.py', D / 'baseline_timing.json')
                rollback_ok = True
            except Exception as error:
                rollback_error = f'{type(error).__name__}: {error}'
                print(json.dumps(dict(rollbackError=rollback_error)), flush=True)
        save('session_result.json', dict(passed=candidate_error is None and rollback_ok and not dumps(),
             candidateError=candidate_error, rollbackError=rollback_error, genealogyRestored=rollback_ok,
             authorizationConsumed=True, stagesStarted=stages, dumpFiles=dumps(),
             faultClears=0, clockChanges=0, powerOperations=0, hardKills=0,
             utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return 0 if candidate_error is None and rollback_ok and not dumps() else 1


if __name__ == '__main__':
    raise SystemExit(main())
