"""A wrong package, process, endpoint or listener never receives a fixture command."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import fraktal_ab_harness_gateway as launch


class Process:
    pid=12345
    def __init__(self):self.code=None;self.terminated=False
    def poll(self):return self.code
    def terminate(self):self.terminated=True;self.code=0
    def wait(self,timeout):return self.code


class Lease(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.exe=self.folder/'gateway.exe'
        self.exe.write_bytes(b'prepared package')
        self.sha=hashlib.sha256(self.exe.read_bytes()).hexdigest().upper()
        self.now=0.;self.proc=Process();self.spawns=[];self.reply=None
    def clock(self):return self.now
    def sleep(self,seconds):self.now+=seconds
    def spawn(self,args,**kwargs):
        self.spawns.append((args,kwargs));return self.proc
    def make(self,**kwargs):
        options=dict(host='127.0.0.1',slot=0,serial='601FC87B',root='Press',directory=self.folder,
                     spawn=self.spawn,read_health=lambda url:self.reply,clock=self.clock,sleep=self.sleep)
        options.update(kwargs)
        lease=launch.GatewayLease(self.exe,self.sha,**options)
        self.addCleanup(lease.close)
        self.reply=dict(instance=lease.instance,status='ready',plcReady=True,
                        writeAccess=dict(enabled=not lease.read_only,roots=[] if lease.read_only else ['Press'],allRootMailboxes=False))
        return lease
    def check(self,lease):return lease.guard(serial='601FC87B',root='Press',url=lease.url)

    def test_owned_process_binds_exact_endpoint_and_root_before_ready(self):
        lease=self.make().start()
        args,options=self.spawns[0]
        self.assertEqual(args[args.index('--plc-endpoint')+1],'cip://127.0.0.1?slot=0&serial=601FC87B')
        self.assertEqual(args[args.index('--write-root')+1],'Press')
        self.assertEqual(args[args.index('--instance-name')+1],lease.instance)
        self.assertIs(options['shell'],False)
        self.assertTrue(self.check(lease))
        record=json.loads(next(self.folder.glob('hx-*.json')).read_bytes())
        self.assertEqual(record['executableSha256'],self.sha)
        lease.close();self.assertTrue(self.proc.terminated)
        self.assertFalse(self.check(lease))
        with self.assertRaises(ValueError):lease.start()

    def test_wrong_hash_or_non_echo_target_never_starts(self):
        with self.assertRaisesRegex(ValueError,'hash'):
            launch.GatewayLease(self.exe,'00'*32,host='127.0.0.1',slot=0,serial='601FC87B',root='Press',directory=self.folder)
        for changed in (dict(host='192.0.2.1'),dict(slot=1),dict(serial='7036B510'),dict(root='Other')):
            with self.subTest(changed=changed),self.assertRaises(ValueError):self.make(**changed)
        self.assertEqual(self.spawns,[])

    def test_other_listener_or_policy_revokes_the_binding(self):
        lease=self.make().start()
        original=dict(self.reply)
        for change in (dict(instance='other'),dict(plcReady=False),dict(status='degraded'),
                       dict(writeAccess=dict(enabled=True,roots=['Other'],allRootMailboxes=False)),
                       dict(writeAccess=dict(enabled=True,roots=['Press'],allRootMailboxes=True))):
            self.reply={**original,**change}
            with self.subTest(change=change):self.assertFalse(self.check(lease))
        self.reply=original;self.assertTrue(self.check(lease))
        self.proc.code=1;self.assertFalse(self.check(lease))

    def test_wrong_serial_root_or_url_is_not_the_owned_target(self):
        lease=self.make().start()
        for change in (dict(serial='12345678'),dict(root='Other'),dict(url=lease.url+'/other')):
            args=dict(serial='601FC87B',root='Press',url=lease.url);args.update(change)
            with self.subTest(change=change):self.assertFalse(lease.guard(**args))

    def test_read_only_lease_has_no_write_root_and_requires_read_only_policy(self):
        lease=self.make(read_only=True).start()
        self.assertNotIn('--write-root',lease.arguments)
        self.assertTrue(self.check(lease))
        self.reply['writeAccess']['enabled']=True
        self.assertFalse(self.check(lease))

    def test_failed_start_is_closed_and_never_restarted(self):
        lease=self.make();self.reply['instance']='wrong'
        with self.assertRaises(TimeoutError):lease.start(timeout=.1)
        self.assertTrue(self.proc.terminated)
        self.assertEqual(len(self.spawns),1)
        with self.assertRaises(ValueError):lease.start()

    def test_a_package_changed_after_preparation_never_starts(self):
        lease=self.make()
        self.exe.write_bytes(b'different package')
        with self.assertRaisesRegex(ValueError,'changed before startup'):lease.start()
        self.assertEqual(self.spawns,[])

    def test_exited_process_cannot_pass_an_old_ready_response(self):
        lease=self.make();self.proc.code=1
        with self.assertRaises(RuntimeError):lease.start()
        self.assertFalse(self.check(lease))

    def test_binding_is_prepared_explicitly_and_closes_with_the_native_context(self):
        native=NS(IPAddress='127.0.0.1',ProcessorSlot=0,Close=lambda:None)
        session=NS(expected_serial='601FC87B',root='Press')
        with patch.dict(launch.os.environ,{},clear=True),self.assertRaises(ValueError):launch.bind(native,session)
        native._fraktal_gateway_executable=str(self.exe);native._fraktal_gateway_sha256=self.sha
        native._fraktal_gateway_directory=self.folder
        lease=self.make().start()
        with patch.object(launch,'GatewayLease',return_value=lease):
            # A fresh construction's start is the lifecycle boundary, mocked
            # here because this lease already owns its fake process.
            with patch.object(lease,'start',return_value=lease):launch.bind(native,session)
        self.assertEqual(native._fraktal_gateway_url,lease.url)
        native.Close();self.assertTrue(self.proc.terminated)

    def test_the_actual_pylogix_context_exit_closes_the_lease(self):
        # No controller connection: exercise the installed driver's lifecycle,
        # whose __exit__ bypasses its public Close method.
        from pylogix import PLC
        lease=self.make().start()
        session=NS(expected_serial='601FC87B',root='Press')
        with PLC('127.0.0.1') as native:
            # The unconnected driver's initial socket also needs closing;
            # its close routine only closes a registered connection.
            self.addCleanup(native.conn.Socket.close)
            self.addCleanup(native.conn.msg_socket.close)
            state=launch.connection_state(native)
            state._fraktal_gateway_executable=str(self.exe)
            state._fraktal_gateway_sha256=self.sha
            state._fraktal_gateway_directory=self.folder
            with patch.object(launch,'GatewayLease',return_value=lease),patch.object(lease,'start',return_value=lease):
                launch.bind(native,session)
            self.assertFalse(self.proc.terminated)
        self.assertTrue(self.proc.terminated)


if __name__=='__main__':unittest.main()
