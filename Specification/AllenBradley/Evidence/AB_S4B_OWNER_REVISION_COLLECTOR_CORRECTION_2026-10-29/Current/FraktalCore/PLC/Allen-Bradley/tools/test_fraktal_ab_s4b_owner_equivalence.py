"""One engineering declaration binds the migration oracle, including V6.10."""
import unittest
from unittest.mock import patch
import fraktal_ab_s4b_equivalence as gate
import fraktal_ab_genealogy_s4b_demo as previous
import fraktal_ab_genealogy_s4b_owner_demo as owner


class OwnerOracleTests(unittest.TestCase):
    def test_explicit_factory_reaches_shared_oracle_without_a_station_fallback(self):
        with patch.object(gate.shared, 'run', return_value='result') as run:
            self.assertEqual(gate.run(None, application_factory=owner.application), 'result')
        self.assertIs(run.call_args.kwargs['application_factory'], owner.application)

    def test_old_default_retains_its_existing_declaration(self):
        with patch.object(gate.shared, 'run') as run:
            gate.run(None)
        self.assertIs(run.call_args.kwargs['application_factory'], previous.application)


if __name__ == '__main__': unittest.main()
