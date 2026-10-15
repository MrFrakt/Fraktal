"""Commission local Fraktal users into ONE station build, as salted hashes only.

The shipped generators emit no users and a disabled login provider (Core §14:
"production defaults remain open until composition provisioning"). This tool is
that composition step for a single station: it rewrites the generated
composition root of a flat package so that

* the named roots enable their local provider, and
* a one-time registration writes each user through the trusted Core seam
  FRK_AccessRegisterHash while the retained user store is ready and EMPTY.

Once a user exists the store is never reseeded; the LOAD_DB/retain medium
persists it. PINs come only from environment variables named on the command
line (never an argument, file or log). The output contains the 16-byte salt and
the Core work-factor SHA-256 hash, so a short PIN is only as strong as its
length: keep such a build local, never in the shared generated package.

    set FRAKTAL_TIA_PIN_ADMIN=...   (or the DPAPI wrapper)
    python fraktal_tia_users.py <flat package> --root PressDemo --user admin:ADMIN:FRAKTAL_TIA_PIN_ADMIN
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets

from fraktal_tia_access import rounds
from fraktal_tia_binding import Catalog

ANCHOR = '    "FRK_AccessStoreBoot"(Startup := #RootStartup);\n'
TEMP = 'VAR_TEMP\n'
MAX_PIN = 32


def pin_hash(pin: bytes, salt: bytes) -> bytes:
    """The Core local-provider hash: SHA-256(salt + PIN), then the Core work
    factor of SHA-256(previous digest + salt)."""
    digest = hashlib.sha256(salt + pin).digest()
    for _ in range(rounds()):
        digest = hashlib.sha256(digest + salt).digest()
    return digest


def parse_user(text: str) -> tuple[str, str, str]:
    parts = text.split(':')
    if len(parts) != 3:
        raise ValueError('--user is name:LEVEL:ENV_VAR')
    name, level, env = parts
    if not re.fullmatch(r'[A-Za-z0-9_.\-]{1,32}', name):
        raise ValueError('user names are 1-32 ASCII letters, digits, ._-')
    if level not in Catalog.read().enums['E_AccessLevel'] or level == 'NONE':
        raise ValueError('level must be an E_AccessLevel above NONE')
    if not re.fullmatch(r'[A-Z_][A-Z0-9_]*', env):
        raise ValueError('the PIN is named by an environment variable')
    return name, level, env


def provision(text: str, roots: list[str], users: list[tuple[str, str, bytes, bytes]]) -> str:
    """Insert provider enablement and one-time hashed registration after the
    access-store boot of a generated composition root."""
    levels = Catalog.read().enums['E_AccessLevel']
    if text.count(ANCHOR) != 1:
        raise ValueError('composition root has no single FRK_AccessStoreBoot call')
    if 'FRK_AccessRegisterHash' in text:
        raise ValueError('package is already provisioned')
    if not roots or not all(re.fullmatch(r'[A-Za-z_]\w*', r) and '"%s"(' % r in text for r in roots):
        raise ValueError('every --root must be a root called by this composition')
    lines = ['    // ---- COMMISSIONING (fraktal_tia_users.py): station-local, hashed only',
             *['    "%s".Access.ProviderEnabled := TRUE;' % root for root in roots],
             '    IF "FRK_AccessStorage".UsersReady AND "FRK_LocalUsers".Count = 0 THEN']
    for name, level, salt, digest in users:
        lines += ['        #ProvisionUser.User := \'%s\';' % name,
                  '        #ProvisionUser.Level := %d;' % levels[level]]
        lines += ['        #ProvisionUser.Salt[%d] := BYTE#16#%02X;' % (i, b) for i, b in enumerate(salt)]
        lines += ['        #ProvisionUser.PinHash[%d] := BYTE#16#%02X;' % (i, b) for i, b in enumerate(digest)]
        lines += ['        #ProvisionOk := "FRK_AccessRegisterHash"(Record := #ProvisionUser);']
    lines += ['    END_IF;', '    // ---- COMMISSIONING end']
    text = text.replace(ANCHOR, ANCHOR + '\n'.join(lines) + '\n')
    if text.count(TEMP) != 1:
        raise ValueError('composition root has no single VAR_TEMP section')
    return text.replace(TEMP, TEMP + '    ProvisionUser : "ST_UserRecord";\n    ProvisionOk : Bool;\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('package', type=Path, help='flat generated package (rewritten in place)')
    parser.add_argument('--root', action='append', required=True)
    parser.add_argument('--user', action='append', required=True, help='name:LEVEL:ENV_VAR')
    args = parser.parse_args(argv)
    sources = [p for p in args.package.iterdir() if re.fullmatch(r'30_\w*Composition\.scl|30_FB_FraktalMain\.scl', p.name)]
    if len(sources) != 1:
        raise SystemExit('expected one generated composition root in ' + str(args.package))
    users = []
    for name, level, env in map(parse_user, args.user):
        pin = os.environ.get(env, '').encode('ascii')
        if not 1 <= len(pin) <= MAX_PIN:
            raise SystemExit('%s must hold a 1-%d character PIN' % (env, MAX_PIN))
        salt = secrets.token_bytes(16)
        users.append((name, level, salt, pin_hash(pin, salt)))
    path = sources[0]
    path.write_bytes(provision(path.read_text('ascii'), args.root, users).encode('ascii'))
    print('provisioned %d user(s) for %s in %s' % (len(users), ', '.join(args.root), path.name))


if __name__ == '__main__':
    main()
