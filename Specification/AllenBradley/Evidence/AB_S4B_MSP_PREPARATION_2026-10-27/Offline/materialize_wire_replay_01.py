from pathlib import Path
W=Path(__file__).parent
source=Path('C:/work/fraktal-ab-s4b-refill-20261027/offline_01/wire_replay_benchmark_test.dart').read_text(encoding='utf-8')
old='show CaptureWire;'
assert source.count(old)==1
source=source.replace(old,"show CaptureWire;\nimport '../../fraktal-ab-s4b-20261025/hmi_verify_01/test/cip_read_batch_test.dart' show BatchCapture;")
source=source.replace('wire = CaptureWire(capture)','wire = BatchCapture(capture)')
source=source.replace('wire.reads.clear(); final previousGroups = plan.acquisitions.length;',
    'wire.reads.clear(); final previousGroups = plan.acquisitions.length;\n    final previousBatches=wire.batches,previousOrdinary=wire.ordinary;')
source=source.replace("'wireReads': wire.reads.length,",
    "'wireReads': wire.reads.length, 'batchPackets':wire.batches-previousBatches,\n      'ordinaryRequests':wire.ordinary-previousOrdinary,\n      'packetRequests':wire.batches-previousBatches+wire.ordinary-previousOrdinary,")
source=source.replace("expect(result['wireReads'], before['wireReads']);",
    "expect(result['packetRequests'] as int, lessThan(before['wireReads'] as int));")
with (W/'wire_replay_benchmark_test.dart').open('x',encoding='utf-8') as f:f.write(source)
print('Prepared batch-capable recorded-wire replay, retaining the independent oracle.')
