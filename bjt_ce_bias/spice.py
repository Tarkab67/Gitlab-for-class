"""ngspice batch cross-check. Optional: every entry point degrades to None."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from bjt_ce_bias.bjt import BiasInputs, BiasResult, classify_vce

_NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_VALUE_RE = r"\s*=\s*(" + _NUMBER + ")"

TIMEOUT_S = 10.0


@dataclass(frozen=True)
class SpiceResult:
    vb: float
    ve: float
    vc: float
    vce: float
    ib: float
    ic: float
    ie: float
    vbe: float


def _tools_root() -> Path:
    return Path(__file__).resolve().parent.parent


def find_ngspice() -> str | None:
    """NGSPICE_BIN -> PATH -> bundled .tools/ copy."""
    override = os.environ.get("NGSPICE_BIN")
    if override:
        path = Path(override)
        if path.is_file():
            return str(path)
        return shutil.which(override)
    found = shutil.which("ngspice")
    if found:
        return found
    for pattern in (".tools/ngspice*/**/ngspice_con.exe", ".tools/**/ngspice_con.exe"):
        for candidate in sorted(_tools_root().glob(pattern)):
            if candidate.is_file():
                return str(candidate)
    return None


def available() -> bool:
    return find_ngspice() is not None


def build_netlist(inputs: BiasInputs) -> str:
    return "\n".join(
        [
            "* BJT common-emitter voltage-divider bias - DC operating point",
            f"VCC vcc 0 {inputs.vcc:.6g}",
            f"R1 vcc b {inputs.r1:.1f}",
            f"R2 b 0 {inputs.r2:.1f}",
            f"RC vcc c {inputs.rc:.1f}",
            f"RE e 0 {inputs.re:.1f}",
            "Q1 c b e QNPN",
            f".model QNPN NPN (BF={inputs.beta:g} IS=1e-14 VAF=100)",
            ".control",
            "op",
            "print v(b) v(e) v(c) i(vcc)",
            ".endc",
            ".end",
            "",
        ]
    )


def _match(text: str, name: str) -> float | None:
    match = re.search(name + _VALUE_RE, text, re.IGNORECASE)
    if match is None:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _parse(text: str, re_ohms: float) -> SpiceResult | None:
    vb = _match(text, r"v\(b\)")
    ve = _match(text, r"v\(e\)")
    vc = _match(text, r"v\(c\)")
    i_vcc = _match(text, r"i\(vcc\)")
    if None in (vb, ve, vc, i_vcc) or re_ohms <= 0.0:
        return None
    ic = -i_vcc
    ie = ve / re_ohms
    return SpiceResult(
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vc - ve,
        ib=ie - ic,
        ic=ic,
        ie=ie,
        vbe=vb - ve,
    )


def run_operating_point(inputs: BiasInputs, timeout_s: float = TIMEOUT_S) -> SpiceResult | None:
    exe = find_ngspice()
    if exe is None:
        return None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            netlist = Path(tmp) / "bias.cir"
            netlist.write_text(build_netlist(inputs), encoding="ascii")
            completed = subprocess.run(
                [exe, "-b", str(netlist)],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return _parse(completed.stdout + "\n" + completed.stderr, inputs.re)


def compare(
    closed: BiasResult,
    spice_result: SpiceResult,
    rel_tol: float = 0.15,
) -> tuple[bool, float]:
    """Agreement on IC and VCE; the region must also match."""
    worst = 0.0
    for field in ("ic", "vce"):
        a = getattr(closed, field)
        b = getattr(spice_result, field)
        worst = max(worst, abs(a - b) / max(abs(a), abs(b), 1e-30))
    region_ok = closed.region == classify_vce(spice_result.vce)
    return region_ok and worst <= rel_tol, worst
