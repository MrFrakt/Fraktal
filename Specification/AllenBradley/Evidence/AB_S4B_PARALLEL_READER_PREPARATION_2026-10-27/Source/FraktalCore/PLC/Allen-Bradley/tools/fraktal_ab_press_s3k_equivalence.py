"""Read-only S3k equivalence of the press declaration on Echo (the S3 exit candidate).

The accepted S3k gate, with the press candidate and its three-rendition legacy
oracle in place of the genealogy fixture. The oracle declaration is pinned before
any legacy module binds its APP singleton.
"""
import os

ORACLE = 'fraktal_ab_press_rendition_echo38'


def run(comm, **state):
    import fraktal_ab_press_canonical_echo38 as candidate
    import fraktal_ab_s3k_equivalence as s3k
    return s3k.run(comm, candidate_factory=candidate.application, oracle_declaration=ORACLE, **state)


def main():
    os.environ['FRAKTAL_AB_DECLARATION'] = ORACLE
    import fraktal_ab_s2_equivalence as shared
    return shared.main(run, description=__doc__)


if __name__ == '__main__': raise SystemExit(main())
