"""Codex (secondary agent, 2026-10-21): guard static-test units, instrument limits and input-lock geometry."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from fixture_math import dimensions, lever_torque, limited_reading

ROOT = Path(__file__).resolve().parent


class FixtureTest(unittest.TestCase):
    def test_force_angle_and_units(self):
        self.assertAlmostEqual(lever_torque(2, 100), 1.96133)
        self.assertAlmostEqual(lever_torque(2, 100, 30), .980665)

    def test_instrument_upper_bound(self):
        reading = limited_reading(5, .04, .1)
        self.assertAlmostEqual(reading * 1.04 + .1, 5)
        with self.assertRaises(ValueError):
            limited_reading(5, 0, 6)

    def test_lock_geometry_rejects_bad_placement(self):
        config = json.loads((ROOT / 'static-fixture.json').read_text())
        drive = json.loads((ROOT / 'drive.json').read_text())
        self.assertAlmostEqual(dimensions(config, drive)['hub_shaft_overlap_mm'], 7.8)
        bad = deepcopy(config)
        bad['plate_front_z_mm'] -= 3
        with self.assertRaises(ValueError):
            dimensions(bad, drive)


if __name__ == '__main__':
    unittest.main()
