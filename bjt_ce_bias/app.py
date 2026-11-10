"""Flask routes. All engineering lives in bjt.py / spice.py."""

from __future__ import annotations

from flask import Flask, render_template, request

from bjt_ce_bias import spice
from bjt_ce_bias.bjt import cross_check, nodal_solve, parse_inputs, solve_bias
from bjt_ce_bias.formatting import format_compact, format_quantity

DEFAULT_FORM = {
    "vcc": "12.0",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1.0",
    "beta": "100",
    "vbe": "0.70",
    "r1_unit": "kohm",
    "r2_unit": "kohm",
    "rc_unit": "kohm",
    "re_unit": "kohm",
}

RESULT_ROWS = (
    ("VB", "vb"),
    ("VE", "ve"),
    ("VC", "vc"),
    ("VCE", "vce"),
    ("IB", "ib"),
    ("IC", "ic"),
    ("IE", "ie"),
)

app = Flask(__name__)


def _result_rows(result):
    return [
        (label, *format_quantity(field, getattr(result, field)))
        for label, field in RESULT_ROWS
    ]


def _schematic(inputs):
    labels = {}
    for field in ("vcc", "r1", "r2", "rc", "re"):
        display, unit = format_compact(field, getattr(inputs, field))
        labels[field] = f"{display} {unit}".strip()
    labels["beta"] = f"{inputs.beta:.6g}"
    return labels


def _pair(field, value):
    display, unit = format_quantity(field, value)
    return f"{display} {unit}"


def _verdict_context(result, inputs):
    if result.region == "cutoff":
        return {
            "nodal": None, "nodal_agrees": None, "nodal_diff": None,
            "nodal_view": {}, "spice": None, "spice_agrees": None,
            "spice_diff": None, "spice_view": {},
            "spice_available": spice.available(), "spice_error": False,
        }

    nodal = nodal_solve(inputs)
    nodal_agrees, nodal_diff = cross_check(result, nodal)
    nodal_view = {"ic": _pair("ic", nodal.ic), "vce": _pair("vce", nodal.vce)}

    spice_result = None
    spice_agrees = None
    spice_diff = None
    spice_error = False
    spice_view = {}
    spice_available = spice.available()
    if spice_available:
        try:
            spice_result = spice.run_operating_point(inputs)
            if spice_result is None:
                spice_error = True
            else:
                spice_agrees, spice_diff = spice.compare(result, spice_result)
                spice_view = {
                    "vbe": _pair("vbe", spice_result.vbe),
                    "ic": _pair("ic", spice_result.ic),
                    "vce": _pair("vce", spice_result.vce),
                }
        except Exception:
            spice_error = True

    return {
        "nodal": nodal,
        "nodal_agrees": nodal_agrees,
        "nodal_diff": nodal_diff,
        "nodal_view": nodal_view,
        "spice": spice_result,
        "spice_agrees": spice_agrees,
        "spice_diff": spice_diff,
        "spice_view": spice_view,
        "spice_available": spice_available,
        "spice_error": spice_error,
    }


def _schematic_inputs(form, errors):
    """Keep every valid typed value; fall back per field only for rejected ones."""
    candidate = dict(form)
    for field in errors:
        if field in DEFAULT_FORM:
            candidate[field] = DEFAULT_FORM[field]
    inputs, _ = parse_inputs(candidate)
    if inputs is None:
        inputs, _ = parse_inputs(DEFAULT_FORM)
    return inputs


def _render(form, errors, result=None, inputs=None):
    if inputs is None:
        inputs, _ = parse_inputs(DEFAULT_FORM)
    checks = _verdict_context(result, inputs) if result is not None else {}
    return render_template(
        "index.html",
        form=form,
        errors=errors,
        result=result,
        rows=_result_rows(result) if result is not None else [],
        schematic=_schematic(inputs),
        **checks,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return _render(DEFAULT_FORM, {})

    form = {**DEFAULT_FORM, **request.form.to_dict()}
    inputs, errors = parse_inputs(form)
    if inputs is None:
        return _render(form, errors, inputs=_schematic_inputs(form, errors))
    try:
        result = solve_bias(inputs)
    except ValueError:
        message = "These values do not produce a finite operating point; check the magnitudes."
        return _render(form, {"form": message}, inputs=inputs)
    return _render(form, {}, result, inputs)


if __name__ == "__main__":
    app.run(debug=True)
