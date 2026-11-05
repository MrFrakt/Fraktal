"""S3f candidate. Selecting a declaration grants no controller authorization."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy
import fraktal_ab_document_revision as document_revision


def application():return replace(genealogy.application(),canonical_publication_stage=8, config_predecessors=document_revision.recorded('fraktal_ab_genealogy_s3f_demo', '6F3F8CDA9A8F6B59'))
