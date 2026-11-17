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

VCE_SAT = 0.2

REGION_ACTIVE = "active"
REGION_SATURATION = "saturation"
REGION_CUTOFF = "cutoff"


@dataclass(frozen=True)
class BiasResult:
    vb: float
    ve: float
    vc: float
    vce: float
    ib: float
    ic: float
    ie: float
    region: str
    message: str


def classify_vce(vce: float) -> str:
    return REGION_SATURATION if vce < VCE_SAT else REGION_ACTIVE


def region_message(region: str, vce: float) -> str:
    if region == REGION_CUTOFF:
        return "Cutoff: the divider cannot forward-bias the base (transistor off)."
    if region == REGION_SATURATION:
        return "Saturation: VCE is below 0.2 V; the linear model overstates IC."
    return f"Active region approximation OK: VCE = {vce:.2f} V ≥ 0.2 V."


def solve_bias_forward(inputs: BiasInputs) -> BiasResult:
    """Forward-active operating point of the voltage-divider bias.

    The currents are computed from the collector side so that very large
    beta values (where beta * IB would overflow) stay finite. The cutoff
    case is reported as-is (no zeroing); the Lab 02 wrapper adds the clamp.
    """
    vbb = inputs.vcc * inputs.r2 / (inputs.r1 + inputs.r2)
    rb = 1.0 / (1.0 / inputs.r1 + 1.0 / inputs.r2)
    ic = (vbb - inputs.vbe) / (rb / inputs.beta + (1.0 + 1.0 / inputs.beta) * inputs.re)

    if not math.isfinite(ic):
        raise ValueError("operating point is not finite; check the input magnitudes")

    ib = ic / inputs.beta
    ie = ic + ib
    ve = ie * inputs.re
    vb = ve + inputs.vbe
    vc = inputs.vcc - ic * inputs.rc
    vce = vc - ve
    if not all(math.isfinite(v) for v in (vb, ve, vc, vce, ib, ie)):
        raise ValueError("operating point is not finite; check the input magnitudes")
    region = REGION_CUTOFF if ic <= 0.0 else classify_vce(vce)
    return BiasResult(
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        ib=ib,
        ic=ic,
        ie=ie,
        region=region,
        message=region_message(region, vce),
    )


def solve_bias(inputs: BiasInputs) -> BiasResult:
    """Lab 02 solver: forward-active point, clamped to zero in cutoff.

    Kept for the existing tests and the divider cross-check.
    """
    forward = solve_bias_forward(inputs)
    if forward.region != REGION_CUTOFF:
        return forward
    return BiasResult(
        vb=inputs.vcc,
        ve=inputs.vcc,
        vc=inputs.vcc,
        vce=inputs.vcc,
        ib=0.0,
        ic=0.0,
        ie=0.0,
        region=REGION_CUTOFF,
        message=region_message(REGION_CUTOFF, inputs.vcc),
    )


def warning_for(ib: float, vce: float) -> str | None:
    """Warn when the forward-active assumption is outside its model limit."""
    reasons = []
    if ib <= 0:
        reasons.append("IB ≤ 0")
    if vce <= VCE_SAT:
        reasons.append(f"VCE ≤ {VCE_SAT:.1f} V")
    if not reasons:
        return None
    return ("The forward-active model may not apply: " + ", ".join(reasons)
            + ". Cutoff/saturation are not calculated.")


def _operating_point(
    mode: str,
    *,
    vcc: float,
    rc: float,
    beta: float,
    vbe: float,
    ib: float,
    re: float,
) -> dict:
    """Build the shared result dict from a forward-active base current."""
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve
    if not all(math.isfinite(v) for v in (vb, ve, vc, vce, ib, ic, ie)):
        raise ValueError("operating point is not finite; check the input magnitudes")
    region = REGION_CUTOFF if ib <= 0.0 else classify_vce(vce)
    return {
        "mode": mode,
        "vb_v": vb,
        "ve_v": ve,
        "vc_v": vc,
        "vce_v": vce,
        "ib_a": ib,
        "ic_ma": ic * 1e3,
        "ie_ma": ie * 1e3,
        "warning": warning_for(ib, vce),
        "region": region,
        "message": region_message(region, vce),
    }


