"""S6-Q genealogy profile: the V6.11 host-services profile, collapsed (WP6.6).

The canonical structures become the working storage, one increment at a time
(fraktal_ab_collapse). Its pre-collapse surface is the V6.11 profile's,
recorded before the collapse began, and the schema-identity gate holds it to
that surface with every intended difference declared.
"""
from dataclasses import replace
import fraktal_ab_genealogy_s6_host_demo as previous


def application():
    # The documents it loads are the V6.11 profile's: same values, same predecessors.
    # The S3h frame copied legacy contexts, which the collapse removes (R6). Its
    # candidate-case harnesses' private facts join O10 when they migrate.
    return replace(previous.application(), canonical_collapse=True, canonical_observation_period_ms=0,
                   fixture_observation=(
                       ('Mailbox', ('DiagnosticKey',)),
                       # Part's restored recovery matrix and its start helper.
                       ('Unit', ('Aborted', 'Complete', 'CycleCount', 'DecisionId',
                                 'Error', 'ErrorID', 'Running')),
                       ('TwoHand', ('OutImm_Armed',)),
                       ('PressRam', ('OutImm_Held',)),
                       ('AccessState', ('CurrentLevel', 'LoginBusy', 'Required')),
                   ))
