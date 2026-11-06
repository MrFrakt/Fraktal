"""O11 apparatus: one owned, pinned loopback gateway per fixture connection.

The process is started with an immutable, serial-pinned CIP endpoint. Its
unguessable instance name is checked through the existing readiness endpoint
before each command, together with process liveness. A different listener or
terminated process can never receive a fixture write. No controller operation
is performed here; all requests still use the brand-neutral command client.
"""
from __future__ import annotations
import atexit
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request
import uuid


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('gateway readiness must not redirect')


def health(url):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
    with opener.open(url,timeout=1) as response:
        data=response.read(65537)
    if len(data)>65536:raise ValueError('gateway readiness reply exceeds budget')
    return json.loads(data)


def connection_state(comm):
    """Session state belongs to the owned connection, including behind Guarded.

    PLC uses __slots__; its Connection supports apparatus state and owns the
    explicit close boundary used by both PLC.Close() and PLC.__exit__().
    """
    native=getattr(comm,'comm',comm)
    return getattr(native,'conn',native)


class GatewayLease:
    """Owns only the gateway child, never Echo or another process.

    Package hash and endpoint come from the session preparation. No failed
    process is restarted; a fresh fixture session must explicitly create a new
    lease. The output directory is private run evidence, never credentials.
    """
    def __init__(self,executable,sha256,*,host,slot,serial,root,directory,
                 read_only=False,spawn=subprocess.Popen,read_health=health,
                 clock=time.monotonic,sleep=time.sleep):
        self.executable=Path(executable).resolve()
        if not self.executable.is_file() or self.executable.suffix.lower()!='.exe':
            raise ValueError('prepared gateway executable is required')
        digest=hashlib.sha256(self.executable.read_bytes()).hexdigest().upper()
        if not isinstance(sha256,str) or digest!=sha256.upper():
            raise ValueError('prepared gateway executable hash differs')
        if host=='localhost':host='127.0.0.1'
        try:loopback=ipaddress.ip_address(host).is_loopback
        except ValueError:loopback=False
        if not loopback or slot!=0 or serial.upper()!='601FC87B' or root!='Press':
            raise ValueError('gateway apparatus is confined to the declared local Echo fixture')
        self.serial,self.root,self.digest=serial.upper(),root,digest
        self.read_only,self._spawn,self._health=read_only,spawn,read_health
        self._clock,self._sleep=clock,sleep
        self.directory=Path(directory).resolve();self.directory.mkdir(parents=True,exist_ok=True)
        self.instance='hx-'+self.serial+'-'+uuid.uuid4().hex
        # Releasing the reservation is safe: a lost port race refuses through
        # process liveness and the unpredictable readiness identity, before I/O.
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1',0));self.port=reservation.getsockname()[1]
        authority='['+host+']' if ':' in host else host
        endpoint=f'cip://{authority}?slot={slot}&serial={self.serial}'
        self.url=f'ws://127.0.0.1:{self.port}/fraktal'
        self.health_url=f'http://127.0.0.1:{self.port}/readyz'
        self.arguments=[str(self.executable),'--plc-endpoint',endpoint,'--port',str(self.port),
                        '--path','/fraktal','--instance-name',self.instance]
        if not read_only:self.arguments+=['--write-root',root]
        self.process=None;self._log=None;self._closed=False

    def start(self,timeout=60):
        if self.process is not None or self._closed:raise ValueError('gateway lease is single-use')
        if not 0<timeout<=120:raise ValueError('gateway startup must be bounded')
        if hashlib.sha256(self.executable.read_bytes()).hexdigest().upper()!=self.digest:
            raise ValueError('prepared gateway executable changed before startup')
        self._log=(self.directory/(self.instance+'.log')).open('x',encoding='utf-8')
        try:
            atexit.register(self.close)
            self.process=self._spawn(self.arguments,cwd=self.executable.parent,
                stdout=self._log,stderr=subprocess.STDOUT,shell=False,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            with (self.directory/(self.instance+'.json')).open('x',encoding='utf-8') as out:
                json.dump(dict(schema='fraktal.harness.gateway-lease',schemaVersion=1,pid=self.process.pid,
                    executableSha256=self.digest,arguments=self.arguments,url=self.url,
                    serial=self.serial,root=self.root,readOnly=self.read_only),out,indent=2)
            deadline=self._clock()+timeout
            while self._clock()<deadline:
                if self.process.poll() is not None:raise RuntimeError('prepared gateway exited before readiness')
                if self.guard(serial=self.serial,root=self.root,url=self.url):return self
                self._sleep(.05)
            raise TimeoutError('prepared gateway did not become ready')
        except BaseException:
            self.close();raise

    def guard(self,*,serial,root,url):
        if self._closed or self.process is None or self.process.poll() is not None or \
                serial.upper()!=self.serial or root!=self.root or url!=self.url:
            return False
        try:reply=self._health(self.health_url)
        except Exception:return False
        if not isinstance(reply,dict) or reply.get('instance')!=self.instance or \
                reply.get('status')!='ready' or reply.get('plcReady') is not True:
            return False
        policy=reply.get('writeAccess')
        return isinstance(policy,dict) and policy.get('enabled') is (not self.read_only) and \
            policy.get('allRootMailboxes') is False and \
            policy.get('roots')==([] if self.read_only else [self.root])

    def close(self):
        if self._closed:return
        self._closed=True
        atexit.unregister(self.close)
        try:
            if self.process is not None and self.process.poll() is None:
                # This is our stateless gateway child, never the controller.
                self.process.terminate()
                self.process.wait(timeout=10)
        finally:
            if self._log is not None:self._log.close()

    def __enter__(self):return self.start()
    def __exit__(self,*unused):self.close()


def bind(comm,session):
    """Used only after the exact fixture identity/fingerprint, before a command."""
    state=connection_state(comm)
    if getattr(state,'_fraktal_gateway_guard',None) is not None:return None
    executable=getattr(state,'_fraktal_gateway_executable',None) or os.environ.get('FRAKTAL_HARNESS_GATEWAY')
    digest=getattr(state,'_fraktal_gateway_sha256',None) or os.environ.get('FRAKTAL_HARNESS_GATEWAY_SHA256')
    if not executable or not digest:
        raise ValueError('collapsed fixture requires the prepared gateway path and SHA-256')
    directory=getattr(state,'_fraktal_gateway_directory',None) or os.environ.get('FRAKTAL_HARNESS_OUTPUT')
    if directory is None:directory=tempfile.mkdtemp(prefix='FraktalHarnessGateway_')
    native=getattr(comm,'comm',comm)
    # pylogix 1.1.5's __exit__ calls conn.close() directly, not PLC.Close().
    # Hook that shared explicit-close boundary; internal identity reconnects
    # use _close_connection() and do not end the fixture's gateway lease.
    connection=getattr(native,'conn',None)
    owner,method=(connection,'close') if connection is not None else (native,'Close')
    original_close=getattr(owner,method,None)
    if not callable(original_close):raise ValueError('fixture connection has no owned close boundary')
    lease=GatewayLease(executable,digest,host=comm.IPAddress,slot=comm.ProcessorSlot,
                       serial=session.expected_serial,root=session.root,directory=directory).start()
    def close_with_gateway(*args,**kwargs):
        try:lease.close()
        finally:original_close(*args,**kwargs)
    try:
        setattr(owner,method,close_with_gateway)
        state._fraktal_gateway_lease=lease
        state._fraktal_gateway_url=lease.url
        state._fraktal_gateway_guard=lease.guard
    except BaseException:
        lease.close();raise
    return lease


def close(comm):
    lease=getattr(connection_state(comm),'_fraktal_gateway_lease',None)
    if lease is not None:lease.close()
