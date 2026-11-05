"""S3i genealogy reference: canonical Line/shift, migration frame enabled."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy
import fraktal_ab_document_revision as document_revision


def application():
    return replace(genealogy.application(),canonical_publication_stage=11,canonical_observation_period_ms=50, config_predecessors=document_revision.recorded('fraktal_ab_genealogy_s3i_demo', '6F3F8CDA9A8F6B59'))
