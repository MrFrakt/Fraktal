"""Record a read-only, hash-bound original medium for an isolated Echo fixture.

No controller connection, document migration or application. Live documents
are selected by default; named sets join only with --include-sets. The source
is never opened by the Dart child: HostLease copies the manifest into a new
store. Credentials and unrelated files are outside the format whitelist.
"""
import argparse
import hashlib
import json
from pathlib import Path

from fraktal_ab_harness_host import STORE_FILE
from fraktal_ab_harness_process import echo_target
from fraktal_ab_live_medium import FileMedium
from fraktal_ab_set_documents import FileStore


def record(directory, output, *, serial, root, include_sets=False):
    unused, serial = echo_target('127.0.0.1', 0, serial, root)
    source, output = Path(directory).resolve(), Path(output).resolve()
    if output.is_relative_to(source):
        raise ValueError('seed manifest must be outside the original medium')
    medium = FileMedium(source / 'live')
    confirmed = medium.index()
    if root + '.station' not in confirmed:
        raise ValueError('original medium has no confirmed station document')
    for key in confirmed:
        doc = medium.read(key)
        if doc is None or doc[0]['root'] != root:
            raise ValueError('original medium is incomplete or belongs to another root')
    sets = FileStore(source)
    named = sets.list() if include_sets else []
    if any(row['root'] != root for row in named):
        raise ValueError('named set belongs to another root')
    # The index is authority. Unconfirmed leftovers are not original documents.
    candidates = [source / 'live/index.json', *(medium._path(key) for key in confirmed),
                  *(sets._path(row['set']) for row in named)]
    files = []
    for path in sorted(candidates):
        relative = path.relative_to(source).as_posix()
        if not STORE_FILE.fullmatch(relative) or path.is_symlink() or not path.resolve().is_relative_to(source):
            raise ValueError('unsafe original medium entry')
        data = path.read_bytes()
        files.append(dict(path=relative, sha256=hashlib.sha256(data).hexdigest().upper()))
    if not 1 <= len(files) <= 256:
        raise ValueError('original medium exceeds fixture manifest bounds')
    result = dict(schema='fraktal.harness.store-seed', schemaVersion=1, serial=serial,
                  root=root, directory=str(source), includeSets=include_sets, files=files)
    with output.open('x', encoding='utf-8', newline='\n') as out:
        json.dump(result, out, indent=2)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--expect-serial', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--include-sets', action='store_true')
    args = parser.parse_args(argv)
    result = record(args.directory, args.output, serial=args.expect_serial,
                    root=args.root, include_sets=args.include_sets)
    print(json.dumps(dict(files=len(result['files']), output=str(args.output),
        sha256=hashlib.sha256(args.output.read_bytes()).hexdigest().upper(), controllerAccess=False)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
