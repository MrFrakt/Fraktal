"""The S3k request-case runner refuses without a matching current authorization."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fraktal_ab_command_binding as binding
import fraktal_ab_part_execute as guarded
import fraktal_ab_s3k_fixture_execute as fixture

PIN = 'A'*64


class AuthorizationTests(unittest.TestCase):
    def authorize(self, **changes):
        record = dict(CurrentOwnerApproved=True, MailboxOrTagWritesAuthorized=True, Serial='601FC87B',
                      CanonicalSha256=PIN, FaultClearAuthorized=False, ClockSetAuthorized=False)
        record.update(changes)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'authorization.json'
            path.write_text(json.dumps(record), encoding='utf-8')
            return fixture.authorize(path, PIN)

    def test_exact_current_request_authorization_is_accepted(self):
        self.assertTrue(self.authorize()['MailboxOrTagWritesAuthorized'])

    def test_download_only_wrong_target_image_or_extra_scope_is_refused(self):
        for changes in (dict(MailboxOrTagWritesAuthorized=False), dict(CurrentOwnerApproved=False),
                        dict(Serial='00000000'), dict(CanonicalSha256='B'*64), dict(FaultClearAuthorized=True),
                        dict(ClockSetAuthorized=True), dict(MailboxOrTagWritesAuthorized='yes')):
            with self.subTest(changes=changes), self.assertRaises(guarded.FixtureRefused):
                self.authorize(**changes)


class HelperTests(unittest.TestCase):
    def test_native_walk_requires_the_s3k_declaration_including_its_legacy_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'authorization.json'
            path.write_text(json.dumps(dict(CurrentOwnerApproved=True,MailboxOrTagWritesAuthorized=True,
                Serial='601FC87B',CanonicalSha256=PIN,FaultClearAuthorized=False,ClockSetAuthorized=False)))
            with patch.object(fixture.genealogy,'main',return_value=0) as selected:
                fixture.main(['--authorization-file',str(path),'--expect-acd-sha256',PIN])
            self.assertEqual(selected.call_args.kwargs['expected_declaration'],'fraktal_ab_genealogy_s3k_demo')

    def test_arguments_are_the_complete_core_set_with_typed_defaults(self):
        value = fixture.arguments(Kind=3, BoolValue=True)
        self.assertEqual(set(value), set(binding.ARGUMENTS))
        self.assertEqual((value['Secret'], value['IntValue'], value['BoolValue']), ('', 0, True))
        with self.assertRaises(ValueError):
            fixture.arguments(Sequence=1)

    def test_uint32_tokens_keep_their_bit_pattern_as_signed_dint(self):
        self.assertEqual([fixture.signed(v) for v in (0, 0x7fffffff, 0x80000000, 0xffffffff, -1)],
                         [0, 0x7fffffff, -0x80000000, -1, -1])


if __name__ == '__main__': unittest.main()
