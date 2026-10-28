"""S3k engineering fixture; native acceptance requires the complete stage gates.

The accepted genealogy simulation and sampled-word fixture are inherited.
Stage 13 selects the versioned report owner and table-driven mailbox routing.
"""
from dataclasses import replace
import fraktal_ab_genealogy_s3j_demo as previous


def application():
    return replace(previous.application(),canonical_publication_stage=13)
