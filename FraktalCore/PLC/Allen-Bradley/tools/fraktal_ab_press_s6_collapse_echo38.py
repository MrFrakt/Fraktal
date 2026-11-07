"""S6-Q press profile: the press S3 exit candidate, collapsed (WP6.6).

The canonical structures become the working storage, one increment at a time
(fraktal_ab_collapse). Its pre-collapse surface is the S3 exit candidate's,
recorded before the collapse began, and the schema-identity gate holds it to
that surface with every intended difference declared.
"""
from dataclasses import replace
import fraktal_ab_press_canonical_echo38 as previous


# O10: the private facts the press harnesses assert (fraktal_ab_press_execute,
# and PressRam's hold in fraktal_ab_press_canonical_execute). Facts with a
# canonical home (the mode, step and scrap count, PartSlide's state) are read
# from the canonical rows instead.
FIXTURE = (
    ('Unit', ('Aborted', 'Complete', 'CycleCount', 'DecisionId', 'Error', 'ErrorID', 'ErrorSource',
              'ModeSwitches', 'OrderFail', 'Par_TaskPeriodMs', 'ReportedCount', 'ReportedReason',
              'ReportedSource', 'Running', 'SchemaVersion', 'StartLatched')),
    ('Chart', ('LastMs', 'StallReason', 'StepCursor', 'Visited')),
    ('Door', ('DoneCount', 'Error', 'Execute', 'ManualCmd', 'OutImm_Pos')),
    ('PartSlide', ('ErrorID', 'Execute')),
    ('TwoHand', ('OutImm_Armed',)),
    ('PressRam', ('OutImm_Held',)),
    ('Mailbox', ('DiagnosticKey',)),
    # Phase 6 capture: exact unmasked value and native audit, not a client cache.
    ('Cfg0', ('SchemaVersion', 'BaselineWorkMs')),
    ('ConfigAudit', ('Head', 'Sequence', 'Kind', 'Value', 'SourceKey', 'Revision')),
    ('Profiler', ('LastWork',)),
    ('AirPressureMonitor', ('OutImm_PressureOk',)),
)


def application():
    # The documents it loads are the candidate's: same values, same predecessors.
    # The S3h frame copied legacy contexts, which the collapse removes (R6); O10
    # observes what the harnesses still need.
    # O10/O11 read native rows with the approved V6.7 counter bindings. The
    # frozen S3 exit parent is V6.6 and deliberately remains unchanged.
    return replace(previous.application(), canonical_collapse=True, canonical_observation_period_ms=0,
                   canonical_read_coherence=True, canonical_config_read_view=True,
                   canonical_owner_revisions=True,
                   fixture_observation=FIXTURE)
