"""S3h candidate. Selecting a declaration grants no controller authorization."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy


# 50 ms holds the oracle frame for three of the slowest recorded 15.9 ms reads.
def application():return replace(genealogy.application(),canonical_publication_stage=10,
                                  canonical_observation_period_ms=50)
