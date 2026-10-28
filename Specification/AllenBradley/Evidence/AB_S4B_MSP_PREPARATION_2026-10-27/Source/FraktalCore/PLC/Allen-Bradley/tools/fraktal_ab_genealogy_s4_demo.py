"""S4 engineering profile: the accepted S3k values plus V6.7 guard bindings."""
from dataclasses import replace
import fraktal_ab_genealogy_s3k_demo as previous


def application():
    return replace(previous.application(), canonical_read_coherence=True)
