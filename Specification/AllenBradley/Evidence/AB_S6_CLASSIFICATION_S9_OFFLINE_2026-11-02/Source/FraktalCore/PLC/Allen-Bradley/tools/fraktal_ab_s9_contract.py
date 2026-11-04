"""Replay the shared Dart repository contract on canonical controller captures.

Offline only: the S1 reader decodes sealed Symbol/Template/raw-byte captures.
No declaration, legacy projection, Python gateway, controller or listener.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from fraktal_ab_canonical_reader import load_json, snapshot as canonical_snapshot

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CAPTURE = ROOT / ('Specification/AllenBradley/Evidence/'
    'AB_S5_GATEWAY_QUALIFICATION_2026-10-31/Runtime/generic_capture.json.gz')


def snapshot(capture=DEFAULT_CAPTURE):
    return canonical_snapshot(load_json(capture))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flutter', required=True, type=Path)
    parser.add_argument('--capture', type=Path, default=DEFAULT_CAPTURE)
    args = parser.parse_args(argv)
    hmi = Path(__file__).resolve().parents[3] / 'HMI'
    with tempfile.TemporaryDirectory(prefix='FraktalS9Contract-') as directory:
        path = Path(directory) / 'snapshot.json'
        path.write_text(json.dumps(snapshot(args.capture)), encoding='utf-8')
        env = dict(os.environ, FRAKTAL_S9_SNAPSHOT=str(path))
        result = subprocess.run([str(args.flutter), 'test', '--no-pub', 'test/repository_contract_test.dart',
                                 'test/reconnecting_opcua_session_client_test.dart',
                                 'test/fraktal_gateway_server_test.dart',
                                 'test/opcua_repository_test.dart',
                                 'test/opcua_freshness_test.dart', '--reporter', 'expanded'],
                                cwd=hmi, env=env, timeout=300)
        return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
