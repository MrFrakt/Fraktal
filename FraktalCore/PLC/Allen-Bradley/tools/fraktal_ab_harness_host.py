"""Supervise the existing Dart V6.11 adapter on a fresh, isolated fixture store.

This module transports no host job and contains no broker/keeper. Serving,
failure and root identity come from the owned child's JSON log. A failure is
latched for the lease; it never restarts or silently accepts a later reconnect.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from fraktal_ab_harness_process import ProcessLease, echo_target, connection_state, attach

MAX_LOG_READ = 1_048_576
STORE_FILE = re.compile(r'(?:[0-9a-f]{64}\.jsonl|live/(?:index\.json|[0-9a-f]{64}\.jsonl))\Z')


def other_adapters():
    # Print PIDs only; another process's command line never enters evidence.
    script = '''$ErrorActionPreference = 'Stop'
$rows = @(Get-CimInstance Win32_Process -Filter "Name='fraktal_host_adapter.exe'" |
 Where-Object { -not $_.CommandLine -or $_.CommandLine -match '601FC87B' } |
 ForEach-Object { [int]$_.ProcessId })
ConvertTo-Json -InputObject $rows -Compress'''
    reply = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
                           capture_output=True, timeout=15, check=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    rows = json.loads(reply.stdout)
    if not isinstance(rows, list) or any(type(pid) is not int or pid <= 0 for pid in rows):
        raise ValueError('adapter process inventory did not answer')
    return rows


class ReadOnlyStore:
    """Independent file reopen using the portable format; no save/delete API."""
    def __init__(self, directory):
        self.directory = Path(directory)

    def read(self, name):
        from fraktal_ab_set_documents import FileStore
        return FileStore(self.directory).read(name)

    def list(self):
        from fraktal_ab_set_documents import FileStore
        return FileStore(self.directory).list()


def read_seed_files(manifest, digest, serial, root):
    """Validate and read a prepared byte-bound medium without mutating it."""
    if not manifest or not digest:
        raise ValueError('prepared original-medium seed manifest and SHA-256 are required')
    manifest = Path(manifest).resolve()
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != digest.upper():
        raise ValueError('store seed manifest hash differs')
    held = json.loads(raw)
    if held.get('schema') != 'fraktal.harness.store-seed' or held.get('schemaVersion') != 1 \
            or held.get('serial') != serial.upper() or held.get('root') != root:
        raise ValueError('store seed target/schema differs')
    source = Path(held['directory']).resolve()
    rows = held.get('files')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 256:
        raise ValueError('store seed requires a bounded file manifest')
    payloads, total, originals = {}, 0, []
    for row in rows:
        name = row['path']
        if not isinstance(name, str) or not STORE_FILE.fullmatch(name) or name in payloads:
            raise ValueError('unsafe or duplicate store seed path')
        path = source / name
        if path.is_symlink() or not path.resolve().is_relative_to(source):
            raise ValueError('store seed path escaped its source')
        data = path.read_bytes()
        total += len(data)
        if total > 16_777_216 or hashlib.sha256(data).hexdigest().upper() != row['sha256'].upper():
            raise ValueError('store seed bytes differ or exceed budget')
        payloads[name] = data
        originals.append(dict(path=str(path), sha256=row['sha256'].upper()))
    return payloads, originals


def seed_store(destination, manifest, digest, serial, root):
    """Copy a prepared byte-bound medium; never open the owner's original in Dart."""
    payloads, originals = read_seed_files(manifest, digest, serial, root)
    for name, data in payloads.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as out:
            out.write(data)
    return originals


