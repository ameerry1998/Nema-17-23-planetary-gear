"""Codex (secondary agent, 2026-10-21): check torque error bounds and overhung bearing equilibrium."""
import json
from pathlib import Path
import unittest
from brake_math import torque_interval, report


class BrakeTest(unittest.TestCase):
    def test_separate_moment_arms(self):
        r = torque_interval(100, 40, 50, 60, 0, 0)
        self.assertAlmostEqual(r['nominal_Nm'], 2.6)
        self.assertEqual(r['nominal_Nm'], r['upper_Nm'])

    def test_error_extrema(self):
        r = torque_interval(100, 40, 50, 50, 1, 2)
        self.assertAlmostEqual(r['lower_Nm'], (99 * 48 - 41 * 52) / 1000)
        self.assertAlmostEqual(r['upper_Nm'], (101 * 52 - 39 * 48) / 1000)

    def test_bearing_equilibrium(self):
        c = json.loads((Path(__file__).parent / 'brake-rotor.json').read_text())
        r = report(c); b = r['radial_screen']
        self.assertAlmostEqual(b['outer_bearing_reaction_N'] - b['inner_bearing_opposing_reaction_N'], c['total_tension_limit_N'])
        self.assertAlmostEqual(b['outer_bearing_reaction_N'] * 16, c['total_tension_limit_N'] * (r['positions']['rope_plane_mm'] - 147.5))
        self.assertAlmostEqual(r['running_brake_power_W'], 31.4159265359)
        c['total_tension_limit_N'] = 100
        with self.assertRaises(ValueError):
            report(c)


if __name__ == '__main__':
    unittest.main()
