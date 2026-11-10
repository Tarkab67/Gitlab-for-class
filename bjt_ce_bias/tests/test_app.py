import unittest

from bjt_ce_bias.app import app
from bjt_ce_bias.formatting import format_quantity


class TestPageShell(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_renders_three_cards_and_form(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("Lab 02: BJT DC Bias Web App", html)
        self.assertIn("Input Parameters", html)
        self.assertIn("Circuit", html)
        self.assertIn("DC Bias Results", html)
        for field in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{field}"', html)
        self.assertIn("style.css", html)

    def test_format_quantity_units(self):
        self.assertEqual(format_quantity("ic", 1.22985e-3), ("1.230", "mA"))
        self.assertEqual(format_quantity("ib", 12.2985e-6), ("12.30", "µA"))
        self.assertEqual(format_quantity("vce", 8.05218), ("8.052", "V"))
        self.assertEqual(format_quantity("rc", 2200.0), ("2.2", "kΩ"))


VALID_FORM = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "beta": "100", "vbe": "0.70",
    "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm", "re_unit": "kohm",
}


class TestResultsPage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_post_valid_renders_all_quantities(self):
        html = self.client.post("/", data=VALID_FORM).get_data(as_text=True)
        for label, value in (("VB", "1.942"), ("VE", "1.242"), ("VC", "9.294"),
                             ("VCE", "8.052"), ("IB", "12.30"), ("IC", "1.230"), ("IE", "1.242")):
            self.assertIn(label, html)
            self.assertIn(value, html)
        self.assertIn("Active region", html)
        self.assertIn("region-active", html)

    def test_post_invalid_shows_field_errors_and_keeps_input(self):
        bad = {**VALID_FORM, "vcc": "abc"}
        html = self.client.post("/", data=bad).get_data(as_text=True)
        self.assertIn("must be a number", html)
        self.assertIn('value="abc"', html)
        self.assertIn('value="kohm" selected', html)
        self.assertNotIn("region-active", html)

    def test_saturation_renders_warning_class(self):
        html = self.client.post("/", data={**VALID_FORM, "rc": "10"}).get_data(as_text=True)
        self.assertIn("region-saturation", html)
        self.assertIn("overstates IC", html)


if __name__ == "__main__":
    unittest.main()