def solve_fixed_bias(inputs: FixedBiasInputs) -> dict:
    """Fixed bias: base resistor from VCC, emitter grounded."""
    ib = (inputs.vcc - inputs.vbe) / inputs.rb
    return _operating_point(
        "fixed",
        vcc=inputs.vcc,
        rc=inputs.rc,
        beta=inputs.beta,
        vbe=inputs.vbe,
        ib=ib,
        re=0.0,
    )


def solve_emitter_bias(inputs: EmitterBiasInputs) -> dict:
    """Emitter bias: RB from VCC to base, RE from emitter to ground."""
    ib = ((inputs.vcc - inputs.vbe) / inputs.beta) / (
        inputs.rb / inputs.beta + inputs.re * (1.0 + 1.0 / inputs.beta)
    )
    return _operating_point(
        "emitter",
        vcc=inputs.vcc,
        rc=inputs.rc,
        beta=inputs.beta,
        vbe=inputs.vbe,
        ib=ib,
        re=inputs.re,
    )


def solve_operating_point(
    mode: str, inputs: BiasInputs | FixedBiasInputs | EmitterBiasInputs
) -> dict:
    """Dispatch to the selected bias mode; never fall back silently."""
    if mode == "divider":
        forward = solve_bias_forward(inputs)
        return _operating_point(
            "divider",
            vcc=inputs.vcc,
            rc=inputs.rc,
            beta=inputs.beta,
            vbe=inputs.vbe,
            ib=forward.ib,
            re=inputs.re,
        )
    if mode == "fixed":
        return solve_fixed_bias(inputs)
    if mode == "emitter":
        return solve_emitter_bias(inputs)
    raise ValueError(f"unknown bias mode: {mode}")


CROSS_FIELDS = ("ib", "ic", "ie", "vce")


