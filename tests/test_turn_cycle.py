import unittest

from elementchess.domain import TerrainOwner
from elementchess.turn_cycle import RoundCycle


class RoundCycleTest(unittest.TestCase):
    def test_interstice_only_follows_black_move(self) -> None:
        cycle = RoundCycle()
        self.assertFalse(cycle.finish_piece_move())
        self.assertEqual(cycle.active_owner, TerrainOwner.BLACK)
        self.assertEqual(cycle.round_number, 1)

        self.assertTrue(cycle.finish_piece_move())
        self.assertEqual(cycle.active_owner, TerrainOwner.WHITE)
        self.assertEqual(cycle.round_number, 2)


if __name__ == "__main__":
    unittest.main()
