"""Offline S9 regression sensitivity. Mutate functions in memory, never files."""
import asyncio
import inspect
import io
import json
from pathlib import Path
import textwrap
import unittest
from unittest import mock

import fraktal_ab_gateway as gw
import fraktal_ab_mailbox as mb
import fraktal_ab_mailbox_frame as frame
from test_fraktal_ab_s9 import APP, FrameTests, CrashTests
import fraktal_ab_projection as projection
from test_fraktal_ab_command_reads import NativeControlReads, GatewayControlReads


def replaced(function, before, after):
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(before) != 1:
        raise AssertionError('mutation does not identify exactly one implementation site')
    namespace = dict(function.__globals__)
    exec(compile(source.replace(before, after), '<S9 in-memory mutant>', 'exec'), namespace)
    return namespace[function.__name__]


def run():
    original = frame.logic
    words = frame.sample_tag(APP) + '.Words'
    request = mb.request_tag_name(APP)
    def emitted(before, after):
        source = '\n'.join(original(APP))
        if source.count(before) != 1:
            raise AssertionError('generated mutation has a missing/ambiguous site')
        return mock.patch.object(frame, 'logic', lambda app: tuple(source.replace(before, after).splitlines()))
    # The schema/sequence checks, copy, bounds and wipes are tested by emitted
    # ST execution. Gateway mutants exercise the actual async implementation.
    cases = [
        ('mailbox-leading-coherence-removed', mock.patch.object(projection, 'read_mailbox_document',
          replaced(projection.read_mailbox_document,
                   'plan.manifest is None or plan.manifest[0] != header', 'False')), NativeControlReads,
         'test_changed_leading_header_refuses_before_reading_response'),
        ('mailbox-trailing-coherence-removed', mock.patch.object(projection, 'read_mailbox_document',
          replaced(projection.read_mailbox_document,
                   'reader.decode_header(after) != header', 'False')), NativeControlReads,
         'test_changed_trailing_header_cannot_publish_a_torn_answer'),
        ('mailbox-preflight-uses-stale-cache', mock.patch.object(gw.Gateway, '_write_batch_locked',
          replaced(gw.Gateway._write_batch_locked,
                   'await self.station.mailbox_document()', 'await self.station.document()')), GatewayControlReads,
         'test_pending_request_refuses_even_when_full_snapshot_was_cached'),
        ('mailbox-failure-revives-cached-good', mock.patch.object(gw.Station, 'mailbox_document',
          replaced(gw.Station.mailbox_document,
                   'self._doc = None', 'pass')), GatewayControlReads,
         'test_failed_control_read_discards_cached_good_and_never_writes'),
        ('schema-unchecked', emitted(f'({words}[0] <> 1) OR ', ''), FrameTests,
         'test_corrupt_lengths_and_schema_refuse_without_array_fault'),
        ('sequence-unchecked', emitted(f' OR ({words}[{frame.word_count(APP)-1}] <> {request}.Sequence)', ''), FrameTests,
         'test_partial_payload_and_early_commit_refuse_without_late_execution'),
        ('aggregate-bound-removed', emitted(f') > {frame.argument_bytes(APP)} THEN', ') > 10000 THEN'), FrameTests,
         'test_corrupt_lengths_and_schema_refuse_without_array_fault'),
        ('private-copy-missing', emitted(f'CPS({request}.Frame,{frame.sample_tag(APP)},1);', ''), FrameTests,
         'test_round_trip_and_uint32_wrap_are_the_generated_decoder'),
        ('transport-frame-not-wiped', emitted(f'{request}.Frame.Words[FRK_{APP.name}_HmiWipe] := 0;', ''), FrameTests,
         'test_round_trip_and_uint32_wrap_are_the_generated_decoder'),
        ('sample-frame-not-wiped', emitted(f'{words}[FRK_{APP.name}_HmiWipe] := 0;', ''), FrameTests,
         'test_round_trip_and_uint32_wrap_are_the_generated_decoder'),
        ('commit-written-first', mock.patch.object(mb, 'command_writes',
          side_effect=lambda *a, _original=mb.command_writes, **kw: list(reversed(_original(*a, **kw)))), FrameTests,
         'test_partial_payload_and_early_commit_refuse_without_late_execution'),
        ('signed-native-sequence-removed', mock.patch.object(frame, 'signed', lambda value: value), FrameTests,
         'test_round_trip_and_uint32_wrap_are_the_generated_decoder'),
        ('sequence-reserved-after-io', mock.patch.object(gw.Gateway, '_write_batch_locked',
          replaced(gw.Gateway._write_batch_locked,
                   'self._mailbox_sequences[mailbox] = sequence\n    self.station._doc = None',
                   'self.station._doc = None')), CrashTests,
         'test_five_replay_boundaries_and_fresh_recovery'),
        ('cached-good-survives-read-failure', mock.patch.object(gw.Station, 'document',
          replaced(gw.Station.document,
                   'self._doc = None  # a forced read failure cannot revive cached Good data',
                   'pass')), CrashTests,
         'test_failed_forced_read_cannot_return_cached_good'),
    ]
    rows = []
    for name, patch, test_class, method in cases:
        with patch:
            result = unittest.TextTestRunner(stream=io.StringIO()).run(test_class(method))
        rows.append(dict(mutation=name, test=method, detected=not result.wasSuccessful(),
                         failures=len(result.failures), errors=len(result.errors)))
    return dict(schema='fraktal.ab.s9-offline-mutations', schemaVersion=1,
                filesystemMutated=False, controllerIo=False, rows=rows,
                passed=all(r['detected'] for r in rows))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    record = run()
    if args.output:
        if args.output.exists():
            parser.error('refusing to overwrite mutation evidence')
        args.output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(passed=record['passed'], detected=sum(r['detected'] for r in record['rows']),
                          mutations=len(record['rows']))))
    raise SystemExit(0 if record['passed'] else 1)
