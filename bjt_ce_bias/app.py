"""Flask routes. All engineering lives in bjt.py / spice.py."""

from __future__ import annotations

from flask import Flask, render_template

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

app = Flask(__name__)


@app.get("/")
def index():
    return render_template(
        "index.html",
        form=DEFAULT_FORM,
        errors={},
        result=None,
    )


if __name__ == "__main__":
    app.run(debug=True)
