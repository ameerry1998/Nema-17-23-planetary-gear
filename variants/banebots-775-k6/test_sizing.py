"""Codex (secondary agent, 2026-10-21): check units, energy and invalid design rejection independently."""
import copy
import json
import math
from pathlib import Path
import unittest
from size_drive import evaluate, geometry
from connection_review import flat_contact


class SizingTests(unittest.TestCase):
    def setUp(self):
        self.c = json.loads(Path(__file__).with_name('drive.json').read_text())

    def test_power_and_speed_conservation(self):
        r = evaluate(self.c)
        self.assertEqual(r['overall_ratio'], 100)
        for case in r['cases'].values():
            motor_power = case['motor_nm'] * case['motor_rpm'] * 2 * math.pi / 60
            self.assertAlmostEqual(case['output_mechanical_w'], motor_power * r['assumed_overall_efficiency'])
        self.assertAlmostEqual(r['cases']['peak']['output_mechanical_w'], 52.35987756, places=6)

    def test_load_doubling_and_contact_sqrt(self):
        before = evaluate(self.c)
        self.c['targets']['brief_peak_nm'] *= 2
        after = evaluate(self.c)
        for b, a in zip(before['stages'], after['stages']):
            b, a = b['cases']['peak'], a['cases']['peak']
            self.assertAlmostEqual(a['sun_lewis_screen_mpa'] / b['sun_lewis_screen_mpa'], 2)
            self.assertAlmostEqual(a['external_mesh_hertz_pitch_point_screen_mpa'] / b['external_mesh_hertz_pitch_point_screen_mpa'], math.sqrt(2))

    def test_carrier_frame_speed(self):
        r = evaluate(self.c)
        self.assertEqual(r['stages'][0]['input_rpm'], 10000)
        self.assertEqual(r['stages'][0]['carrier_rpm'], 2000)
        self.assertAlmostEqual(r['stages'][0]['pitch_speed_in_carrier_frame_m_s'], 6.031857895, places=6)
        self.assertAlmostEqual(r['stages'][2]['planet_bearing_relative_rpm'], 300)

    def test_nonassemblable_planet_spacing_rejected(self):
        self.c['stages'][2]['planets'] = 5
        with self.assertRaises(AssertionError):
            evaluate(self.c)

    def test_wrong_pin_length_rejected(self):
        self.c['stages'][1]['shoulder_length_mm'] += 5
        with self.assertRaises(AssertionError):
            evaluate(self.c)

    def test_unsupported_pressure_angle_rejected(self):
        self.c['geometry']['pressure_angle_deg'] = 25
        with self.assertRaises(AssertionError):
            evaluate(self.c)

    def test_impossible_efficiency_rejected(self):
        self.c['stages'][0]['efficiency_assumed'] = 1.1
        with self.assertRaises(AssertionError):
            evaluate(self.c)

    def test_125_voltage_shortfall_is_exposed(self):
        row = evaluate(self.c)['ratio_comparison_at_target_rpm'][-1]
        self.assertFalse(row['fits_average_voltage_model'])

    def test_spacer_shield_contact_rejected(self):
        self.c['geometry']['planet_spacer_od_mm'] = 8
        with self.assertRaises(AssertionError):
            evaluate(self.c)

    def test_eccentric_spacer_shield_contact_rejected(self):
        self.c['geometry']['planet_spacer_od_mm'] = 6.35
        self.c['geometry']['planet_spacer_id_mm'] = 5.64
        with self.assertRaises(AssertionError):
            evaluate(self.c)

    def test_contact_moment_integration(self):
        pressure = flat_contact(5, 15, 2, faces=3)
        recovered_nmm = 3 * pressure * 15 * 2 ** 2 / 2
        self.assertAlmostEqual(recovered_nmm, 5000)
        self.assertAlmostEqual(flat_contact(5, 15, 2, faces=1), 3 * pressure)

    def test_contact_engagement_scaling(self):
        initial = flat_contact(5, 15, 2)
        self.assertAlmostEqual(flat_contact(5, 30, 2), initial / 2)
        self.assertAlmostEqual(flat_contact(5, 15, 4), initial / 4)


if __name__ == '__main__':
    unittest.main()
