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


if __name__ == "__main__":
    unittest.main()