class HostLease(ProcessLease):
    def __init__(self, executable, sha256, *, host, slot, serial, root, directory, store,
                 seed=None, seed_sha256=None, spawn=subprocess.Popen,
                 competitors=other_adapters, clock=time.monotonic, sleep=time.sleep):
        host, self.serial = echo_target(host, slot, serial, root)
        self.root = root
        super().__init__(executable, sha256, directory=directory, prefix='hx-host-' + self.serial, spawn=spawn)
        self.store = Path(store).resolve()
        # A lease owns a new store only. Reusing an existing folder, including
        # the owner's deployed medium, is never an implicit operation.
        if self.store.exists() or self.store == self.store.parent:
            raise ValueError('host fixture requires a new isolated store')
        if bool(seed) != bool(seed_sha256):
            raise ValueError('store seed requires its prepared manifest hash')
        self.seed, self.seed_sha256 = seed, seed_sha256
        self.arguments = [str(self.executable), '--host', host, '--port', '44818', '--slot', str(slot),
                          '--expect-serial', self.serial, '--interval-ms', '20']
        self._clock, self._sleep = clock, sleep
        self._competitors = competitors
        self._offset, self._buffer, self._serving = 0, b'', False
        self.failure, self.health = '', {}
        self.seed_files = []

    def start(self, timeout=60):
        if self.process is not None or self._closed:
            raise ValueError('host lease is single-use')
        if not 0 < timeout <= 120:
            raise ValueError('host startup must be bounded')
        try:
            if self._competitors():
                raise ValueError('another host adapter may own the Echo controller')
            self.store.mkdir(parents=True, exist_ok=False)
            if self.seed:
                self.seed_files = seed_store(self.store, self.seed, self.seed_sha256, self.serial, self.root)
            environment = dict(os.environ, FRAKTAL_AB_CONFIG_SET_DIR=str(self.store))
            self.start_child(dict(schema='fraktal.harness.host-lease', serial=self.serial,
                                  root=self.root, store=str(self.store), seedManifestSha256=self.seed_sha256),
                             environment=environment)
            deadline = self._clock() + timeout
            while self._clock() < deadline:
                if not self.alive():
                    raise RuntimeError('prepared host adapter exited before readiness')
                if self.guard(serial=self.serial, root=self.root):
                    return self
                if self.failure:
                    raise RuntimeError('host adapter refused readiness: ' + self.failure)
                self._sleep(.05)
            raise TimeoutError('prepared host adapter did not become ready')
        except BaseException:
            self.close()
            raise

    def _status(self):
        with self.log_path.open('rb') as source:
            source.seek(self._offset)
            raw = source.read(MAX_LOG_READ + 1)
        if len(raw) > MAX_LOG_READ:
            raise ValueError('adapter log exceeds the bounded poll')
        self._offset += len(raw)
        lines = (self._buffer + raw).split(b'\n')
        self._buffer = lines.pop()
        if len(self._buffer) > 65536:
            raise ValueError('adapter log line exceeds budget')
        for line in lines:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError('invalid adapter status')
            state = row.get('state')
            if state == 'serving':
                if row.get('roots') != [self.root] or any(r != self.root for r in row.get('eventRings', [])):
                    raise ValueError('adapter serves another root')
                self._serving = True
            elif state is not None:
                raise ValueError('adapter is unavailable: ' + str(state))
            if 'root' in row:
                if row['root'] != self.root:
                    raise ValueError('adapter status belongs to another root')
                self.health.update(row)
                if 'health' in row and (not isinstance(row['health'], dict)
                                       or type(row['health'].get('failed')) is not bool):
                    raise ValueError('invalid adapter health status')
                if any(isinstance(row.get(key), dict) and row[key].get('failed') is True
                       for key in ('health', 'events')):
                    raise ValueError('adapter reported a failed service')

    def guard(self, *, serial, root):
        if self.failure or not self.alive() or serial.upper() != self.serial or root != self.root:
            return False
        try:
            self._status()
        except (OSError, ValueError, TypeError) as error:
            self.failure = str(error)
            return False
        return self._serving

    def originals_unchanged(self):
        return all(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest().upper() == row['sha256']
                   for row in self.seed_files)


def bind(comm, app, *, store=None, require_seed=False):
    """Join the connection's owned adapter, or start one from preparation pins."""
    import tempfile
    import fraktal_ab_fixture_reads as fixture
    session = fixture._session(comm, app)
    fixture._guard_command(comm, session)
    state = connection_state(comm)
    current = getattr(state, '_fraktal_host_lease', None)
    if current is not None:
        if not current.guard(serial=session.expected_serial, root=session.root):
            raise ValueError('owned host adapter is no longer ready; no restart')
        if require_seed and not current.seed:
            raise ValueError('document restoration requires the prepared original medium seed')
        return current
    executable = os.environ.get('FRAKTAL_HARNESS_HOST_ADAPTER')
    digest = os.environ.get('FRAKTAL_HARNESS_HOST_ADAPTER_SHA256')
    seed = os.environ.get('FRAKTAL_HARNESS_HOST_SEED')
    seed_hash = os.environ.get('FRAKTAL_HARNESS_HOST_SEED_SHA256')
    if not executable or not digest or require_seed and not seed:
        raise ValueError('prepared host executable/hash and original-medium seed are required')
    directory = os.environ.get('FRAKTAL_HARNESS_OUTPUT') or tempfile.mkdtemp(prefix='FraktalHarnessHost_')
    if store is None:
        store = Path(directory) / ('store-' + uuid.uuid4().hex)
    lease = HostLease(executable, digest, host=comm.IPAddress, slot=comm.ProcessorSlot,
                      serial=session.expected_serial, root=session.root, directory=directory,
                      store=store, seed=seed, seed_sha256=seed_hash).start()
    try:
        attach(comm, 'host', lease)
        state._fraktal_host_lease = lease
    except BaseException:
        lease.close()
        raise
    return lease
