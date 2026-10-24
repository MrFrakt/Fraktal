"""Inherited 31-row fixture with read-only sequence/decision/held/fault pairs."""
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_s3a_fixture_execute as shared
import fraktal_ab_s3b_fixture_execute as previous
import fraktal_ab_s3c_equivalence as equivalence


def paired_run(destination):
    parent=previous.paired_run(destination,gate=equivalence.run,prefix='s3c')
    class SequenceRun(parent):
        def record(self,language,case,*args,**kwargs):
            row=super().record(language,case,*args,**kwargs)
            report=shared.capture_pair(self,destination,
                lambda writer:previous.capture_gate(writer,equivalence.run),
                key='s3cSequencePairs',kind='sequence',metadata=dict(language=language,case=case))
            values=report['pair']['canonical']['values'];root=self.app.name+'/'
            if case=='mode_change':
                self.check(values[root+'SequenceStepCount']==0,'mode change must clear the chart')
            if case in ('OK','handled_NOK','HELD_resume','single_reset_restart'):
                self.check(values[root+'SequenceStepCount']>0,'completed chain must retain discovered history')
                self.check(any(v for k,v in values.items() if k.startswith(root+'SequenceSteps[') and k.endswith('/Visited')),
                           'the PLC must retain visited rows')
            if case=='handled_NOK':
                self.check(values[root+'SequenceAnnotationCount']>0,'handled failure must retain its sparse note')
            return row
    return SequenceRun


def main(argv=None):
    return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3c-genealogy-fixture')


if __name__=='__main__':raise SystemExit(main())
