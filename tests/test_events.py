import unittest
from collections import Counter

from elementchess.board import Board
from elementchess.domain import Element, TerrainOwner
from elementchess.events import (
    ELEMENT_POWER_ORDER,
    GameEventType,
    OpeningEventSystem,
    TerrainStateCapture,
)
from elementchess.time_engine import IncrementalTimeEngine


class OpeningEventSystemTest(unittest.TestCase):
    def setUp(self) -> None:
        self.board = Board()
        self.time_engine = IncrementalTimeEngine()
        self.system = OpeningEventSystem(self.board, self.time_engine, seed=426)

    def test_balanced_assignment_covers_only_terrain_cells(self) -> None:
        self.system.prepare()
        terrain_cells = [cell for row in self.board.rows() for cell in row if not cell.is_chess_cell]
        counts = Counter(cell.terrain for cell in terrain_cells)
        self.assertNotIn(Element.NONE, counts)
        self.assertEqual(sum(counts.values()), 225)
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)
        self.assertTrue(
            all(cell.terrain is Element.NONE for row in self.board.rows() for cell in row if cell.is_chess_cell)
        )

    def test_opening_draws_three_distinct_elements(self) -> None:
        self.system.prepare()
        events = self.system.open_first_interstice()
        drawn = [event.element for event in events if event.type is GameEventType.ELEMENT_DRAWN]
        self.assertEqual(len(drawn), 3)
        self.assertEqual(len(set(drawn)), 3)
        self.assertEqual(events[-1].type, GameEventType.TURN_ANNOUNCED)

    def test_each_player_receives_five_gold_token_values(self) -> None:
        self.system.prepare()
        self.system.open_first_interstice()
        for owner in (TerrainOwner.WHITE, TerrainOwner.BLACK):
            tokens = self.system.player_tokens[owner]
            self.assertEqual(len(tokens), 5)
            self.assertTrue(all(1 <= token.value <= 5 for token in tokens))
            self.assertTrue(all(token.owner is owner for token in tokens))
            self.assertNotEqual({token.value for token in tokens}, {1, 2, 3, 4, 5})

    def test_five_valid_clues_are_prepositioned_in_each_zone(self) -> None:
        self.system.prepare()
        for zone_row in range(1, 4):
            for zone_col in range(1, 4):
                zone_id = f"Z{zone_row}{zone_col}"
                clues = [
                    cell for row in self.board.rows() for cell in row
                    if cell.zone_id == zone_id and cell.terrain_number is not None
                ]
                self.assertEqual(len(clues), 5)
                self.assertTrue(all(not cell.is_chess_cell for cell in clues))
                self.assertTrue(all(cell.terrain_owner is TerrainOwner.NONE for cell in clues))

    def test_prepositioned_clues_have_no_local_duplicates(self) -> None:
        self.system.prepare()
        for zone_row in range(3):
            for zone_col in range(3):
                start_x = 1 + zone_col * 5
                start_y = 1 + zone_row * 5
                for offset in range(5):
                    row_values = [
                        self.board.cell(x, start_y + offset).terrain_number
                        for x in range(start_x, start_x + 5)
                        if self.board.cell(x, start_y + offset).terrain_number is not None
                    ]
                    column_values = [
                        self.board.cell(start_x + offset, y).terrain_number
                        for y in range(start_y, start_y + 5)
                        if self.board.cell(start_x + offset, y).terrain_number is not None
                    ]
                    self.assertEqual(len(row_values), len(set(row_values)))
                    self.assertEqual(len(column_values), len(set(column_values)))

    def test_rotation_commands_follow_descending_power(self) -> None:
        self.system.prepare()
        self.system.open_first_interstice()
        indices = [ELEMENT_POWER_ORDER.index(command.element) for command in self.system.rotation_commands]
        self.assertEqual(indices, sorted(indices))

    def test_capture_uses_value_line_and_owner_direction(self) -> None:
        self.board.assign_element(2, 10, Element.FIRE)
        first = self.board.cell(2, 10)
        first.terrain_number = 5
        first.terrain_owner = TerrainOwner.BLACK
        self.board.assign_element(4, 10, Element.FIRE)
        second = self.board.cell(4, 10)
        second.terrain_number = 5
        second.terrain_owner = TerrainOwner.WHITE
        self.assertEqual(TerrainStateCapture.scores(self.board)[Element.FIRE], 0)

    def test_without_player_tokens_opening_rotations_are_zero(self) -> None:
        self.system.prepare()
        self.system.open_first_interstice()
        self.assertTrue(all(command.increments == 0 for command in self.system.rotation_commands))

    def test_reserve_accumulates_but_never_exceeds_twenty_one(self) -> None:
        self.system.prepare()
        self.system.open_first_interstice()
        for turn in range(2, 20):
            self.system.open_interstice(turn, TerrainOwner.WHITE)
        self.assertEqual(len(self.system.player_tokens[TerrainOwner.WHITE]), 21)
        self.assertEqual(len(self.system.player_tokens[TerrainOwner.BLACK]), 21)

    def test_later_interstices_distribute_two_tokens_per_player(self) -> None:
        self.system.prepare()
        self.system.open_first_interstice()
        self.system.open_interstice(2, TerrainOwner.WHITE)
        self.assertEqual(len(self.system.player_tokens[TerrainOwner.WHITE]), 7)
        self.assertEqual(len(self.system.player_tokens[TerrainOwner.BLACK]), 7)

    def test_captured_terrain_numbers_no_longer_score(self) -> None:
        self.board.assign_element(2, 2, Element.FIRE)
        cell = self.board.cell(2, 2)
        cell.terrain_number = 5
        cell.terrain_owner = TerrainOwner.BLACK
        self.assertNotEqual(TerrainStateCapture.scores(self.board)[Element.FIRE], 0)
        self.board.capture_zone(cell.zone_id or "", TerrainOwner.BLACK)
        self.assertEqual(TerrainStateCapture.scores(self.board)[Element.FIRE], 0)


if __name__ == "__main__":
    unittest.main()
