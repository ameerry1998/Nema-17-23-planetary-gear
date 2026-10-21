"""Codex (secondary agent, 2026-10-21): independent unit/scaling and overhung-beam checks."""
import math
import unittest
from dynamic_review import orbital_force, beam_bounds


class DynamicTests(unittest.TestCase):
    def test_centripetal_units_and_scaling(self):
        rpm = 60 / math.tau
        self.assertAlmostEqual(orbital_force(1000,1000,rpm),1)
        self.assertAlmostEqual(orbital_force(1000,1000,rpm*2),4)
        self.assertAlmostEqual(orbital_force(2000,1000,rpm),2)
        self.assertEqual(orbital_force(10,20,0),0)

    def test_center_load_and_overhang(self):
        centered = beam_bounds(100,50,50,0,100)
        self.assertAlmostEqual(centered['moment_bound_Nmm'],2500)
        self.assertAlmostEqual(centered['left_reaction_bound_N'],50)
        overhang = beam_bounds(100,120,120,0,100)
        self.assertAlmostEqual(overhang['moment_bound_Nmm'],2000)
        self.assertAlmostEqual(overhang['left_reaction_bound_N'],20)
        self.assertAlmostEqual(overhang['right_reaction_bound_N'],120)

    def test_extent_bounds_contain_point_load_sweep(self):
        b=beam_bounds(100,-30,140,0,100)
        for x in range(-30,141):
            one=beam_bounds(100,x,x,0,100)
            for key in b:
                self.assertLessEqual(one[key],b[key]+1e-9)

    def test_invalid_inputs_rejected(self):
        for mass in [-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):
                orbital_force(mass,20,1000)
        with self.assertRaises(ValueError):
            beam_bounds(1,0,10,5,5)


if __name__=='__main__':
    unittest.main()
