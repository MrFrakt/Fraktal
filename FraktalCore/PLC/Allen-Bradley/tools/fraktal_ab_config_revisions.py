"""The configuration revisions a build accepts, recorded before the WP6.6 collapse (O12).

A set or live document carries `configRev`, and the controller loads only a
revision its build accepts (`fraktal_ab_sets.accepted_revisions`). Up to
WP6.6 that revision is derived from the V5 manifest content, which increment
C6 deletes together with the context declarations it is built from. O12
(approved 2026-11-05) redefines the revision from what gives a stored value
its meaning, and keeps loading every document saved before: the collapsed
build accepts, as constants, every revision its pre-collapse build accepted.

Only the pre-collapse generator can compute those constants, so they are
recorded while it exists:

- `--declaration D` prints one declaration's record. A station declared
  outside this repository runs this, with the pre-collapse tools, before it
  upgrades past C6, and carries the list into its declaration.
- `--all --output F` records every declaration in this tree, each in its own
  process because station selection is process state, into the fixture C6
  builds its constants from.

Contacts no controller.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = 'fraktal.ab.config-revisions'
SCHEMA_VERSION = 1
SELECTOR = 'fraktal_ab_station'


def declarations(folder: Path = HERE) -> list[str]:
    """Every station declaration in `folder`: a module exposing `application()`."""
    found = []
    for path in sorted(folder.glob('fraktal_ab_*.py')):
        if path.stem != SELECTOR and re.search(r'^def application\(', path.read_text(encoding='utf-8'), re.M):
            found.append(path.stem)
    return found


def record(declaration: str) -> dict:
    """The selected declaration's own revision and every revision its build accepts."""
    os.environ['FRAKTAL_AB_DECLARATION'] = declaration
    import fraktal_ab_manifest as manifest
    import fraktal_ab_sets as sets
    import fraktal_ab_station as station
    app = station.application()
    accepted = sets.accepted_revisions(app)
    own = manifest.config_revision(app)
    if own not in accepted:
        raise ValueError(f'{declaration}: own revision {own} is not accepted')
    return dict(declaration=declaration, application=app.name, legacyContentHash=manifest.content_hash(app),
                configRevision=own, acceptedRevisions=accepted)


def record_all(folder: Path = HERE) -> dict:
    rows = []
    env = {k: v for k, v in os.environ.items() if k != 'FRAKTAL_AB_DECLARATION'}
    for declaration in declarations(folder):
        done = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--declaration', declaration],
                              capture_output=True, text=True, cwd=folder, env=env)
        if done.returncode:
            raise RuntimeError(f'{declaration}: {done.stderr.strip()[-2000:]}')
        rows.append(json.loads(done.stdout))
    return dict(schema=SCHEMA, schemaVersion=SCHEMA_VERSION, declarations=rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument('--declaration')
    which.add_argument('--all', action='store_true')
    parser.add_argument('--output', type=Path, help='with --all: the fixture to write (refuses to overwrite)')
    args = parser.parse_args(argv)
    if args.declaration:
        print(json.dumps(record(args.declaration), sort_keys=True))
        return 0
    if args.output is None:
        parser.error('--all needs --output')
    result = record_all()
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=1, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(declarations=len(result['declarations']),
                          revisions=sum(len(r['acceptedRevisions']) for r in result['declarations']))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
