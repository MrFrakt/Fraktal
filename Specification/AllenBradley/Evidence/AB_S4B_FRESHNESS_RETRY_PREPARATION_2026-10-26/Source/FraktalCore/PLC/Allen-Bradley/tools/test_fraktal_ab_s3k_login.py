"""Execute typed ingress and the private access owner with independent tokens."""
from copy import deepcopy
from dataclasses import replace
import unittest

import fraktal_ab_access as access
import fraktal_ab_canonical_commands as commands
import fraktal_ab_mailbox as mailbox
import fraktal_ab_mailbox_frame as frame
import fraktal_ab_manifest as manifest
import fraktal_ab_st_model as st
import test_fraktal_ab_access as authority
import test_fraktal_ab_canonical_commands as ingress_fixture


class LoginSequenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ingress_fixture.IngressTests.setUpClass()
        cls.app = replace(ingress_fixture.IngressTests.app, access_users=(authority.USER,))

    def bench(self, real_sha=False):
        ingress = ingress_fixture.IngressTests()
        ingress.setUp()
        plc = authority.controller()
        plc.tags.update(ingress.tags)
        ingress.tags = plc.tags
        ingress.plc = plc
        plc.routines.update({name: st.parse('\n'.join(body)) for name, body in ingress.routines.items()})
        authority.add_access(plc, self.app, real_sha=real_sha)
        plc.tags[manifest.header_tag(self.app)]['ConfigRevision'] = 7
        plc.tags[access.tag(self.app, 'LoginRequest')] = deepcopy(ingress.request)
        ingress.request['Sequence'] = ingress.work['LastLegacySeen'] = 701
        ingress.response['AckSequence'] = 701
        return ingress

    def consume_and_finish(self, bench):
        plc = bench.plc
        plc.run(bench.ingress)
        self.assertEqual(bench.work['Error'], 0)
        plc.tags['FRK_Press_HmiLastSequence'] = bench.work['OwnerSequence']
        plc.run('\n'.join(access.login(self.app)))
        bench.response['Accepted'] = 1
        plc.run(bench.after)
        cyclic = st.parse('\n'.join(access.cyclic(self.app)))
        for unused in range((access.PIN_HASH_ROUNDS + 1) * access.HASH_BLOCK_SCANS):
            plc.run(cyclic)
            held = plc.tags[access.tag(self.app, 'State')]
            if not held['LoginBusy']:
                break
        else:
            self.fail('login exceeded its declared scan budget')
        for source in (bench.request, plc.tags[access.tag(self.app, 'LoginRequest')]):
            for name in ('Secret', 'TextValue'):
                self.assertEqual(source[name]['LEN'], 0)
                self.assertFalse(any(source[name]['DATA']))
        return held

    def test_typed_pin_login_completes_with_real_sha_and_preserves_legacy_commit_and_ack(self):
        bench = self.bench(real_sha=True)
        bench.stage(12, Kind=mailbox.LOGIN, User='tester', Secret=authority.PIN.decode())
        held = self.consume_and_finish(bench)
        self.assertEqual((held['CurrentLevel'], held['LoginFailed'], held['LoginResultSequence']), (4, 0, 12))
        self.assertEqual((bench.request['Sequence'], bench.response['AckSequence']), (701, 701))
        bench.plc.run(bench.ingress)
        self.assertEqual(bench.work['Pending'], 0)

    def test_wrong_typed_pin_still_fails_under_the_typed_token(self):
        bench = self.bench()
        bench.stage(12, Kind=mailbox.LOGIN, User='tester', Secret='wrong')
        held = self.consume_and_finish(bench)
        self.assertEqual((held['CurrentLevel'], held['LoginFailed'], held['LoginResultSequence']), (0, 1, 12))
        self.assertEqual((bench.request['Sequence'], bench.response['AckSequence']), (701, 701))

    def test_legacy_login_after_typed_uses_its_own_token(self):
        bench = self.bench()
        bench.stage(12, Kind=mailbox.LOGIN, User='tester', Secret=authority.PIN.decode())
        self.assertEqual(self.consume_and_finish(bench)['CurrentLevel'], 4)
        bench.request['Sequence'] = 702
        bench.request['Frame']['Words'] = frame.encode(self.app,
            dict(Kind=mailbox.LOGIN, Sequence=702, User='tester', Secret=authority.PIN.decode()))
        held = self.consume_and_finish(bench)
        self.assertEqual((held['CurrentLevel'], held['LoginFailed'], held['LoginResultSequence']), (4, 0, 702))
        self.assertEqual((bench.request['Sequence'], bench.response['AckSequence']), (702, 702))
        self.assertEqual(bench.work['LastCoreSeen'], 12)


if __name__ == '__main__':
    unittest.main()
