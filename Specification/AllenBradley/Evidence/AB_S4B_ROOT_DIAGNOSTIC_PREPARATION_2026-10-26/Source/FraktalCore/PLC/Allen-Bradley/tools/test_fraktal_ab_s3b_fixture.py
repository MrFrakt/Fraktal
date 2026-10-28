"""S3b observations add reads; inherited writes and cleanup stay authoritative."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch

import fraktal_ab_s3b_fixture_execute as fixture


class ConditionFixtureTests(unittest.TestCase):
    def runner(self,path):
        cls=fixture.paired_run(path)
        run=object.__new__(cls)
        run.app=SimpleNamespace(name='Press')
        run.comm=SimpleNamespace(Read=lambda tag:SimpleNamespace(Status='Success',Value=1))
        run.evidence={}
        return run

    def test_condition_pair_precedes_the_original_release_write(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'fixture.json');events=[]
            report=dict(passed=True,pair=dict(canonical=dict(values={
                'Press/PressRam/Status/Diagnostic/ReasonCode':1,
                'Press/PressRam/Status/Diagnostic/Since':'1998-01-01T00:00:00.000Z'})))
            with patch.object(fixture.execute,'read_module',return_value=dict(OutImm_Reason=1,OutImm_Held=1)), \
                 patch.object(fixture,'capture_gate',side_effect=lambda comm:events.append('pair') or report), \
                 patch.object(fixture.genealogy.GenealogyRun,'set',side_effect=lambda *args:events.append('write')):
                run.set(fixture.execute.HOLD['PressRam'],0)
            self.assertEqual(events,['pair','write'])
            self.assertEqual(run.evidence['s3bConditionPairs'][0]['languageOrdinal'],1)

    def test_failed_observation_blocks_release_but_not_parent_cleanup(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'fixture.json')
            with patch.object(fixture.execute,'read_module',return_value=dict(OutImm_Reason=1,OutImm_Held=1)), \
                 patch.object(fixture,'capture_gate',side_effect=ValueError('unstable scan')) as capture, \
                 patch.object(fixture.genealogy.GenealogyRun,'set') as write:
                with self.assertRaisesRegex(RuntimeError,'equivalence failed'):
                    run.set(fixture.execute.HOLD['PressRam'],0)
                write.assert_not_called()
                run.evidence['error']='parent recorded the failed observation'
                run.set(fixture.execute.HOLD['PressRam'],0)
                write.assert_called_once()
                capture.assert_called_once()
            self.assertEqual(len(list(Path(directory).glob('*.json.gz'))),1)

    def test_unobserved_inputs_use_only_the_original_write(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'fixture.json')
            with patch.object(fixture,'capture_gate') as capture, \
                 patch.object(fixture.genealogy.GenealogyRun,'set') as write:
                run.set('an_existing_fixture_input',1)
                write.assert_called_once_with('an_existing_fixture_input',1)
                capture.assert_not_called()

    def test_observer_does_not_change_the_mailbox_connection(self):
        writer=SimpleNamespace(IPAddress='127.0.0.1',ProcessorSlot=0,ConnectionSize=500)
        context=MagicMock();observer=context.__enter__.return_value
        with patch('pylogix.PLC',return_value=context) as connect, \
             patch.object(fixture.equivalence,'run',return_value={'passed':True}) as gate:
            report=fixture.capture_gate(writer)
            self.assertTrue(report['passed'])
            self.assertEqual(report['fixtureObserver'],dict(independent=True,
                writerConnectionBytes=500,readConnectionBytes=4000))
        connect.assert_called_once_with('127.0.0.1')
        gate.assert_called_once_with(observer)
        self.assertEqual((observer.ProcessorSlot,observer.ConnectionSize,observer.SocketTimeout),(0,4000,5))
        self.assertEqual(writer.ConnectionSize,500)
        context.__exit__.assert_called_once()

    def test_adopted_fault_uses_the_units_latched_first_out(self):
        with TemporaryDirectory() as directory:
            run=self.runner(Path(directory)/'fixture.json');events=[]
            report=dict(passed=True,pair=dict(canonical=dict(values={
                'Press/Status/Diagnostic/ReasonCode':2001,
                'Press/Status/Diagnostic/Since':'1998-01-01T00:00:00.000Z'})))
            with patch.object(fixture.execute,'read_unit',return_value=dict(Error=1,DiagReason=2001)), \
                 patch.object(fixture.execute,'read_module') as child, \
                 patch.object(fixture,'capture_gate',side_effect=lambda comm:events.append('pair') or report), \
                 patch.object(fixture.genealogy.GenealogyRun,'set',side_effect=lambda *args:events.append('write')):
                run.set(fixture.execute.FAULT['PartSlide'],0)
            child.assert_not_called()
            self.assertEqual(events,['pair','write'])
            pair=run.evidence['s3bConditionPairs'][0]
            self.assertEqual((pair['kind'],pair['module'],pair['diagnosticPath']),
                             ('fault','PartSlide','Press/Status/Diagnostic/'))

    def test_observer_closes_after_failed_acquisition(self):
        writer=SimpleNamespace(IPAddress='127.0.0.1',ProcessorSlot=0,ConnectionSize=500)
        context=MagicMock()
        with patch('pylogix.PLC',return_value=context), \
             patch.object(fixture.equivalence,'run',side_effect=ValueError('unstable scan')):
            with self.assertRaisesRegex(ValueError,'unstable scan'):fixture.capture_gate(writer)
        context.__exit__.assert_called_once()
        self.assertEqual(writer.ConnectionSize,500)

    def test_observer_refuses_another_target_before_connecting(self):
        for address,slot in (('127.0.0.2',0),('127.0.0.1',1)):
            with self.subTest(address=address,slot=slot),patch('pylogix.PLC') as connect:
                with self.assertRaisesRegex(ValueError,'fixed local Echo'):
                    fixture.capture_gate(SimpleNamespace(IPAddress=address,ProcessorSlot=slot))
                connect.assert_not_called()


if __name__=='__main__':unittest.main()
