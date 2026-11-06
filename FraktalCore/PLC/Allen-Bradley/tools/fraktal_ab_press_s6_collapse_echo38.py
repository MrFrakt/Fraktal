"""S6-Q press profile: the press S3 exit candidate, collapsed (WP6.6).

The canonical structures become the working storage, one increment at a time
(fraktal_ab_collapse). Its pre-collapse surface is the S3 exit candidate's,
recorded before the collapse began, and the schema-identity gate holds it to
that surface with every intended difference declared.
"""
from dataclasses import replace
import fraktal_ab_press_canonical_echo38 as previous


def application():
    # The documents it loads are the candidate's: same values, same predecessors.
    return replace(previous.application(), canonical_collapse=True)
