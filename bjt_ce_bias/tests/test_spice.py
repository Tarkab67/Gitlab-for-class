import unittest

from bjt_ce_bias.bjt import BiasInputs, solve_bias
from bjt_ce_bias import spice

INPUTS = BiasInputs(12.0, 100e3, 22e3, 2.2e3, 1e3, 100.0, 0.7)


class TestNetlist(unittest.TestCase):
    def test_netlist_contains_components_and_model(self):
        net = spice.build_netlist(INPUTS)
        for line in ("R1 vcc b 100000.0", "R2 b 0 22000.0", "RC vcc c 2200.0",
                     "RE e 0 1000.0", "Q1 c b e QNPN", "BF=100", ".control", "op"):
            self.assertIn(line, net)

    def test_missing_ngspice_is_reported_not_raised(self):
        self.assertFalse(spice.available() and spice.find_ngspice() is None)
        if not spice.available():
            self.assertIsNone(spice.run_operating_point(INPUTS))

    @unittest.skipUnless(spice.available(), "ngspice not installed")
    def test_spice_agrees_with_closed_form(self):
        result = spice.run_operating_point(INPUTS)
        self.assertIsNotNone(result)
        agree, diff = spice.compare(solve_bias(INPUTS), result)
        self.assertTrue(agree, f"relative difference {diff:.3f}")
        self.assertLess(diff, 0.15)

    @unittest.skipUnless(spice.available(), "ngspice not installed")
    def test_spice_operating_point_is_physical(self):
        result = spice.run_operating_point(INPUTS)
        self.assertGreater(result.ic, 0.5e-3)
        self.assertLess(result.ic, 3e-3)