def _solve_linear(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting (stdlib only)."""
    n = len(matrix)
    a = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if a[pivot][col] == 0.0:
            raise ValueError("singular system")
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
        pivot_value = a[col][col]
        for row in range(col + 1, n):
            factor = a[row][col] / pivot_value
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                a[row][c] -= factor * a[col][c]
    solution = [0.0] * n
    for row in range(n - 1, -1, -1):
        total = a[row][n] - sum(a[row][c] * solution[c] for c in range(row + 1, n))
        solution[row] = total / a[row][row]
    return solution


def nodal_solve(inputs: BiasInputs) -> BiasResult:
    """Independent solution: KCL at the three nodes, solved as a 6x6 system.

    Unknowns are ordered [IB, IC, IE, VB, VC, VE].
    """
    g1 = 1.0 / inputs.r1
    g2 = 1.0 / inputs.r2
    gc = 1.0 / inputs.rc
    ge = 1.0 / inputs.re
    beta = inputs.beta

    rows = [
        [-beta, 1.0, 0.0, 0.0, 0.0, 0.0],
        [-(beta + 1.0), 0.0, 1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0, 0.0, -1.0],
        [-1.0, 0.0, 0.0, -(g1 + g2), 0.0, 0.0],
        [0.0, -1.0, 0.0, 0.0, -gc, 0.0],
        [0.0, 0.0, -1.0, 0.0, 0.0, ge],
    ]
    rhs = [0.0, 0.0, inputs.vbe, -inputs.vcc * g1, -inputs.vcc * gc, 0.0]

    ib, ic, ie, vb, vc, ve = _solve_linear(rows, rhs)
    return BiasResult(
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vc - ve,
        ib=ib,
        ic=ic,
        ie=ie,
        region="",
        message="nodal",
    )


def cross_check(closed: BiasResult, nodal: BiasResult, rel_tol: float = 1e-9) -> tuple[bool, float]:
    """Return (agree, worst relative difference) over currents and VCE.

    Any non-finite operand counts as a hard disagreement, never a pass.
    """
    worst = 0.0
    for field in CROSS_FIELDS:
        a = getattr(closed, field)
        b = getattr(nodal, field)
        if not (math.isfinite(a) and math.isfinite(b)):
            return False, math.inf
        denominator = max(abs(a), abs(b), 1e-30)
        worst = max(worst, abs(a - b) / denominator)
    return worst <= rel_tol, worst




@dataclass(frozen=True)
class BiasInputs:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class FixedBiasInputs:
    vcc: float
    rb: float
    rc: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class EmitterBiasInputs:
    vcc: float
    rb: float
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


def _scale(raw: Mapping[str, str], field: str, errors: dict[str, str]) -> float | None:
    unit = (raw.get(f"{field}_unit") or DEFAULT_UNIT).strip().lower()
    scale = UNIT_SCALE.get(unit)
    if scale is None:
        errors[f"{field}_unit"] = "unit must be ohm or kohm"
    return scale


def _parse_common(
    raw: Mapping[str, str], errors: dict[str, str]
) -> tuple[float | None, float | None, float | None]:
    """Parse VCC, beta, and VBE shared by every bias mode."""
    vcc = _number(raw, "vcc", errors)
    if vcc is not None and vcc <= 0:
        errors["vcc"] = "VCC must be greater than 0 V"

    beta = _number(raw, "beta", errors)
    if beta is not None and beta <= 1:
        errors["beta"] = "beta must be greater than 1"

    vbe = _number(raw, "vbe", errors)
    if vbe is not None and not (0.0 <= vbe <= 1.0):
        errors["vbe"] = "VBE must be between 0 and 1 V"
    return vcc, beta, vbe


def _parse_resistors(
    raw: Mapping[str, str], errors: dict[str, str], fields: tuple[str, ...]
) -> dict[str, float]:
    """Parse the resistor fields a mode needs and scale them to ohms."""
    values: dict[str, float] = {}
    for field in fields:
        value = _number(raw, field, errors)
        if value is None:
            continue
        scale = _scale(raw, field, errors)
        if scale is None:
            continue
        ohms = value * scale
        if not math.isfinite(ohms):
            errors[field] = f"{field.upper()} is too large"
            continue
        if ohms <= 0:
            errors[field] = f"{field.upper()} must be greater than 0 Ω"
            continue
        values[field] = ohms
    return values


def parse_inputs(raw: Mapping[str, str]) -> tuple[BiasInputs | None, dict[str, str]]:
    """Parse and validate raw form data, scaling resistors to ohms."""
    errors: dict[str, str] = {}
    vcc, beta, vbe = _parse_common(raw, errors)
    resistors = _parse_resistors(raw, errors, RESISTOR_FIELDS)
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


def parse_fixed(raw: Mapping[str, str]) -> tuple[FixedBiasInputs | None, dict[str, str]]:
    """Parse the fixed-bias form (VCC, RB, RC, beta, VBE)."""
    errors: dict[str, str] = {}
    vcc, beta, vbe = _parse_common(raw, errors)
    resistors = _parse_resistors(raw, errors, ("rb", "rc"))
    if errors:
        return None, errors
    return (
        FixedBiasInputs(
            vcc=vcc,
            rb=resistors["rb"],
            rc=resistors["rc"],
            beta=beta,
            vbe=vbe,
        ),
        {},
    )


def parse_emitter(raw: Mapping[str, str]) -> tuple[EmitterBiasInputs | None, dict[str, str]]:
    """Parse the emitter-bias form (VCC, RB, RC, RE, beta, VBE)."""
    errors: dict[str, str] = {}
    vcc, beta, vbe = _parse_common(raw, errors)
    resistors = _parse_resistors(raw, errors, ("rb", "re", "rc"))
    if errors:
        return None, errors
    return (
        EmitterBiasInputs(
            vcc=vcc,
            rb=resistors["rb"],
            rc=resistors["rc"],
            re=resistors["re"],
            beta=beta,
            vbe=vbe,
        ),
        {},
    )
