import math
import unittest

from bjt_ce_bias.bjt import BiasInputs, parse_inputs

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
