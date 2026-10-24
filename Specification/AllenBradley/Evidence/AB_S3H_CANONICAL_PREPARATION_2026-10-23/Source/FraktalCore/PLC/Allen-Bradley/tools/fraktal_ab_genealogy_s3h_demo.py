"""S3h candidate. Selecting a declaration grants no controller authorization."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy


def application():return replace(genealogy.application(),canonical_publication_stage=10)
