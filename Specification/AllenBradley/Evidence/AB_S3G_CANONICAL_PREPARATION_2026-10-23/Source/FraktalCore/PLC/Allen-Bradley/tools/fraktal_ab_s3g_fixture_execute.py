"""S3g guarded fixture; inherited writes, expanded read-only metric captures.

Current authorization must name this exact image and fixture. The independent
reference compares metrics in every inherited decision/held/fault/config pair.
No direct accounting/profiler writes are added by this observer.
"""
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_genealogy_s3g_demo as candidate
import fraktal_ab_s3g_equivalence as equivalence
import fraktal_ab_s3f_fixture_execute as previous
import fraktal_ab_s3g_native_checks as native


def paired_run(destination):
    parent=previous.paired_run(destination,candidate_factory=candidate.application,
        equivalence_gate=equivalence.run,prefix='s3g')
    class MetricsRun(parent):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.evidence['s3gNativeChecks']=native.read_results(self.comm)
    return MetricsRun


def main(argv=None):return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3g-genealogy-fixture')
if __name__=='__main__':raise SystemExit(main())
