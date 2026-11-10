"""Pure engineering logic for the BJT common-emitter DC bias lab.

No Flask, no subprocess, no formatting: everything here is SI (V, ohm, A).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

RESISTOR_FIELDS = ("r1", "r2", "rc", "re")
UNIT_SCALE = {"ohm": 1.0, "kohm": 1e3}
DEFAULT_UNIT = "kohm"


@dataclass(frozen=True)
class BiasInputs:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


def _number(raw: Mapping[str, str], field: str, errors: dict[str, str]) -> float | None:
    text = (raw.get(field) or "").strip()
    try:
        value = float(text)
    except (TypeError, ValueError):
        errors[field] = "must be a number"
        return None
    if not math.isfinite(value):
        errors[field] = "must be a number"
        return None
    return value


def _scale(raw: Mapping[str, str], field: str) -> float:
    unit = (raw.get(f"{field}_unit") or DEFAULT_UNIT).strip().lower()
    return UNIT_SCALE.get(unit, UNIT_SCALE[DEFAULT_UNIT])


def parse_inputs(raw: Mapping[str, str]) -> tuple[BiasInputs | None, dict[str, str]]:
    """Parse and validate raw form data, scaling resistors to ohms."""
    errors: dict[str, str] = {}

    vcc = _number(raw, "vcc", errors)
    if vcc is not None and vcc <= 0:
        errors["vcc"] = "VCC must be greater than 0 V"

    resistors: dict[str, float] = {}
    for field in RESISTOR_FIELDS:
        value = _number(raw, field, errors)
        if value is None:
            continue
        ohms = value * _scale(raw, field)
        if ohms <= 0:
            errors[field] = f"{field.upper()} must be greater than 0 Ω"
            continue
        resistors[field] = ohms

    beta = _number(raw, "beta", errors)
    if beta is not None and beta <= 1:
        errors["beta"] = "beta must be greater than 1"

    vbe = _number(raw, "vbe", errors)
    if vbe is not None and not (0.0 <= vbe <= 1.0):
        errors["vbe"] = "VBE must be between 0 and 1 V"

    if errors:
        return None, errors

    return (
        BiasInputs(
            vcc=vcc,
            r1=resistors["r1"],
            r2=resistors["r2"],
            rc=resistors["rc"],
            re=resistors["re"],
            beta=beta,
            vbe=vbe,
        ),
        {},
    )
