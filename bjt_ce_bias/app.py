"""Flask routes. All engineering lives in bjt.py / spice.py."""

from __future__ import annotations

from flask import Flask, render_template, request

from bjt_ce_bias.bjt import parse_inputs, solve_bias
from bjt_ce_bias.formatting import format_quantity

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


def _render(form, errors, result=None):
    return render_template(
        "index.html",
        form=form,
        errors=errors,
        result=result,
        rows=_result_rows(result) if result is not None else [],
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return _render(DEFAULT_FORM, {})

    form = {**DEFAULT_FORM, **request.form.to_dict()}
    inputs, errors = parse_inputs(form)
    if inputs is None:
        return _render(form, errors)
    return _render(form, {}, solve_bias(inputs))


if __name__ == "__main__":
    app.run(debug=True)
