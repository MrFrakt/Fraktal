"""Session-only transient Access proof; no writes or credential-bearing reads.

Warm the two public scalar paths before the first login. After its existing
acknowledgement, compare canonical BOOL and legacy DINT within the existing
entire-scan guard. The inherited full comparison follows, at its actual later
state; it is never substituted by this one-path witness.
"""
from pathlib import Path
import json

import fraktal_ab_access as access
import fraktal_ab_canonical_publication as publication
from fraktal_ab_canonical_equivalence import stable_scan_pair
from fraktal_ab_canonical_reader import snapshot


class BusyWitness:
    def __init__(self, comm, app, seed):
        self.comm = comm
        self.path = app.name+'/Access/LoginBusy'
        if snapshot(seed)['types'].get(self.path) != 'Boolean':
            raise ValueError('busy witness requires the published Boolean type')
        self.generation_tag = publication.generation_tag(app)
        self.tags = (app.name+'.Access.LoginBusy', access.tag(app, 'State')+'.LoginBusy')
        self.manifest_hash = seed['manifest']['contentHash']
        # Cache native scalar types before any login request. These samples
        # supply neither accepted values nor a same-state proof.
        warmed_generation=self.generation()
        if type(warmed_generation) is not int or not 1 <= warmed_generation <= 2147483646:
            raise ValueError('busy witness requires an initialized scan generation')
        self.body()

    def generation(self):
        response = self.comm.Read(self.generation_tag)
        if response.Status != 'Success':
            raise ValueError('busy witness generation read refused')
        return response.Value

    def body(self):
        replies = self.comm.Read(list(self.tags))
        if not isinstance(replies, list) or len(replies) != 2:
            raise ValueError('busy witness requires exactly two scalar replies')
        if any(reply.Status != 'Success' for reply in replies):
            raise ValueError('busy witness scalar read refused')
        canonical, legacy = (reply.Value for reply in replies)
        if type(canonical) not in (bool, int) or canonical not in (0, 1):
            raise ValueError('busy witness canonical BOOL is invalid')
        if type(legacy) is not int or legacy not in (0, 1):
            raise ValueError('busy witness legacy DINT is invalid')
        return dict(rawReads=[dict(tag=tag,status=reply.Status,value=reply.Value)
            for tag,reply in zip(self.tags,replies,strict=True)])

    def capture(self, destination):
        destination = Path(destination)
        if destination.exists():
            raise ValueError('refusing existing busy witness output')
        try:
            pair = stable_scan_pair(self.generation, self.body, fresh_start=True)
            canonical, legacy = (row['value'] for row in pair['rawReads'])
            equal = bool(canonical) == bool(legacy)
            pair.update(canonical=dict(values={self.path:bool(canonical)},types={self.path:'Boolean'}),
                projection=dict(values={self.path:bool(legacy)},types={self.path:'Boolean'}))
            report = dict(passed=equal and bool(canonical),readOnly=True,scope='transient Access/LoginBusy only',
                fullComparison=False,manifestHash=self.manifest_hash,pair=pair,
                valueEquivalent=equal,busyObserved=bool(canonical),
                error=None if equal and canonical else 'paired busy state was not observed')
        except Exception as error:
            report = dict(passed=False,readOnly=True,scope='transient Access/LoginBusy only',
                fullComparison=False,error=str(error),attempts=getattr(error,'attempts',[]))
        with destination.open('x',encoding='utf-8',newline='') as stream:
            json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
        if not report['passed']:
            raise ValueError(report['error'])
        return report


def with_busy_witness(parent, destination):
    """Keep the inherited writer/cases/restoration and every full pair intact."""
    destination = Path(destination)
    class TransientAccessRun(parent):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self._busy_witness = BusyWitness(self.comm,self.app,self.provider_capture)

        def access_pair(self,phase):
            if phase != 'login_busy':
                return super().access_pair(phase)
            output=destination.with_name(destination.stem+'_login_busy_witness.json')
            witness=self._busy_witness.capture(output)
            self.evidence['loginBusyWitness']=dict(output=str(output),passed=True,
                paths=1,sameScanVerified=True,fullComparison=False)
            # The full capture retains its actual later values and raw frames.
            # A failure still propagates; the witness cannot replace that gate.
            super().access_pair('after_login_busy_witness')
            return witness
    return TransientAccessRun
