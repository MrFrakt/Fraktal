"""O11 apparatus: one owned, pinned loopback gateway per fixture connection.

The process is started with an immutable, serial-pinned CIP endpoint. Its
unguessable instance name is checked through the existing readiness endpoint
before each command, together with process liveness. A different listener or
terminated process can never receive a fixture write. No controller operation
is performed here; all requests still use the brand-neutral command client.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request
from fraktal_ab_harness_process import ProcessLease, echo_target, connection_state, attach


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('gateway readiness must not redirect')


def health(url):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
    with opener.open(url,timeout=1) as response:
        data=response.read(65537)
    if len(data)>65536:raise ValueError('gateway readiness reply exceeds budget')
    return json.loads(data)


class GatewayLease(ProcessLease):
    """Owns only the gateway child, never Echo or another process.

    Package hash and endpoint come from the session preparation. No failed
    process is restarted; a fresh fixture session must explicitly create a new
    lease. The output directory is private run evidence, never credentials.
    """
    def __init__(self,executable,sha256,*,host,slot,serial,root,directory,
                 read_only=False,spawn=subprocess.Popen,read_health=health,
                 clock=time.monotonic,sleep=time.sleep):
        host,self.serial=echo_target(host,slot,serial,root)
        self.root=root
        super().__init__(executable,sha256,directory=directory,prefix='hx-'+self.serial,spawn=spawn)
        self.read_only,self._health=read_only,read_health
        self._clock,self._sleep=clock,sleep
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

    def start(self,timeout=60):
        if self.process is not None or self._closed:raise ValueError('gateway lease is single-use')
        if not 0<timeout<=120:raise ValueError('gateway startup must be bounded')
        try:
            self.start_child(dict(schema='fraktal.harness.gateway-lease',url=self.url,
                                  serial=self.serial,root=self.root,readOnly=self.read_only))
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
    lease=GatewayLease(executable,digest,host=comm.IPAddress,slot=comm.ProcessorSlot,
                       serial=session.expected_serial,root=session.root,directory=directory).start()
    try:
        attach(comm,'gateway',lease)
        state._fraktal_gateway_lease=lease
        state._fraktal_gateway_url=lease.url
        state._fraktal_gateway_guard=lease.guard
    except BaseException:
        lease.close();raise
    return lease


def close(comm):
    lease=getattr(connection_state(comm),'_fraktal_gateway_lease',None)
    if lease is not None:lease.close()
