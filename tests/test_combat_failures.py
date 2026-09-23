import unittest

from elementchess.combat_failures import CombatFailureTracker


class CombatFailureTrackerTest(unittest.TestCase):
    def test_failure_grows_to_three_and_two_clean_turns_remove_one(self) -> None:
        tracker = CombatFailureTracker()
        tracker.record_failure("BLANC")
        tracker.finish_turn("BLANC")
        self.assertEqual(tracker.failures["BLANC"], 1)
        tracker.finish_turn("BLANC")
        self.assertEqual(tracker.failures["BLANC"], 1)
        tracker.finish_turn("BLANC")
        self.assertEqual(tracker.failures["BLANC"], 0)
        for _ in range(3):
            tracker.record_failure("NOIR")
            tracker.finish_turn("NOIR")
        self.assertTrue(tracker.defeated("NOIR"))


if __name__ == "__main__":
    unittest.main()
