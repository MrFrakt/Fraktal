"""Twenty fixed read-only MSPs on the pinned restored genealogy baseline.

This tests native packet support and timing only, not canonical coherence or
desktop acceptance. Every embedded service is asserted Read Tag before send.
"""
from pathlib import Path
import json
import statistics
import struct
import time
from pylogix import PLC

W=Path(__file__).parent
tags=('FRK_Press_HealthProbe.Samples','FRK_Press_HealthProbe.TaskLastScanUs','FRK_Press_HealthProbe.Samples')
destination=W/'read_msp_probe_01.json'
assert not destination.exists()
rows=[]
with PLC('127.0.0.1') as comm:
    comm.ProcessorSlot,comm.ConnectionSize,comm.SocketTimeout=0,4000,3
    device=comm.GetDeviceProperties()
    assert device.Status=='Success' and device.Value is not None
    assert (str(device.Value.SerialNumber).lower(),device.Value.ProductName,device.Value.Revision)==('0x601fc87b','Emulate 5580 Controller','38.11')
    for tag in dict.fromkeys(tags):
        response=comm.Read(tag)
        assert response.Status=='Success' and type(response.Value) is int
    services=[comm._add_read_service(comm._build_ioi(tag,0xc4),1) for tag in tags]
    assert all(service[0]==0x4c for service in services)
    header=comm._build_multi_service_header()
    assert header==b'\x0a\x02\x20\x02\x24\x01'
    offset=2+2*len(services);offsets=[]
    for service in services:
        offsets.append(offset);offset+=len(service)
    request=header+struct.pack('<H',len(services))+struct.pack('<3H',*offsets)+b''.join(services)
    assert len(request)<500
    for index in range(20):
        started=time.perf_counter_ns()
        status,raw=comm.conn.send(request)
        elapsed=(time.perf_counter_ns()-started)//1000
        assert status==0 and raw[46:50]==b'\x8a\x00\x00\x00'
        data=raw[50:]
        assert struct.unpack_from('<H',data)[0]==3
        positions=list(struct.unpack_from('<3H',data,2))
        assert positions[0]==8 and positions==sorted(set(positions)) and positions[-1]<len(data)
        values=[]
        for at,end in zip(positions,positions[1:]+[len(data)],strict=True):
            segment=data[at:end]
            assert len(segment)==10 and segment[:6]==b'\xcc\x00\x00\x00\xc4\x00'
            values.append(struct.unpack_from('<i',segment,6)[0])
        rows.append(dict(index=index,elapsedUs=elapsed,values=values,rawHex=raw.hex(),
            equalSampleCounter=values[0]==values[2]))
result=dict(passed=True,readOnly=True,serial='601FC87B',tags=tags,
    packets=20,embeddedReadServices=60,plcWrites=0,requestHex=request.hex(),rows=rows,
    elapsedUs=dict(minimum=min(r['elapsedUs'] for r in rows),median=statistics.median(r['elapsedUs'] for r in rows),
        maximum=max(r['elapsedUs'] for r in rows)),
    equalSampleCounterPackets=sum(r['equalSampleCounter'] for r in rows),
    canonicalCoherenceClaim=False,desktopAcceptanceClaim=False)
with destination.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('requestHex','rows')}))
