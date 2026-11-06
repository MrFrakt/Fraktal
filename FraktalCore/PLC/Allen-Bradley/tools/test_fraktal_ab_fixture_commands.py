"""C5 apparatus commands use the operator path and independently observe CIP."""
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import fraktal_ab_fixture_reads as fixture
import fraktal_ab_harness_commands as gateway
import fraktal_ab_press_s6_collapse_echo38 as profile
import fraktal_ab_press_execute as px
import fraktal_ab_mailbox as mailbox

APP=profile.application()


class Rows:
    def __init__(self):
        self.sequence=self.ack=40;self.accepted=False;self.key=0;self.calls=[]
    def read_row(self,paths,private):
        self.calls.append((paths,private))
        values=(self.sequence,self.ack,self.accepted,'fixture.refused' if self.key else '')
        return dict(values=dict(zip(paths,values)),private={next(iter(private)):{'Mailbox_DiagnosticKey':self.key}})


class Comm:
    def __init__(self,rows):
        self.properties=0;self.serial=0x601fc87b;self.writes=[]
        self._fraktal_gateway_guard=lambda **target: target==dict(serial='601FC87B',root='Press',url=fixture.DEFAULT_GATEWAY)
        self._fraktal_fixture_reads=fixture.FixtureReads(APP,rows,expected_serial='601FC87B')
    def GetDeviceProperties(self):
        self.properties+=1
        return NS(Status='Success',Value=NS(SerialNumber=hex(self.serial)))
    def Write(self,*args):
        self.writes.append(args)
        raise AssertionError('operator request must not use native CIP Write')


class Client:
    def __init__(self,rows,*,ok=True,answer=True,fail=False):
        self.rows,self.ok,self.answer,self.fail=rows,ok,answer,fail
        self.calls=[];self.closed=False
    def write_batch(self,root,sequence,**arguments):
        self.calls.append((root,sequence,arguments))
        if self.fail:raise gateway.GatewayCommandUnavailable('outcome unknown')
        if self.ok:
            self.rows.sequence=self.rows.ack=sequence
            self.rows.accepted=self.answer;self.rows.key=0 if self.answer else 77
        return gateway.BatchReply(self.ok,True if self.ok else None,None if self.ok else 'refused')
    def close(self):self.closed=True


class Commands(unittest.TestCase):
    def setUp(self):
        self.rows=Rows();self.comm=Comm(self.rows)
    def run_command(self,client,**arguments):
        with patch.object(gateway,'GatewayCommands',return_value=client) as factory:
            value=fixture.command(self.comm,mailbox.START,app=APP,settle=1,**arguments)
        self.assertEqual(factory.call_args.args,(fixture.DEFAULT_GATEWAY,))
        return value

    def test_gateway_writes_once_cip_observes_ack_and_exact_numeric_key(self):
        client=Client(self.rows,answer=False)
        value=self.run_command(client)
        self.assertEqual(value,dict(sequence=41,accepted=False,diagnosticKey=77))
        self.assertEqual(client.calls,[('Press',41,dict(Kind=mailbox.START))])
        self.assertEqual(len(self.rows.calls),2)
        self.assertEqual(self.rows.calls[-1][1],{'FRK_Press_FixtureObservation':('Mailbox_DiagnosticKey',)})
        self.assertTrue(client.closed);self.assertEqual(self.comm.writes,[])
        self.assertEqual(self.comm.properties,1)

    def test_changed_serial_refuses_before_gateway_or_control_reads(self):
        self.comm.serial=0x1234
        with patch.object(gateway,'GatewayCommands') as factory,self.assertRaisesRegex(ValueError,'identity changed'):
            fixture.command(self.comm,mailbox.START,app=APP,settle=1)
        factory.assert_not_called();self.assertEqual(self.rows.calls,[])

    def test_missing_mailbox_accounting_refuses_without_a_request(self):
        self.comm._fraktal_fixture_reads.fields.pop('Mailbox')
        with patch.object(gateway,'GatewayCommands') as factory,self.assertRaises(ValueError):
            fixture.command(self.comm,mailbox.START,app=APP,settle=1)
        factory.assert_not_called();self.assertEqual(self.rows.calls,[])

    def test_missing_or_mismatched_gateway_target_binding_refuses_before_a_request(self):
        for guard in (None,lambda **target:False):
            self.comm._fraktal_gateway_guard=guard
            with patch.object(gateway,'GatewayCommands') as factory,self.assertRaisesRegex(ValueError,'target binding'):
                fixture.command(self.comm,mailbox.START,app=APP,settle=1)
            factory.assert_not_called()
        self.assertEqual(self.rows.calls,[])

    def test_unsettled_previous_ack_never_sends_a_batch(self):
        self.rows.ack=39;client=Client(self.rows)
        with self.assertRaisesRegex(AssertionError,'settled'):
            self.run_command(client)
        self.assertEqual(client.calls,[]);self.assertTrue(client.closed)

    def test_gateway_refusal_has_no_native_fallback_or_retry(self):
        client=Client(self.rows,ok=False)
        with self.assertRaisesRegex(AssertionError,'gateway refused'):
            self.run_command(client)
        self.assertEqual(len(client.calls),1);self.assertEqual(self.comm.writes,[])
        self.assertTrue(client.closed)

    def test_unknown_transport_outcome_closes_without_a_second_request(self):
        client=Client(self.rows,fail=True)
        with self.assertRaises(gateway.GatewayCommandUnavailable):self.run_command(client)
        self.assertEqual(len(client.calls),1);self.assertTrue(client.closed)
        self.assertEqual(self.comm.writes,[])

    def test_only_boolean_zero_one_are_adapted_to_the_core_type(self):
        client=Client(self.rows)
        self.run_command(client,BoolValue=1)
        self.assertIs(client.calls[0][2]['BoolValue'],True)
        for value in (2,-1,1.0):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.run_command(Client(self.rows),BoolValue=value)
        self.assertEqual(self.comm.properties,1)

    def test_manual_uses_identity_and_catalogue_command_without_native_ordinal(self):
        with patch.object(px,'APP',APP),patch.object(px,'command',return_value={'accepted':True}) as command:
            px.manual(self.comm,'Door',2)
        self.assertEqual(command.call_args.kwargs,dict(settle=2.0,TargetPath='Press.Door',IntValue=2))

    def test_px_command_delegates_only_for_the_collapsed_profile(self):
        with patch.object(px,'APP',APP),patch.object(fixture,'command',return_value={'accepted':True}) as command:
            self.assertEqual(px.command(self.comm,mailbox.START),{'accepted':True})
        command.assert_called_once_with(self.comm,mailbox.START,app=APP,settle=2.0)

    def test_reader_binding_uses_the_actual_slotted_plc_connection(self):
        from pylogix import PLC
        with PLC('127.0.0.1') as native:
            self.addCleanup(native.conn.Socket.close)
            self.addCleanup(native.conn.msg_socket.close)
            with patch.object(fixture,'open_row_reader',return_value=self.rows):
                session=fixture.bind(native,APP,'601FC87B')
            self.assertIs(fixture._session(native,APP),session)
            self.assertIs(fixture._session(NS(comm=native),APP),session)
            self.assertFalse(hasattr(native,'_fraktal_fixture_reads'))


if __name__=='__main__':unittest.main()
