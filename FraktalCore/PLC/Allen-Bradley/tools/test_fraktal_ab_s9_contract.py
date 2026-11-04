"""First S6 harness migration replays sealed bytes; no live connection or writes."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import fraktal_ab_s9_contract as harness


class CanonicalContractReplay(unittest.TestCase):
    def test_all_values_and_types_match_the_sealed_native_qualification(self):
        runtime = harness.DEFAULT_CAPTURE.parent
        hashes = json.loads((runtime.parent / 'payload_hashes.json').read_bytes())
        for name in ('generic_capture.json.gz', 'generic_snapshot.json.gz'):
            self.assertEqual(hashlib.sha256((runtime/name).read_bytes()).hexdigest().upper(),
                             hashes['Runtime/' + name])
        expected = json.loads(gzip.decompress((runtime/'generic_snapshot.json.gz').read_bytes()))
        actual = harness.snapshot()
        self.assertEqual(actual['values'], expected['values'])
        self.assertEqual(actual['types'], expected['types'])
        self.assertEqual(actual['contentHash'], expected['contentHash'])
        self.assertEqual(actual['moduleCount'], expected['moduleCount'])

    def test_replay_import_graph_has_no_declaration_projection_or_gateway(self):
        program = ('import sys; import fraktal_ab_s9_contract as h; h.snapshot(); '
            'assert not set(sys.modules) & {"fraktal_ab_projection", "fraktal_ab_gateway", '
            '"fraktal_ab_declaration", "fraktal_ab_generate", "fraktal_ab_station"}')
        run = subprocess.run([sys.executable, '-c', program], cwd=Path(__file__).parent,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_other_accepted_captures_keep_their_own_discovered_identity(self):
        path = harness.ROOT/'FraktalCore/HMI/test/fixtures/cip_publication_goldens.json.gz'
        fixtures = json.loads(gzip.decompress(path.read_bytes()))['vectors']
        with tempfile.TemporaryDirectory() as temp:
            for fixture in fixtures:
                capture = Path(temp)/'capture.json'
                capture.write_text(json.dumps(fixture['capture']), encoding='utf-8')
                actual = harness.snapshot(capture)
                self.assertEqual(actual['values'], fixture['expected']['values'])
                self.assertEqual(actual['types'], fixture['expected']['types'])

    def test_invalid_capture_is_refused_before_any_dart_process(self):
        value = json.loads(gzip.decompress(harness.DEFAULT_CAPTURE.read_bytes()))
        value['manifest']['valid'] = False
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'bad.json'
            path.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaises(ValueError):
                harness.snapshot(path)


if __name__ == '__main__':
    unittest.main()
