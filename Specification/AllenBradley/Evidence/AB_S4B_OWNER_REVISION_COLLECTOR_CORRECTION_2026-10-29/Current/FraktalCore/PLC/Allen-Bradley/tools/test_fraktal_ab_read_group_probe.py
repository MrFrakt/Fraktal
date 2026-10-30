"""Qualification accepts only bounded, live, native groups with declared guards."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from fraktal_ab_read_group_probe import guarded_read, plan_groups


def capture():
    def member(name,code,offset=0,info=0):return dict(name=name,code=code,offset=offset,info=info)
    def template(handle,size,members):return dict(handle=handle,byteSize=size,members=members)
    return dict(manifest=dict(schemaMinor=7,
        dataProducts=[dict(CanonicalRoot='Fieldbus/Topology',SourceSymbol='NativeProduct')],
        readCoherenceBindings=[dict(CanonicalPrefix=p,RevisionSymbol='PublishedGuard',Protocol=1,MutationPeriodUs=10000)
                               for p in ('Unit','Fieldbus/Topology')]),
        templates=[template(1,64,[member('Value',0xc4)]),
                   template(2,64,[member('Status',0x8001)]),
                   template(3,128,[member('Status',0x8001),member('Child',0x8002,64)]),
                   template(4,128,[member('Rows',0xa001,info=2)])],
        symbols=[dict(name='Unit',handle=3,arrayRank=0),dict(name='NativeProduct',handle=4,arrayRank=0),
                 dict(name='PublishedGuard',atomic=0xc4,arrayRank=0)])


class Communication:
    def __init__(self,values,clock=None):
        self.values=iter(values);self.SocketTimeout=5;self.reads=[];self.closed=False;self.clock=clock
        self.conn=SimpleNamespace(SocketConnected=True,Socket=Mock())
    def Read(self,symbol):
        self.reads.append(symbol)
        value=next(self.values)
        if self.clock is not None:self.clock[0]+=.0001
        if isinstance(value,Exception):raise value
        return SimpleNamespace(Status='Success',Value=value)
    def Close(self):self.closed=True;self.conn.SocketConnected=False


class GroupProbeTests(unittest.TestCase):
    def setUp(self):
        self.capture=capture();self.groups=plan_groups(self.capture)
        self.group=self.groups[0]

    def read(self,values,**kwargs):
        comm=Communication(values)
        result=guarded_read(comm,self.group,self.capture['templates'],clock=lambda:0,**kwargs)
        self.assertEqual(comm.SocketTimeout,5)
        return result,comm

    def test_template_plan_covers_modules_and_product_without_name_conventions(self):
        self.assertEqual([g['symbol'] for g in self.groups],['Unit.Status','Unit.Child.Status','NativeProduct'])
        self.assertEqual({g['binding']['CanonicalPrefix'] for g in self.groups},{'Unit','Fieldbus/Topology'})
        # Force descent into an actual array element, using Template array metadata.
        modified=deepcopy(self.capture);modified['templates'][-1]['byteSize']=4096
        self.assertEqual(plan_groups(modified)[-1]['symbol'],'NativeProduct.Rows[0]')

    def test_missing_coverage_bad_counter_type_old_manifest_and_oversize_refuse(self):
        for change in ('coverage','type','old','oversize'):
            bad=deepcopy(self.capture)
            if change=='coverage':bad['manifest']['readCoherenceBindings'].pop()
            if change=='type':bad['symbols'][-1]['atomic']=0xc5
            if change=='old':bad['manifest']['schemaMinor']=6
            if change=='oversize':bad['templates'][0]['byteSize']=4096
            with self.subTest(change=change),self.assertRaises(ValueError):plan_groups(bad)

    def test_good_exact_group_with_published_revision_and_restored_socket_budget(self):
        result,comm=self.read([2,bytes(64),2])
        self.assertEqual(result['quality'],'GOOD');self.assertEqual(result['rawHex'],bytes(64).hex())
        self.assertEqual(comm.reads,['PublishedGuard','Unit.Status','PublishedGuard'])
        self.assertFalse(comm.closed);comm.conn.Socket.settimeout.assert_called_with(5)

    def test_odd_zero_and_torn_reads_never_escape_as_good(self):
        result,comm=self.read([0,3,4,bytes(64),6])
        self.assertEqual(result['quality'],'UNCERTAIN');self.assertIsNone(result['rawHex'])
        self.assertEqual(result['attempts'],3);self.assertFalse(comm.closed)
        result,_=self.read([3,4,bytes(64),4])
        self.assertEqual(result['quality'],'GOOD');self.assertEqual(result['attempts'],2)

    def test_first_counter_latency_counts_and_late_groups_have_no_bytes(self):
        now=[0.0];comm=Communication([2,bytes(64),2]*3,now)
        self.group['binding']['MutationPeriodUs']=250
        result=guarded_read(comm,self.group,self.capture['templates'],clock=lambda:now[0])
        self.assertEqual(result['quality'],'UNCERTAIN')
        self.assertEqual(result['reason'],'window-exceeds-publication-interval');self.assertIsNone(result['rawHex'])

    def test_deadline_invalid_counter_transport_or_layout_stops_connection(self):
        for values in ([True],[-2],[2147483647],[2,bytes(63),2],[OSError('lost')]):
            result,comm=self.read(values)
            self.assertEqual(result['quality'],'BAD');self.assertIsNone(result['rawHex']);self.assertTrue(comm.closed)
        now=[0.0];comm=Communication([2,bytes(64),2],now)
        result=guarded_read(comm,self.group,self.capture['templates'],clock=lambda:now[0],timeout=.00015)
        self.assertEqual(result['reason'],'read-timeout');self.assertIsNone(result['rawHex']);self.assertTrue(comm.closed)
        self.assertEqual(comm.reads,['PublishedGuard','Unit.Status'])

    def test_bad_budgets_fail_before_access(self):
        for kw in (dict(attempts=0),dict(attempts=True),dict(attempts=101),dict(timeout=0),dict(timeout=6)):
            comm=Communication([])
            with self.subTest(kw=kw),self.assertRaises(ValueError):guarded_read(comm,self.group,self.capture['templates'],**kw)
            self.assertEqual(comm.reads,[])


if __name__=='__main__':unittest.main()
