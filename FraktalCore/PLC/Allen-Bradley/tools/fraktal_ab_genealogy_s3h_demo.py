"""S3h candidate. Selecting a declaration grants no controller authorization."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy
import fraktal_ab_document_revision as document_revision


# 50 ms holds the oracle frame for three of the slowest recorded 15.9 ms reads.
def application():return replace(genealogy.application(),canonical_publication_stage=10,
                                  canonical_observation_period_ms=50, config_predecessors=document_revision.recorded('fraktal_ab_genealogy_s3h_demo', '6F3F8CDA9A8F6B59'))
