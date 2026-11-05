"""One guarded S6 V6.11 host-services capture session, with genealogy rollback after any download.

Plan §4 on the standing Echo decision O3. No controller access happens before the
armed record, the source bindings and the clean tools tree verify. Stages:
baseline guard and backup; download of the exact candidate; the Dart host
adapter restoring its live documents natively from a session copy; the
unchanged fixture's core rows producing host events; a quiet read-only capture
of both rings. Writers stop at their first failure. Then the rollback: genealogy
pin, the five original documents (never written: the adapter used a copy),
31 baseline cases, MANUAL, preflight equal to the start, final checks, timing.
The adapter and the TASK monitor are this session's own child processes; they
are the only processes it ever stops, and never Echo.
"""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys, time

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'
SDK = D / 'session/bin/Debug/net8.0/win-x86/HostSession.exe'
ADAPTER = D / 'bin/fraktal_host_adapter.exe'
PY = sys.executable
CANDIDATE, SOURCE = ('902831B49087BA2FF658412E1293296B29CEF956D573333B19838EA8AE74E5C4',
                     '5ADEF279CB93BE1D53ED067915C8F7C21434658DD32C633E7DC3176D1BEDE2FA')
CREDENTIAL = 'C:/work/fraktal_echo38_access_fixture.json'
BASELINE_PREFLIGHT = Path('C:/work/fraktal-ab-s6-rebaseline-20261104/session_01/preflight.json')
LIVE = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/ConfigSets/601FC87B-Press/live'
DUMPS = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/'
             '91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
FLAGS = ('BackupUploadAuthorized', 'DownloadAuthorized', 'MailboxOrTagWritesAuthorized', 'ManualNormalizationAuthorized',
         'RestoreGenealogyAuthorized', 'BaselineRegressionWritesAuthorized', 'HostAdapterWritesAuthorized')
NEVER = ('FaultClearAuthorized', 'ClockSetAuthorized', 'PowerOperationsAuthorized', 'VendorStateEditsAuthorized')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def authorize(value):
    if (value.get('CurrentOwnerApproved') is not True or value.get('StandingDecision') != 'O3'
            or value.get('Serial') != '601FC87B' or value.get('CanonicalSha256') != CANDIDATE
            or value.get('SourceSha256') != SOURCE or not str(value.get('OwnerInstruction', '')).strip()
            or any(value.get(k) is not True for k in FLAGS) or any(value.get(k) is not False for k in NEVER)):
        raise ValueError('armed standing O3 record for exactly this candidate and rollback required')


