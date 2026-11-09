"""Owned, hash-pinned fixture processes; never a controller process."""
import atexit
import hashlib
import ipaddress
import json
from pathlib import Path
import subprocess
import uuid


def connection_state(comm):
    native = getattr(comm, 'comm', comm)
    return getattr(native, 'conn', native)


def attach(comm, name, lease):
    """One explicit-close hook drains every owned child, even after a failure."""
    state = connection_state(comm)
    children = getattr(state, '_fraktal_child_leases', None)
    if children is None:
        native = getattr(comm, 'comm', comm)
        connection = getattr(native, 'conn', None)
        owner, method = (connection, 'close') if connection is not None else (native, 'Close')
        original = getattr(owner, method, None)
        if not callable(original):
            raise ValueError('fixture connection has no owned close boundary')
        children = {}
        def close_owned(*args, **kwargs):
            errors = []
            for child in tuple(children.values()):
                try:
                    child.close()
                except BaseException as error:
                    errors.append(error)
            try:
                return original(*args, **kwargs)
            finally:
                if errors:
                    raise errors[0]
        setattr(owner, method, close_owned)
        state._fraktal_child_leases = children
    if name in children:
        raise ValueError('fixture already owns this process lease')
    children[name] = lease


def echo_target(host, slot, serial, root):
    if host == 'localhost':
        host = '127.0.0.1'
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = False
    if not local or slot != 0 or not isinstance(serial, str) or serial.upper() != '601FC87B' or root != 'Press':
        raise ValueError('apparatus is confined to the declared local Echo fixture')
    return host, serial.upper()


class ProcessLease:
    """One child, no restart or process discovery/termination by name."""
    def __init__(self, executable, sha256, *, directory, prefix, spawn=subprocess.Popen):
        self.executable = Path(executable).resolve()
        if not self.executable.is_file() or self.executable.suffix.lower() != '.exe':
            raise ValueError('prepared executable is required')
        self.digest = hashlib.sha256(self.executable.read_bytes()).hexdigest().upper()
        if not isinstance(sha256, str) or self.digest != sha256.upper():
            raise ValueError('prepared executable hash differs')
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.instance = (prefix + '-' + uuid.uuid4().hex)[:32]
        self.log_path = self.directory / (self.instance + '.log')
        self.process, self._log, self._closed = None, None, False
        self._spawn = spawn

    def start_child(self, record, *, environment=None):
        if self.process is not None or self._closed:
            raise ValueError('process lease is single-use')
        if hashlib.sha256(self.executable.read_bytes()).hexdigest().upper() != self.digest:
            raise ValueError('prepared executable changed before startup')
        self._log = self.log_path.open('x', encoding='utf-8')
        try:
            atexit.register(self.close)
            options = dict(cwd=self.executable.parent, stdout=self._log, stderr=subprocess.STDOUT,
                           shell=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if environment is not None:
                options['env'] = environment
            self.process = self._spawn(self.arguments, **options)
            with (self.directory / (self.instance + '.json')).open('x', encoding='utf-8') as out:
                json.dump(dict(schemaVersion=1, pid=self.process.pid, executableSha256=self.digest,
                               arguments=self.arguments, **record), out, indent=2)
        except BaseException:
            self.close()
            raise

    def alive(self):
        return not self._closed and self.process is not None and self.process.poll() is None

    def close(self):
        if self._closed:
            return
        self._closed = True
        atexit.unregister(self.close)
        try:
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=10)
        finally:
            if self._log is not None:
                self._log.close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *unused):
        self.close()
