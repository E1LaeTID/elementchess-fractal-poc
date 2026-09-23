import unittest

from elementchess.balance_simulation import BalanceMonteCarlo


class BalanceSimulationTest(unittest.TestCase):
    def test_same_seed_produces_same_report(self):
        first = BalanceMonteCarlo(17).run(10).to_dict()
        second = BalanceMonteCarlo(17).run(10).to_dict()
        self.assertEqual(first, second)
        self.assertEqual(len(first["geometries"]), 3)
        self.assertIn("checkmate", first["terminal_race"])
        self.assertIn("stock_reaches_twenty_one", first["terminal_race"])


if __name__ == "__main__":
    unittest.main()
