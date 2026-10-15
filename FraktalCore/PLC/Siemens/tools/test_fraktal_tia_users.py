"""Station-local user commissioning overlay: hashed only, one-time, refusing misuse."""
import hashlib
import unittest

import fraktal_tia_examples as EX
import fraktal_tia_users as USERS
from fraktal_tia_access import rounds


class UsersOverlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources, _, _ = EX.build()
        cls.composition = sources['30_PressDemoComposition.scl']

    def test_hash_is_the_core_local_provider_hash(self):
        salt = bytes(range(16))
        digest = hashlib.sha256(salt + b'1234').digest()
        for _ in range(rounds()):
            digest = hashlib.sha256(digest + salt).digest()
        self.assertEqual(USERS.pin_hash(b'1234', salt), digest)
        self.assertNotEqual(USERS.pin_hash(b'1234', bytes(16)), digest)

    def test_overlay_enables_provider_and_registers_once_after_store_boot(self):
        salt, digest = bytes(range(16)), bytes(range(32))
        text = USERS.provision(self.composition, ['PressDemo'], [('admin', 'ADMIN', salt, digest)])
        boot = text.index('"FRK_AccessStoreBoot"(Startup := #RootStartup);')
        enable = text.index('"PressDemo".Access.ProviderEnabled := TRUE;')
        guard = text.index('IF "FRK_AccessStorage".UsersReady AND "FRK_LocalUsers".Count = 0 THEN')
        register = text.index('"FRK_AccessRegisterHash"(Record := #ProvisionUser);')
        root = text.index('"PressDemo"(ParentIndex := 0')
        self.assertLess(boot, enable)
        self.assertLess(enable, guard)
        self.assertLess(guard, register)
        self.assertLess(register, root)
        self.assertIn("#ProvisionUser.User := 'admin';", text)
        self.assertIn('#ProvisionUser.PinHash[31] := BYTE#16#1F;', text)
        self.assertIn('ProvisionUser : "ST_UserRecord";', text)
        self.assertNotIn('1234', text)

    def test_misuse_is_refused(self):
        row = [('admin', 'ADMIN', bytes(16), bytes(32))]
        once = USERS.provision(self.composition, ['PressDemo'], row)
        with self.assertRaises(ValueError):
            USERS.provision(once, ['PressDemo'], row)
        with self.assertRaises(ValueError):
            USERS.provision(self.composition, ['Elsewhere'], row)
        for bad in ('admin:ROOT:FRAKTAL_TIA_PIN_ADMIN', 'admin:NONE:FRAKTAL_TIA_PIN_ADMIN',
                    "ad'min:ADMIN:FRAKTAL_TIA_PIN_ADMIN", 'admin:ADMIN:pin', 'admin:ADMIN'):
            with self.assertRaises(ValueError, msg=bad):
                USERS.parse_user(bad)


if __name__ == '__main__':
    unittest.main()
