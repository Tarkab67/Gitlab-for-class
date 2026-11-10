import math
import unittest

from bjt_ce_bias.bjt import BiasInputs, parse_inputs
from bjt_ce_bias.bjt import VCE_SAT, classify_vce, solve_bias
from bjt_ce_bias.bjt import BiasResult, cross_check, nodal_solve

DEFAULTS = BiasInputs(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3, re=1e3, beta=100.0, vbe=0.7)

GOOD = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "beta": "100", "vbe": "0.70",
    "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm", "re_unit": "kohm",
}


class TestParseInputs(unittest.TestCase):
    def test_parses_scaled_si_values(self):
        inputs, errors = parse_inputs(GOOD)
        self.assertEqual(errors, {})
        self.assertAlmostEqual(inputs.r1, 100_000.0)
        self.assertAlmostEqual(inputs.rc, 2_200.0)
        self.assertAlmostEqual(inputs.vbe, 0.70)

    def test_ohm_unit_is_not_scaled(self):
        inputs, errors = parse_inputs({**GOOD, "r1": "100", "r1_unit": "ohm"})
        self.assertEqual(errors, {})
        self.assertAlmostEqual(inputs.r1, 100.0)

    def test_rejects_non_finite(self):
        for bad in ("nan", "inf", "-inf", "1e400", ""):
            with self.subTest(bad=bad):
                inputs, errors = parse_inputs({**GOOD, "vcc": bad})
                self.assertIsNone(inputs)
                self.assertIn("vcc", errors)

    def test_rejects_out_of_range_values(self):
        cases = {"vcc": "0", "r1": "-5", "beta": "1", "vbe": "1.5"}
        for field, bad in cases.items():
            with self.subTest(field=field):
                inputs, errors = parse_inputs({**GOOD, field: bad})
                self.assertIsNone(inputs)
                self.assertIn(field, errors)

    def test_reports_every_bad_field_at_once(self):
        inputs, errors = parse_inputs({**GOOD, "vcc": "abc", "re": "0"})
        self.assertIsNone(inputs)
        self.assertEqual(set(errors), {"vcc", "re"})


class TestSolveBias(unittest.TestCase):
    def test_known_active_point(self):
        r = solve_bias(DEFAULTS)
        self.assertAlmostEqual(r.ib, 12.2985e-6, delta=1e-7)
        self.assertAlmostEqual(r.ic, 1.22985e-3, delta=1e-7)
        self.assertAlmostEqual(r.ie, 1.24215e-3, delta=1e-7)
        self.assertAlmostEqual(r.ve, 1.24215, delta=1e-4)
        self.assertAlmostEqual(r.vb, 1.94215, delta=1e-4)
        self.assertAlmostEqual(r.vc, 9.29433, delta=1e-4)
        self.assertAlmostEqual(r.vce, 8.05218, delta=1e-4)
        self.assertEqual(r.region, "active")

    def test_cutoff_when_divider_cannot_bias(self):
        r = solve_bias(BiasInputs(vcc=12.0, r1=100e3, r2=1e3, rc=4.7e3, re=1e3, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "cutoff")
        self.assertEqual((r.ib, r.ic, r.ie), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(r.vce, 12.0)

    def test_saturation_when_vce_below_threshold(self):
        r = solve_bias(BiasInputs(vcc=12.0, r1=100e3, r2=22e3, rc=10e3, re=1e3, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "saturation")
        self.assertLess(r.vce, VCE_SAT)

    def test_extreme_magnitudes_stay_finite(self):
        for r1, re_ in ((1e-3, 1e-3), (1e9, 1e9), (1e9, 1.0)):
            with self.subTest(r1=r1, re=re_):
                r = solve_bias(BiasInputs(12.0, r1, 22e3, 2.2e3, re_, 100.0, 0.7))
                for value in (r.vb, r.ve, r.vc, r.vce, r.ib, r.ic, r.ie):
                    self.assertTrue(math.isfinite(value))

    def test_huge_beta_is_handled(self):
        r = solve_bias(BiasInputs(12.0, 100e3, 22e3, 2.2e3, 1e3, 1e6, 0.7))
        self.assertIn(r.region, {"active", "saturation", "cutoff"})
        self.assertTrue(math.isfinite(r.ic))

    def test_saturation_boundary_is_strict(self):
        self.assertEqual(classify_vce(0.3), "active")
        self.assertEqual(classify_vce(0.2999999), "saturation")


class TestNodalSolve(unittest.TestCase):
    def test_matches_closed_form_on_active_case(self):
        closed = solve_bias(DEFAULTS)
        nodal = nodal_solve(DEFAULTS)
        agree, diff = cross_check(closed, nodal)
        self.assertTrue(agree)
        self.assertLess(diff, 1e-9)

    def test_nodal_solution_satisfies_kcl(self):
        nodal = nodal_solve(DEFAULTS)
        i_r1 = (12.0 - nodal.vb) / 100e3
        i_r2 = nodal.vb / 22e3
        self.assertAlmostEqual(i_r1 - i_r2, nodal.ib, delta=1e-12)
        self.assertAlmostEqual((12.0 - nodal.vc) / 2.2e3, nodal.ic, delta=1e-12)
        self.assertAlmostEqual(nodal.ve / 1e3, nodal.ie, delta=1e-12)

    def test_detects_a_wrong_solution(self):
        closed = solve_bias(DEFAULTS)
        nodal = nodal_solve(DEFAULTS)
        broken = BiasResult(**{**nodal.__dict__, "ic": nodal.ic * 1.01})
        agree, diff = cross_check(closed, broken)
        self.assertFalse(agree)
        self.assertGreater(diff, 1e-4)
