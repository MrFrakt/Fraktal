"""Read-only S9 cost measurement for the selected, serial-guarded station.

Measure the production reader's cold/steady manifest cost, native tier caching,
targeted promotion and six viewers sharing one supervised gateway. No listener,
write roots, tag writes or state changes. Budgets are declared from measured
cost afterward; this report alone never grants a write-enabled claim.
"""
import argparse
import asyncio
import json
import statistics
import time

import fraktal_ab_gateway as gw
import fraktal_ab_projection as projection
from fraktal_ab_s16_execute import _normalize_serial


class Reads:
    def __init__(self, comm):
        self.comm, self.calls = comm, []

    def __getattr__(self, name):
        return getattr(self.comm, name)

    def Read(self, *args, **kwargs):
        self.calls.append(args[0])
        return self.comm.Read(*args, **kwargs)


async def measure(comm, cycles):
    counted = Reads(comm)
    plan = projection.ReadPlan()
    def read():
        return projection.read_document(counted, plan=plan)
    read.set_tiers, read.targeted = plan.set_tiers, plan.targeted
    read.mailbox = lambda: projection.read_mailbox_document(counted, plan)
    read.mailbox_paths = frozenset(f'{projection.APP.name}/{leaf}'
                                 for leaf in projection.MAILBOX_CONTROL_LEAVES)
    read.budget = projection.APP.read_budget
    station = gw.Station(read, cache_ttl=.1)
    gateway = gw.Gateway(station)  # read-only, never listening
    rows = []

    async def sample(label, operation):
        count, started = len(counted.calls), time.perf_counter()
        result = await operation()
        rows.append(dict(case=label, elapsedMs=round((time.perf_counter()-started)*1000, 3),
                         nativeReadCalls=len(counted.calls)-count,
                         healthy=station.healthy))
        return result

    first = gw._ConnState()
    await sample('cold', lambda: gateway._snapshot(first))
    if read.mailbox_paths <= set(station.paths):
        ack_indices = [station.paths.index(f'{projection.APP.name}/HmiResponse/{leaf}')
                       for leaf in ('AckSequence', 'Accepted', 'Diagnostic')]
        for _ in range(cycles):
            await sample('mailbox-preflight', station.mailbox_document)
            await sample('mailbox-ack', lambda: gateway._read_values(first,
                dict(revision=station.revision, indices=ack_indices)))
    for _ in range(cycles):
        await sample('steady', lambda: station.document(force=True))
    prefix = projection.APP.name + '/Profiler/'
    excluded = [i for i, path in enumerate(station.paths) if path.startswith(prefix)]
    await gateway._set_read_tiers(first, dict(revision=station.revision, excluded=excluded))
    for _ in range(cycles):
        await sample('profiler-excluded', lambda: station.document(force=True))
    if excluded:
        await sample('profiler-targeted', lambda: gateway._read_values(first, dict(revision=station.revision, indices=[excluded[0]])))
    await gateway._set_read_tiers(first, dict(revision=station.revision, slow=excluded))
    for _ in range(cycles):
        await sample('profiler-slow', lambda: station.document(force=True))
    viewers = [gw._ConnState() for _ in range(6)]
    for viewer in viewers:
        await gateway._snapshot(viewer)  # every unconfigured viewer needs fast
    for _ in range(cycles):
        station._doc = None
        await sample('six-viewer-burst', lambda: asyncio.gather(*(gateway._snapshot(v) for v in viewers)))
    summary = {}
    for name in dict.fromkeys(row['case'] for row in rows):
        selected = [r for r in rows if r['case'] == name]
        summary[name] = dict(medianMs=statistics.median(r['elapsedMs'] for r in selected),
                             maximumMs=max(r['elapsedMs'] for r in selected),
                             nativeReadCalls=[r['nativeReadCalls'] for r in selected])
    budget = projection.APP.read_budget
    fits = (budget is None or (summary['steady']['maximumMs'] < budget.poll_period_ms
            and summary['cold']['maximumMs'] * 2 < budget.fast_good_ms
            and summary['six-viewer-burst']['maximumMs'] < budget.poll_period_ms))
    return dict(schema='fraktal.ab.s9-read-cost', schemaVersion=1, wrote=False,
                writeEnabledClaim=False, expectedContentHash=projection.manifest.content_hash(projection.APP),
                discoveryRevision=station.revision, paths=len(station.paths), rows=rows,
                budget=budget.wire() if budget else None, budgetFitsMeasuredCost=fits,
                summary=summary, passed=fits and all(r['healthy'] for r in rows))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target')
    parser.add_argument('--expect-serial', required=True, type=_normalize_serial)
    parser.add_argument('--cycles', type=int, default=5)
    args = parser.parse_args(argv)
    if not 1 <= args.cycles <= 10:
        parser.error('cycles must be 1..10')
    from pylogix import PLC
    with PLC() as comm:
        connection = projection.APP.read_budget.connection_bytes if projection.APP.read_budget else 4000
        comm.IPAddress, comm.ProcessorSlot, comm.ConnectionSize = args.target, 0, connection
        _serial, matches = projection.verify_serial(comm, args.expect_serial)
        if not matches:
            raise ValueError('controller serial mismatch; no reads of station data')
        result = asyncio.run(measure(comm, args.cycles))
        result.update(target=args.target, serial=args.expect_serial, connectionBytes=connection)
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
