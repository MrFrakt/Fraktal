"""Derive UNLINKED load-only sources using the measured native declaration."""
import argparse
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def prepare(out, native):
    out.mkdir(parents=True, exist_ok=False)
    for name in ('GDB_LoadBankA', 'GDB_LoadBankB'):
        data = (native / 'scl' / (name + '.db')).read_bytes()
        anchor = b'NON_RETAIN'
        assert data.count(anchor) == 1
        assert b'UNLINKED' not in data
        (out / (name + '.db')).write_bytes(data.replace(anchor, b'UNLINKED\n' + anchor))
    source = (HERE / 'bench.scl.in').read_text('ascii')
    source, count = re.subn(r'            3:\n.*?            4:', '            3:\n                "GDB_LoadMemoryTest".NativeStatus := WORD#16#FFFF;\n            4:', source, flags=re.S)
    assert count == 1
    source, count = re.subn(r'^    "GDB_LoadMemoryTest"\.Bank[AB]WorkByte := .*?;\n', '', source, flags=re.M)
    assert count == 2
    (out / '39f_LoadMemoryBench.scl').write_bytes(source.encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('native', type=Path)
    args = parser.parse_args()
    prepare(args.out, args.native)
