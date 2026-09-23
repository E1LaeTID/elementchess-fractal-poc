import unittest
from math import pi

from elementchess.time_engine import (
    IncrementalTimeEngine,
    WHEEL_EARTH,
    WHEEL_FIRE,
    WHEEL_GAME,
    WHEEL_ICE,
    WHEEL_MAGMAT,
    WHEEL_THUNDER,
    WHEEL_WATER,
    WHEEL_WIND,
    WHEEL_WOOD,
)


class IncrementalTimeEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = IncrementalTimeEngine()

    def test_every_component_uses_the_same_tooth_pitch(self) -> None:
        for state in self.engine.states.values():
            self.assertAlmostEqual(state.spec.tooth_pitch, 25 * pi)

    def test_requested_tooth_counts_and_angles_are_normalized(self) -> None:
        game = self.engine.states[WHEEL_GAME].spec
        water = self.engine.states[WHEEL_WATER].spec
        earth = self.engine.states[WHEEL_EARTH].spec
        self.assertEqual((game.radius, game.tooth_count, game.tooth_angle), (800, 64, pi / 32))
        self.assertEqual((water.radius, water.tooth_count, water.tooth_angle), (200, 16, pi / 8))
        self.assertEqual((earth.radius, earth.tooth_count, earth.tooth_angle), (1200, 96, pi / 48))
        self.assertEqual(earth.rim_width, 400)

    def test_main_wheel_cannot_be_controlled_manually(self) -> None:
        self.assertNotIn(WHEEL_GAME, self.engine.controllable_identifiers)
        with self.assertRaises(PermissionError):
            self.engine.rotate_manual(WHEEL_GAME, 1)

    def test_main_wheel_advances_and_drives_the_complete_train(self) -> None:
        before = {key: state.position for key, state in self.engine.states.items()}
        step = self.engine.advance_main()
        self.assertEqual(step.identifier, WHEEL_GAME)
        self.assertEqual(self.engine.states[WHEEL_GAME].position, before[WHEEL_GAME] + 1)
        wave = {item.identifier: item.delta_teeth for item in self.engine.last_wave}
        self.assertEqual(wave[WHEEL_WATER], -1)
        self.assertEqual(wave[WHEEL_FIRE], -1)
        self.assertEqual(wave[WHEEL_WIND], -1)
        self.assertEqual(wave[WHEEL_WOOD], -1)
        self.assertEqual(wave[WHEEL_MAGMAT], 1)
        self.assertEqual(wave[WHEEL_THUNDER], 1)
        self.assertEqual(set(wave), set(self.engine.states))

    def test_all_eight_elements_can_be_controlled_manually(self) -> None:
        self.assertEqual(
            set(self.engine.controllable_identifiers),
            set(self.engine.states) - {WHEEL_GAME},
        )
        self.assertEqual(len(self.engine.controllable_identifiers), 8)

    def test_each_direct_contact_reverses_the_rotation(self) -> None:
        wave = {step.identifier: step.delta_teeth for step in self.engine.rotate_manual(WHEEL_WATER, 1)}
        self.assertEqual(wave[WHEEL_WATER], 1)
        self.assertEqual(wave[WHEEL_GAME], -1)
        self.assertEqual(wave[WHEEL_WIND], 1)

    def test_positions_wrap_according_to_each_wheel_tooth_count(self) -> None:
        self.engine.rotate_manual(WHEEL_WATER, -1)
        self.assertEqual(self.engine.states[WHEEL_WATER].position, 15)
        self.assertEqual(self.engine.states[WHEEL_GAME].position, 1)

    def test_ice_behaves_as_a_linear_rack(self) -> None:
        self.engine.rotate_manual(WHEEL_ICE, 1, increments=3)
        self.assertEqual(self.engine.states[WHEEL_ICE].position, 3)
        self.assertEqual(self.engine.states[WHEEL_EARTH].position, 93)

    def test_a_propagation_wave_updates_each_component_once(self) -> None:
        wave = self.engine.rotate_manual(WHEEL_WIND, 1)
        self.assertEqual(len(wave), len(self.engine.states))
        self.assertEqual(len({step.identifier for step in wave}), len(wave))


if __name__ == "__main__":
    unittest.main()
