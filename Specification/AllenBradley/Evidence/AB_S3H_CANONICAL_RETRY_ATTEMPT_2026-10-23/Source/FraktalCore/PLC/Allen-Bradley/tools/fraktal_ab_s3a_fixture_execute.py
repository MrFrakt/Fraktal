"""Existing 31-row genealogy fixture, adding read-only S3a pairs before decision answers.

The inherited fixture owns every tag write and cleanup. This adds no command,
simulation stimulus, credential surface or regression row. Exact arming,
identity, manifest, active-session and new-output guards remain inherited.
"""
import gzip
import json

import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_mailbox as mailbox
import fraktal_ab_s3a_equivalence as equivalence


def capture_pair(run,destination,gate,*,key='s3aDecisionPairs',kind='decision',prompt=False,metadata=None):
    pairs=run.evidence.setdefault(key,[])
    output=destination.with_name(destination.stem+f'_{kind}_{len(pairs)+1:02}.json.gz')
    run.check(not output.exists(),'refusing existing paired output')
    try:
        report=gate(run.comm)
    except Exception as error:
        report=dict(passed=False,readOnly=True,error=str(error),attempts=getattr(error,'attempts',[]))
    with gzip.open(output,'xt',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
    pairs.append(dict(output=str(output),passed=report['passed'],**(metadata or {})))
    run.check(report['passed'],kind+' equivalence failed')
    if prompt:
        run.check(bool(report['pair']['canonical']['values'][run.app.name+'/Decision/Prompt']),
                  'decision capture requires an active prompt')
    return report


def paired_run(destination,*,gate=None,key='s3aDecisionPairs'):
    class PairedRun(genealogy.GenealogyRun):
        def command(self, kind, **arguments):
            if kind == mailbox.DECISION_ANSWER:
                capture_pair(self,destination,gate or equivalence.run,key=key,prompt=True)
            return super().command(kind,**arguments)
    return PairedRun


def main(argv=None):
    return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3a-genealogy-fixture')


if __name__=='__main__':raise SystemExit(main())
