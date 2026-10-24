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


def paired_run(destination):
    class PairedRun(genealogy.GenealogyRun):
        def command(self, kind, **arguments):
            if kind == mailbox.DECISION_ANSWER:
                pairs=self.evidence.setdefault('s3aDecisionPairs',[])
                output=destination.with_name(destination.stem+f'_decision_{len(pairs)+1:02}.json.gz')
                self.check(not output.exists(),'refusing existing S3a pair output')
                try:
                    report=equivalence.run(self.comm)
                except Exception as error:
                    report=dict(passed=False,readOnly=True,error=str(error),attempts=getattr(error,'attempts',[]))
                with gzip.open(output,'xt',encoding='utf-8') as stream:
                    json.dump(report,stream,indent=2,allow_nan=False)
                pairs.append(dict(output=str(output),passed=report['passed']))
                self.check(report['passed'],'S3a active-decision equivalence failed')
                self.check(bool(report['pair']['canonical']['values'][self.app.name+'/Decision/Prompt']),
                           'S3a decision capture requires an active prompt')
            return super().command(kind,**arguments)
    return PairedRun


def main(argv=None):
    return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3a-genealogy-fixture')


if __name__=='__main__':raise SystemExit(main())
