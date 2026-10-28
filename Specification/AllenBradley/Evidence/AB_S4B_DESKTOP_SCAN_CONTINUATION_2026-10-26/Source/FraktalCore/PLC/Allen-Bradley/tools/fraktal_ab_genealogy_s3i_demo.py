"""S3i genealogy reference: canonical Line/shift, migration frame enabled."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy


def application():
    return replace(genealogy.application(),canonical_publication_stage=11,canonical_observation_period_ms=50)
