"""S3i guarded fixture: inherited fixed writes and read-only Line captures."""
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_genealogy_s3i_demo as candidate
import fraktal_ab_s3i_equivalence as equivalence
import fraktal_ab_s3i_native_checks as native
import fraktal_ab_s3f_fixture_execute as previous


def paired_run(destination):
    parent=previous.paired_run(destination,candidate_factory=candidate.application,equivalence_gate=equivalence.run,prefix='s3i')
    class LineRun(parent):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.evidence['s3iNativeChecks']=native.read_results(self.comm)
    return LineRun


def main(argv=None):return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3i-genealogy-fixture')
if __name__=='__main__':raise SystemExit(main())
