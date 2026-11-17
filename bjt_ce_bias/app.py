"""Flask routes. All engineering lives in bjt.py / spice.py."""

from __future__ import annotations

from flask import Flask, render_template, request

from bjt_ce_bias import spice
from bjt_ce_bias.bjt import (
    cross_check,
    nodal_solve,
    parse_emitter,
    parse_fixed,
    parse_inputs,
    solve_bias_forward,
    solve_operating_point,
)
from bjt_ce_bias.formatting import format_compact, format_quantity

MODES = ("divider", "fixed", "emitter")
MODE_NAMES = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

DEFAULT_FORM = {
    "vcc": "12.0",
    "r1": "100",
    "r2": "22",
    "rb": "1000",
    "rc": "2.2",
    "re": "1.0",
    "beta": "100",
    "vbe": "0.70",
    "r1_unit": "kohm",
    "r2_unit": "kohm",
    "rb_unit": "kohm",
    "rc_unit": "kohm",
    "re_unit": "kohm",
}

app = Flask(__name__)


def _result_rows(result):
    return [
        ("VB", *format_quantity("vb", result["vb_v"])),
        ("VE", *format_quantity("ve", result["ve_v"])),
        ("VC", *format_quantity("vc", result["vc_v"])),
        ("VCE", *format_quantity("vce", result["vce_v"])),
        ("IB", *format_quantity("ib", result["ib_a"])),
        ("IC", f"{result['ic_ma']:.3f}", "mA"),
        ("IE", f"{result['ie_ma']:.3f}", "mA"),
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


def _render(mode, form, errors, result=None, inputs=None, forward=None):
    context = {
        "mode": mode,
        "mode_name": MODE_NAMES.get(mode, ""),
        "mode_options": tuple(MODE_NAMES.items()),
        "form": form,
        "errors": errors,
        "result": result,
        "rows": _result_rows(result) if result is not None else [],
    }
    if mode == "divider":
        if inputs is None:
            inputs, _ = parse_inputs(DEFAULT_FORM)
        context["schematic"] = _schematic(inputs)
        if forward is not None:
            context.update(_verdict_context(forward, inputs))
    return render_template("index.html", **context)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        mode = request.args.get("mode", "divider")
        if mode not in MODES:
            return _render(None, {}, {"form": f"Unknown bias mode: {mode}."}), 400
        return _render(mode, DEFAULT_FORM, {})

    mode = request.form.get("mode", "divider")
    if mode not in MODES:
        return _render(None, {}, {"form": f"Unknown bias mode: {mode}."}), 400

    form = {**DEFAULT_FORM, **request.form.to_dict()}
    if mode == "divider":
        inputs, errors = parse_inputs(form)
        schematic_inputs = _schematic_inputs(form, errors)
    elif mode == "fixed":
        inputs, errors = parse_fixed(form)
        schematic_inputs = None
    else:
        inputs, errors = parse_emitter(form)
        schematic_inputs = None

    if inputs is None:
        return _render(mode, form, errors, inputs=schematic_inputs)

    try:
        result = solve_operating_point(mode, inputs)
        forward = solve_bias_forward(inputs) if mode == "divider" else None
    except ValueError:
        message = "These values do not produce a finite operating point; check the magnitudes."
        return _render(mode, form, {"form": message}, inputs=schematic_inputs)

    return _render(
        mode,
        form,
        {},
        result,
        inputs=inputs if mode == "divider" else None,
        forward=forward,
    )


if __name__ == "__main__":
    app.run(debug=True)
