"""Inherited 41-case apparatus and read-only S3j fieldbus observations.

The new sampled-word stimulus vectors have a separate explicit authorization
and exact-image guard. This inherited walk adds no new write vectors.
"""
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_genealogy_s3j_demo as candidate
import fraktal_ab_s3j_equivalence as equivalence
import fraktal_ab_s3f_fixture_execute as previous


def paired_run(destination):
    return previous.paired_run(destination,candidate_factory=candidate.application,equivalence_gate=equivalence.run,prefix='s3j')


def main(argv=None):return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3j-genealogy-fixture')
if __name__=='__main__':raise SystemExit(main())
