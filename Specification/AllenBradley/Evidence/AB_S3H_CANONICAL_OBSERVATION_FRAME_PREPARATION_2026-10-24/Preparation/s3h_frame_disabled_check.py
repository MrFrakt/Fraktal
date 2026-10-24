"""Scratch declaration: the S3h candidate with the observation frame off."""
from dataclasses import replace
import fraktal_ab_genealogy_s3h_demo as s3h
def application():return replace(s3h.application(),canonical_observation_period_ms=0)
