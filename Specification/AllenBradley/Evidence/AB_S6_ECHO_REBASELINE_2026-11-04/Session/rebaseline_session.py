"""One guarded re-baseline of the factory-reset Echo 601FC87B onto the genealogy pin.

The plan's §4 rollback sequence, run forward from an empty controller: the
genealogy pin, its access audit, the unchanged host documents, the 31 baseline
cases, MANUAL, a fresh preflight, final checks and timing. No controller access
happens before the armed O3 record and the source bindings verify. Nothing runs
after a failed stage except the read-only final record; there is no candidate,
so there is nothing to roll back to but this baseline itself.
"""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'
SDK = D / 'session/bin/Debug/net8.0/win-x86/RebaselineSession.exe'
PY = sys.executable
PIN = 'D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
REFERENCE = Path('C:/work/fraktal-ab-s5-20261029/session_19/preflight.json')
CREDENTIAL = 'C:/work/fraktal_echo38_access_fixture.json'
DUMPS = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/'
             '91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
FLAGS = ('RestoreGenealogyAuthorized', 'BaselineRegressionWritesAuthorized', 'ManualNormalizationAuthorized',
         'MailboxOrTagWritesAuthorized')
NEVER = ('DownloadAuthorized', 'BackupUploadAuthorized', 'FaultClearAuthorized', 'ClockSetAuthorized',
         'PowerOperationsAuthorized', 'VendorStateEditsAuthorized')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def authorize(value):
    if (value.get('CurrentOwnerApproved') is not True or value.get('StandingDecision') != 'O3'
            or value.get('Serial') != '601FC87B' or value.get('CanonicalSha256') != PIN
            or not str(value.get('OwnerInstruction', '')).strip()
            or any(value.get(k) is not True for k in FLAGS) or any(value.get(k) is not False for k in NEVER)):
        raise ValueError('armed standing O3 record for exactly this re-baseline required')


def save(name, value):
    with (D / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def dumps():
    return sorted(p.relative_to(DUMPS).as_posix() for p in DUMPS.rglob('*.dmp')) if DUMPS.exists() else []


def main():
    authorize(json.loads((D / 'authorization.json').read_bytes()))
    bindings = json.loads((D / 'source_bindings.json').read_bytes())
    for path, expected in bindings['sha256'].items():
        assert digest(path) == expected, 'bound input changed: ' + path
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(['git', 'status', '--porcelain', '--', 'FraktalCore/PLC/Allen-Bradley/tools'], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout
    assert head == bindings['repositoryHead'] and not dirty, 'tools tree differs from the bound commit'
    assert (D / 'canonical.sha256').read_text().strip() == PIN == digest('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')
    save('session_started.json', dict(approvalSha256=digest(D / 'authorization.json'), pinSha256=PIN,
         repositoryHead=head, utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    stages, error = [], None

    def run(label, *args):
        print(json.dumps(dict(stage=label, status='started')), flush=True)
        stages.append(label)
        subprocess.run([PY, str(D / 'run_logged.py'), label, *map(str, args)], cwd=ROOT, check=True)

    def audit(label, *operations):
        arguments = [PY, T / 'fraktal_ab_sdk_log_gate.py', D / (label + '.log')]
        for operation in operations:
            arguments += ['--require', operation]
        run(label + '_audit', *arguments)

    try:
        run('guard_initial', PY, D / 'scripts/guard_echo.py')
        save('dumps_initial.json', dict(readOnly=True, dumpFiles=dumps()))
        if dumps():
            raise RuntimeError('controller dump present; no change permitted')
        run('pre_download_guard', PY, D / 'pre_download_guard.py')
        run('restore_genealogy', SDK, 'restore-genealogy')
        audit('restore_genealogy', 'Open project', 'Download', 'Save', 'Save As')
        run('restore_access', PY, D / 'audit_baseline_access.py', D / 'genealogy_restored.L5X',
            '--output', D / 'restore_access.json')
        os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
        run('guard_baseline', PY, D / 'scripts/guard_echo.py')
        run('medium_check', PY, D / 'medium_check.py')
        run('baseline_regressions', PY, T / 'fraktal_ab_genealogy_execute.py', '--execute-fixture',
            '--expect-serial', '601FC87B', '--credential-file', CREDENTIAL,
            '--output', D / 'baseline_regressions.json')
        run('manual_final', PY, D / 'ensure_manual_baseline.py', '--output', D / 'manual_final.json')
        run('preflight', PY, D / 'preflight.py')
        preflight = json.loads((D / 'preflight.json').read_bytes())
        reference = json.loads(REFERENCE.read_bytes())
        save('preflight_reference_comparison.json', dict(readOnly=True, reference=str(REFERENCE),
             equal=preflight == reference, differingKeys=sorted(k for k in set(preflight) | set(reference)
                                                                 if preflight.get(k) != reference.get(k))))
        if preflight != reference:
            raise RuntimeError('re-established baseline differs from the verified S5 baseline record')
        run('final_checks', PY, D / 'final_checks.py', D / 'final_checks.json')
        run('baseline_timing', PY, D / 'measure_timing.py', D / 'baseline_timing.json')
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        print(json.dumps(dict(error=error)), flush=True)
    save('session_result.json', dict(passed=error is None and not dumps(), error=error, stagesStarted=stages,
         downloadAttempted=(D / 'download_attempt.json').exists(), dumpFiles=dumps(), backupUploads=0,
         faultClears=0, taskCounterClears=0, clockChanges=0, powerOperations=0, echoHardKills=0,
         utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return 0 if error is None and not dumps() else 1


if __name__ == '__main__':
    raise SystemExit(main())
