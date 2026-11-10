"""Display formatting. SI values in, (display, unit) out. No math here."""

from __future__ import annotations

VOLTAGE_FIELDS = {"vcc", "vbe", "vb", "ve", "vc", "vce"}
MICROAMP_FIELDS = {"ib"}
MILLIAMP_FIELDS = {"ic", "ie"}
RESISTOR_FIELDS = {"r1", "r2", "rc", "re"}


def format_quantity(quantity: str, value_si: float) -> tuple[str, str]:
    """Fixed precision for the results table."""
    if quantity in MICROAMP_FIELDS:
        return f"{value_si * 1e6:.2f}", "µA"
    if quantity in MILLIAMP_FIELDS:
        return f"{value_si * 1e3:.3f}", "mA"
    if quantity in RESISTOR_FIELDS:
        return f"{value_si / 1e3:.1f}", "kΩ"
    return f"{value_si:.3f}", "V"


def format_compact(quantity: str, value_si: float) -> tuple[str, str]:
    """Short labels for the schematic: 12 V, 100 kΩ, 2.2 kΩ."""
    if quantity in RESISTOR_FIELDS:
        return f"{value_si / 1e3:.6g}", "kΩ"
    if quantity in MICROAMP_FIELDS:
        return f"{value_si * 1e6:.6g}", "µA"
    if quantity in MILLIAMP_FIELDS:
        return f"{value_si * 1e3:.6g}", "mA"
    return f"{value_si:.6g}", "V"