def save(name, value):
    with (D / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write('\n')


def dumps():
    return sorted(p.relative_to(DUMPS).as_posix() for p in DUMPS.rglob('*.dmp')) if DUMPS.exists() else []


def tree_hashes(folder):
    return {p.name: digest(p) for p in sorted(folder.iterdir()) if p.is_file()}


def main():
    authorize(json.loads((D / 'authorization.json').read_bytes()))
    bindings = json.loads((D / 'source_bindings.json').read_bytes())
    for path, expected in bindings['sha256'].items():
        assert digest(path) == expected, 'bound input changed: ' + path
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(['git', 'status', '--porcelain', '--', 'FraktalCore/PLC/Allen-Bradley/tools',
                            'FraktalCore/HMI/gateway/lib', 'FraktalCore/HMI/gateway/bin',
                            'FraktalCore/HMI/packages/fraktal_opcua_client/lib'],
                           cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert head == bindings['repositoryHead'] and not dirty, 'source tree differs from the bound commit'
    assert (D / 'canonical.sha256').read_text().strip() == CANDIDATE == digest(D / 's6_host_05.ACD')
    originals = tree_hashes(LIVE)
    save('session_started.json', dict(approvalSha256=digest(D / 'authorization.json'), candidateSha256=CANDIDATE,
         sourceSha256=SOURCE, repositoryHead=head, originalLiveHashes=originals,
         utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    stages, candidate_error, rollback_error, rollback_ok = [], None, None, False
    children = {}

    def run(label, *args, env=None):
        print(json.dumps(dict(stage=label, status='started')), flush=True)
        stages.append(label)
        subprocess.run([PY, str(D / 'run_logged.py'), label, *map(str, args)], cwd=ROOT, check=True,
                       env=None if env is None else {**os.environ, **env})

    def audit(label, *operations):
        arguments = [PY, T / 'fraktal_ab_sdk_log_gate.py', D / (label + '.log')]
        for operation in operations:
            arguments += ['--require', operation]
        run(label + '_audit', *arguments)

    def start(name, args, env=None, ready=None):
        log = (D / f'{name}.log').open('x', encoding='utf-8')
        process = subprocess.Popen(args, cwd=D, stdout=log, stderr=subprocess.STDOUT,
                                   env=None if env is None else {**os.environ, **env},
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        children[name] = (process, log)
        if ready is not None:
            deadline = time.monotonic() + 20
            while not ready.exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError(f'{name} did not become ready')
                time.sleep(.2)

    def stop(name, stop_file=None):
        if name not in children:
            return
        process, log = children.pop(name)
        if stop_file is not None:
            with stop_file.open('x') as stream:
                json.dump(dict(stop=True), stream)
            try:
                code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.terminate()  # this session's own read-only helper, never Echo
                code = process.wait(timeout=10)
        else:
            process.terminate()  # the adapter never resends; an open job times out and refuses
            code = process.wait(timeout=10)
        log.close()
        save(f'{name}_exit.json', dict(exitCode=code, stoppedBySession=True))

    try:
        os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
        run('guard_initial', PY, D / 'scripts/guard_echo.py')
        save('dumps_initial.json', dict(readOnly=True, dumpFiles=dumps()))
        if dumps():
            raise RuntimeError('controller dump present; no change permitted')
        run('manual_initial', PY, D / 'ensure_manual_baseline.py', '--output', D / 'manual_initial.json')
        run('preflight_initial', PY, D / 'preflight.py')
        if json.loads((D / 'preflight.json').read_bytes()) != json.loads(BASELINE_PREFLIGHT.read_bytes()):
            raise RuntimeError('Echo is not on the re-established genealogy baseline')
        run('backup', SDK, 'backup')
        audit('backup', 'Save As')
        run('backup_access', PY, D / 'audit_baseline_access.py', D / 'echo_before_s6.L5X', '--output', D / 'backup_access.json')
        start('task_monitor', [PY, str(D / 'task_monitor.py')], ready=D / 'task_monitor_ready.json')
        run('deploy', SDK, 'deploy-candidate')
        audit('deploy', 'Open project', 'Download', 'Save', 'Save As')
        run('deploy_readback', PY, T / 'fraktal_ab_readback.py', D / 's6_host_05.L5X', D / 'candidate_downloaded.L5X')
        run('deploy_access', PY, D / 'audit_access_candidate.py', D / 'candidate_downloaded.L5X', D / 'deploy_access.json')
        os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_s6_host_demo'
        run('guard_candidate', PY, D / 'scripts/guard_echo.py')
        # The adapter serves a byte-exact copy, so the original documents are never written.
        (D / 'medium/live').mkdir(parents=True)
        for name in originals:
            with (D / 'medium/live' / name).open('xb') as stream:
                stream.write((LIVE / name).read_bytes())
        assert tree_hashes(D / 'medium/live') == originals
        # Restoring writes stay under the logged-in session's authorization; the
        # adapter gains no login (session 02 was denied the line document logged out).
        run('login', PY, D / 'session_login.py', 'login')
        start('adapter', [str(ADAPTER), '--host', '127.0.0.1', '--slot', '0', '--expect-serial', '601FC87B'],
              env={'FRAKTAL_AB_CONFIG_SET_DIR': str(D / 'medium')})
        run('adapter_restore', PY, D / 'adapter_restore_check.py')
        run('logout', PY, D / 'session_login.py', 'logout')
        run('events', PY, D / 'events.py')
        stop('adapter')
        time.sleep(2)  # let the last scans settle; the capture brackets the ring itself
        run('capture', PY, D / 'capture.py')
    except Exception as error:
        candidate_error = f'{type(error).__name__}: {error}'
        print(json.dumps(dict(candidateError=candidate_error)), flush=True)
    finally:
        try:
            stop('adapter')
        except Exception as error:
            candidate_error = candidate_error or f'adapter stop: {error}'
        try:
            stop('task_monitor', D / 'task_monitor_stop.json')
        except Exception as error:
            candidate_error = candidate_error or f'monitor stop: {error}'
        if (D / 'session_login_login.json').exists() and not (D / 'session_login_logout.json').exists():
            try:
                run('logout_after_failure', PY, D / 'session_login.py', 'logout')
            except Exception as error:
                candidate_error = candidate_error or f'logout: {error}'
        if (D / 'deploy_attempt.json').exists():
            try:
                if dumps():
                    raise RuntimeError('controller dump present; rollback stopped before any further change')
                os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_s6_host_demo'
                run('guard_rollback', PY, D / 'scripts/guard_echo.py')
                run('manual_rollback', PY, D / 'ensure_manual_candidate.py', '--output', D / 'manual_rollback.json')
                run('restore_genealogy', SDK, 'restore-genealogy')
                audit('restore_genealogy', 'Open project', 'Download', 'Save', 'Save As')
                run('restore_access', PY, D / 'audit_baseline_access.py', D / 'genealogy_restored.L5X',
                    '--output', D / 'restore_access.json')
                os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
                run('guard_baseline', PY, D / 'scripts/guard_echo.py')
                if tree_hashes(LIVE) != originals:
                    raise RuntimeError('original host documents changed during the session')
                run('medium_check', PY, D / 'medium_check.py')
                run('baseline_regressions', PY, T / 'fraktal_ab_genealogy_execute.py', '--execute-fixture',
                    '--expect-serial', '601FC87B', '--credential-file', CREDENTIAL,
                    '--output', D / 'baseline_regressions.json')
                run('manual_final', PY, D / 'ensure_manual_baseline.py', '--output', D / 'manual_final.json')
                run('preflight_final', PY, D / 'preflight.py', '--verify-only')
                run('final_checks', PY, D / 'final_checks.py', D / 'final_checks.json')
                run('baseline_timing', PY, D / 'measure_timing.py', D / 'baseline_timing.json')
                rollback_ok = True
            except Exception as error:
                rollback_error = f'{type(error).__name__}: {error}'
                print(json.dumps(dict(rollbackError=rollback_error)), flush=True)
        save('session_result.json', dict(passed=candidate_error is None and rollback_ok and not dumps(),
             candidateError=candidate_error, rollbackError=rollback_error, genealogyRestored=rollback_ok,
             stagesStarted=stages, dumpFiles=dumps(), originalLiveUnchanged=tree_hashes(LIVE) == originals,
             faultClears=0, taskCounterClears=0, clockChanges=0, powerOperations=0, echoHardKills=0,
             utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return 0 if candidate_error is None and rollback_ok and not dumps() else 1


if __name__ == '__main__':
    raise SystemExit(main())
