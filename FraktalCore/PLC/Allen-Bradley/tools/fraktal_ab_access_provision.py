"""Create an offline salted User registration; never store or print its PIN.

Paste the resulting hash record into the station's committed access_users.
Use the owner's controlled commissioning/download workflow to replace users.
"""
import argparse
import getpass
import secrets
import sys

from fraktal_ab_access import User, pin_hash, validate_users


def registration(name, level, pin, salt=None):
    if not pin or len(pin) > 32 or any(not 32 <= ord(c) <= 126 for c in pin):
        raise ValueError('PIN must be 1..32 printable ASCII characters')
    salt = secrets.token_bytes(16) if salt is None else salt
    user = User(name, level, salt.hex(), pin_hash(salt, pin.encode('ascii')).hex())
    if validate_users((user,)):
        raise ValueError('invalid user registration')
    return user


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('user')
    p.add_argument('--level', required=True, type=int, choices=(1, 2, 3, 4))
    args = p.parse_args(argv)
    pin = getpass.getpass('New PIN (never printed or stored): ')
    again = getpass.getpass('Repeat PIN: ')
    try:
        if pin != again:
            raise ValueError('PIN confirmation does not match')
        user = registration(args.user, args.level, pin)
    except ValueError as error:
        p.error(str(error))
    finally:
        pin = again = ''
    print(f'access.User({user.name!r}, {user.level}, {user.salt!r}, {user.pin_hash!r}),')
    return 0


if __name__ == '__main__':
    sys.exit(main())
