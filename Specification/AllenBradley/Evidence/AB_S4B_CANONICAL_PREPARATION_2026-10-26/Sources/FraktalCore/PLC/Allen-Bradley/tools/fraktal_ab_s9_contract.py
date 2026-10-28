"""Run the shared Dart repository contract on the actual AB adapter document.

Offline only: native data fixtures are generated from the committed declaration,
projected by production code and wrapped by Gateway. No controller or listener.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import tempfile


def snapshot():
    import fraktal_ab_gateway as gw
    import fraktal_ab_projection as projection
    from test_fraktal_ab_projection import build, persist_values, record_values, alarm_values, oee_values
    doc = build(persist=persist_values(), record_values=record_values(),
                alarm_state=alarm_values(), oee_state=oee_values(),
                mailbox_state={'requestSequence': 0, 'response': {'AckSequence': 0, 'Accepted': 0, 'DiagnosticKey': 0}})
    # Same Station metadata, discovery and per-connection envelope as a browser.
    gateway = gw.Gateway(gw.Station(lambda: doc, budget=projection.APP.read_budget))
    result = asyncio.run(gateway._snapshot(gw._ConnState()))
    assert result['schema'] == projection.SCHEMA and result['moduleCount'] == len(projection.APP.modules) + 1
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flutter', required=True, type=Path)
    args = parser.parse_args(argv)
    hmi = Path(__file__).resolve().parents[3] / 'HMI'
    with tempfile.TemporaryDirectory(prefix='FraktalS9Contract-') as directory:
        path = Path(directory) / 'snapshot.json'
        path.write_text(json.dumps(snapshot()), encoding='utf-8')
        env = dict(os.environ, FRAKTAL_S9_SNAPSHOT=str(path))
        result = subprocess.run([str(args.flutter), 'test', 'test/repository_contract_test.dart',
                                 'test/reconnecting_opcua_session_client_test.dart',
                                 'test/fraktal_gateway_server_test.dart',
                                 'test/opcua_repository_test.dart',
                                 'test/opcua_freshness_test.dart', '--reporter', 'expanded'],
                                cwd=hmi, env=env, timeout=300)
        return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
