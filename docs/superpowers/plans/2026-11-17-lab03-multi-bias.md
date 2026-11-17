# Lab 03 Multi-mode BJT Bias Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Fixed Bias and Emitter Bias modes to the existing Flask divider-bias app without changing the Lab 02 divider results.

**Architecture:** All engineering stays in `bjt.py`: one forward-active solver shared by divider/fixed/emitter, a mode dispatcher returning a plain dict, and per-mode parsers. `app.py` selects the parser and solver with if/elif, renders only the active mode's fields, and returns an explicit error for unknown modes. The template gains a GET mode form, per-mode field blocks, a warning box, and keeps the divider badge/cross-check.

**Tech Stack:** Python 3, Flask, Jinja2, stdlib `math`/`dataclasses`, existing venv `.venv`, unittest suite already in the repo.

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`

## Global Constraints

- Equations live only in `bjt_ce_bias/bjt.py`; `app.py` and templates do no engineering math.
- No new `unittest` files and no Playwright script (Lab 03 sheet). Existing 37 tests must pass.
- `VCE_SAT = 0.2` for every mode; warning when `IB <= 0` or `VCE <= 0.2`.
- Divider A1 must stay IC 1.2299 mA / VCE 8.0522 V (IC `1.2298581462608458e-3`, VCE `8.052155350502685`).
- Unknown mode must return an explicit error, never render divider results.
- POST with no `mode` field means divider (keeps Lab 02 tests green).
- New modes show no circuit card and no nodal/SPICE panel; divider keeps both.
- Stack stays Flask + Jinja + stdlib; no new dependencies.
- Windows venv; test command:
  `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`
- Use `$env:PYTHONIOENCODING="utf-8"` for shell commands that print `Ω`/`µ`/`≤`.

## Review Focus

- A POST with an unknown or tampered `mode` value: expect an explicit 400 error page, never divider output.
- Divider pushed to cutoff or saturation: expect raw forward-active values plus the amber warning, no zeroed values, no crash.
- Fixed/Emitter with extreme values (tiny RB, huge beta): expect a form-level finite check error, never `nan`/`inf` on the page.
- Switching modes then submitting: expect only the selected mode's fields and results, with no leftover results from the previous mode.
- RB/RE entered in Ω vs kΩ, or 0: expect correct scaling and a field error for zero.

---

### Task 1: Forward-active math for all three modes

**Files:**
- Modify: `bjt_ce_bias/bjt.py`
- Modify: `bjt_ce_bias/formatting.py:8`
- Modify: `bjt_ce_bias/tests/test_bjt.py:96-98`

**Interfaces:**
- Consumes: existing `BiasInputs`, `BiasResult`, `classify_vce`.
- Produces:
  - `VCE_SAT = 0.2`
  - `solve_bias_forward(inputs: BiasInputs) -> BiasResult`
  - `solve_bias(inputs: BiasInputs) -> BiasResult` (unchanged behaviour, now wraps forward)
  - `warning_for(ib: float, vce: float) -> str | None`
  - `FixedBiasInputs(vcc, rb, rc, beta, vbe)`
  - `EmitterBiasInputs(vcc, rb, rc, re, beta, vbe)`
  - `parse_fixed(raw) -> tuple[FixedBiasInputs | None, dict[str, str]]`
  - `parse_emitter(raw) -> tuple[EmitterBiasInputs | None, dict[str, str]]`
  - `solve_fixed_bias(inputs: FixedBiasInputs) -> dict`
  - `solve_emitter_bias(inputs: EmitterBiasInputs) -> dict`
  - `solve_operating_point(mode: str, inputs) -> dict`, raises `ValueError` on unknown mode
  - result dict keys: `mode, vb_v, ve_v, vc_v, vce_v, ib_a, ic_ma, ie_ma, warning, region, message`

- [ ] **Step 1: Update the threshold and its existing boundary test**

In `bjt_ce_bias/bjt.py` set `VCE_SAT = 0.2` and change both `0.3 V` strings in
`region_message` to `0.2 V`. In `test_bjt.py` change
`classify_vce(0.3)` to `classify_vce(0.2)` and `classify_vce(0.2999999)` to
`classify_vce(0.1999999)`.

- [ ] **Step 2: Run the suite**

Run: `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`
Expected: 37 tests OK.

- [ ] **Step 3: Split the divider solver into forward and Lab 02 wrappers**

`solve_bias_forward(inputs: BiasInputs) -> BiasResult` keeps the current body
of `solve_bias` but never zeroes the cutoff case: it computes `ic` from the
Thevenin form, raises `ValueError` on non-finite values, derives `ib, ie, ve,
vb, vc, vce`, then sets `region = REGION_CUTOFF if ic <= 0 else classify_vce(vce)`
and `message = region_message(region, vce)`.

`solve_bias(inputs)` calls `solve_bias_forward(inputs)`; if the forward region is
cutoff it returns the existing zeroed `BiasResult` (`vb=ve=vc=vce=vcc`,
`ib=ic=ie=0`, cutoff message); otherwise it returns the forward result unchanged.

- [ ] **Step 4: Verify A1 and cutoff behaviour**

Run:

```powershell
@'
from bjt_ce_bias.bjt import BiasInputs, solve_bias, solve_bias_forward
I = BiasInputs(12.0, 100e3, 22e3, 2.2e3, 1e3, 100.0, 0.7)
f = solve_bias_forward(I)
assert abs(f.ic - 1.2298581462608458e-3) < 1e-12, f.ic
assert abs(f.vce - 8.052155350502685) < 1e-9, f.vce
c = solve_bias(BiasInputs(12.0, 100e3, 1e3, 4.7e3, 1e3, 100.0, 0.7))
assert (c.ib, c.ic, c.ie, c.vce) == (0.0, 0.0, 0.0, 12.0)
print("A1 and cutoff OK")
'@ | .venv\Scripts\python -
```

Expected: `A1 and cutoff OK`.

- [ ] **Step 5: Add the new input types and parsers**

In `bjt.py` add the two frozen dataclasses from the Interfaces block. Refactor
parsing into `_parse_common(raw: Mapping[str, str], errors: dict[str, str]) ->
tuple[float | None, float | None, float | None]` returning `(vcc, beta, vbe)`
with VCC > 0, `beta > 1`, `0 <= VBE <= 1`, and
`_parse_resistors(raw, errors, fields) -> dict[str, float]` (number, known unit,
finite after scaling, `> 0`; error text
`f"{field.upper()} must be greater than 0 Ω"`). `parse_fixed` uses
`("rb", "rc")`; `parse_emitter` uses `("rb", "re", "rc")`; both return
`(None, errors)` when `errors` is non-empty. Keep `parse_inputs` behaviour
exactly as today for divider.

Add `formatting.RESISTOR_FIELDS` member `"rb"`.

- [ ] **Step 6: Add the warning, shared result builder, and mode solvers**

Add `_operating_point(mode, *, vcc, rc, beta, vbe, ib, re) -> dict` that computes
`ic = beta * ib`, `ie = (beta + 1) * ib`, `ve = ie * re`, `vb = ve + vbe`,
`vc = vcc - ic * rc`, `vce = vc - ve`; raises `ValueError` if any is non-finite;
sets `region` and `message` like `solve_bias_forward`; sets `warning =
warning_for(ib, vce)`; returns the dict in the contract (SI volts/amps, currents
in mA for `ic_ma`/`ie_ma`).

Add `warning_for`:

```python
def warning_for(ib: float, vce: float) -> str | None:
    reasons = []
    if ib <= 0:
        reasons.append("IB ≤ 0")
    if vce <= VCE_SAT:
        reasons.append(f"VCE ≤ {VCE_SAT:.1f} V")
    if not reasons:
        return None
    return ("The forward-active model may not apply: " + ", ".join(reasons)
            + ". Cutoff/saturation are not calculated.")
```

`solve_fixed_bias` uses `ib = (vcc - vbe) / rb`, `re = 0.0`.
`solve_emitter_bias` uses the overflow-safe form
`ib = ((vcc - vbe) / beta) / (rb / beta + re * (1.0 + 1.0 / beta))`.
`solve_operating_point` dispatches with if/elif on `"divider"`, `"fixed"`,
`"emitter"`; divider calls `solve_bias_forward(inputs)` and passes
`ib=f.ib, re=inputs.re` plus the input's `vcc/rc/beta/vbe` to
`_operating_point("divider", ...)`; any other value raises
`ValueError(f"unknown bias mode: {mode}")`.

- [ ] **Step 7: Verify A2–A4 and parser errors**

Run:

```powershell
@'
from bjt_ce_bias.bjt import (FixedBiasInputs, EmitterBiasInputs,
    parse_fixed, parse_emitter, solve_operating_point)
def show(r): print(r["mode"], round(r["ic_ma"], 4), round(r["vce_v"], 4), r["warning"])
show(solve_operating_point("fixed", FixedBiasInputs(12.0, 1e6, 2.2e3, 100.0, 0.7)))
show(solve_operating_point("emitter", EmitterBiasInputs(12.0, 1e6, 2.2e3, 1e3, 100.0, 0.7)))
show(solve_operating_point("emitter", EmitterBiasInputs(12.0, 1e6, 2.2e3, 2e3, 100.0, 0.7)))
base = {"vcc":"12","rc":"2.2","beta":"100","vbe":"0.7","rc_unit":"kohm",
        "rb_unit":"kohm","re_unit":"kohm","rb":"1000","re":"1"}
assert parse_fixed({**base, "rb":"0"})[0] is None
assert "rb" in parse_fixed({**base, "rb":"0"})[1]
assert parse_emitter({**base, "re":""})[0] is None
assert "re" in parse_emitter({**base, "re":""})[1]
assert parse_fixed({**base, "rb":"1000", "rb_unit":"ohm"})[0].rb == 1000.0
try:
    solve_operating_point("fixed", FixedBiasInputs(12.0, 1e-320, 2.2e3, 100.0, 0.7))
    raise AssertionError("overflow should fail")
except ValueError:
    pass
try:
    solve_operating_point("bogus", FixedBiasInputs(12.0, 1e6, 2.2e3, 100.0, 0.7))
    raise AssertionError("unknown mode should fail")
except ValueError:
    pass
print("parsers OK")
'@ | .venv\Scripts\python -
```

Expected: fixed `1.13 9.514`, emitter `1.0263 8.7054` then `0.9401 8.0328`,
then `parsers OK`. Warnings are `None` for all three.

- [ ] **Step 8: Run the full suite and commit**

Run: `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`
Expected: 37 tests OK.

```bash
git add bjt_ce_bias/bjt.py bjt_ce_bias/formatting.py bjt_ce_bias/tests/test_bjt.py
git commit -m "feat: add fixed and emitter bias math"
```

---

### Task 2: Mode selector, per-mode forms, and results rendering

**Files:**
- Modify: `bjt_ce_bias/app.py`
- Modify: `bjt_ce_bias/templates/index.html`
- Modify: `bjt_ce_bias/static/style.css`
- Modify: `bjt_ce_bias/tests/test_app.py:13`

**Interfaces:**
- Consumes: everything produced by Task 1.
- Produces:
  - `MODES = ("divider", "fixed", "emitter")`
  - `MODE_NAMES = {"divider": "Voltage Divider Bias", "fixed": "Fixed Bias", "emitter": "Emitter Bias"}`
  - `DEFAULT_FORM` gains `"rb": "1000"` and `"rb_unit": "kohm"`
  - template variables: `mode` (str or `None`), `mode_name`, `mode_options`, `form`, `errors`, `result`, `rows`, `schematic`, `nodal_view`, `nodal_agrees`, `spice_view`, `spice_agrees`, `spice_available`, `spice_error`
  - routes: `GET /?mode=...` (invalid → 400), `POST /` (missing `mode` → divider, invalid → 400)

- [ ] **Step 1: Update the page-title assertion first**

In `test_app.py` change `"Lab 02: BJT DC Bias Web App"` to
`"Lab 03: BJT DC Bias Web App"`. Run the suite and confirm that test fails
before the template change.

- [ ] **Step 2: Add app constants and the dict-based result helper**

Add `MODES`, `MODE_NAMES`, and the `rb` defaults. Replace `_result_rows` so it
reads the dict keys:

```python
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
```

Change `_render` to `_render(mode, form, errors, result=None, inputs=None,
forward=None)`. It always passes `mode`, `mode_name`,
`mode_options=tuple(MODE_NAMES.items())`, `form`, `errors`, `result`, `rows`.
For `mode == "divider"` it parses defaults when `inputs is None`, sets
`schematic`, and when `forward is not None` merges `_verdict_context(forward,
inputs)`. Other modes get no schematic and no checks.

- [ ] **Step 3: Rewrite `index` around the mode**

Replace the route body with:

```python
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        mode = request.args.get("mode", "divider")
        if mode not in MODES:
            return _render(None, {}, {"form": f"Unknown bias mode: {mode}."}), 400
        return _render(mode, DEFAULT_FORM, {})

    mode = request.form.get("mode") or "divider"
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

    return _render(mode, form, {}, result, inputs=inputs if mode == "divider" else None,
                   forward=forward)
```

Keep `_verdict_context`, `_schematic`, and `_schematic_inputs` working as they
do today.

- [ ] **Step 4: Rebuild `index.html` around the mode**

Change `<title>` and `<h1>` to `Lab 03: BJT DC Bias Web App`; subtitle to
`ENG29 2121 – Common Emitter (Fixed, Emitter, Voltage Divider Bias)`.

In the Input Parameters card, above the errors, add:

```html
<form method="get" action="/" class="mode-switch">
  <label for="mode">Bias mode</label>
  <select id="mode" name="mode">
    {% for value, label in mode_options %}
    <option value="{{ value }}" {% if mode == value %}selected{% endif %}>{{ label }}</option>
    {% endfor %}
  </select>
  <button type="submit" class="load-mode">Load mode</button>
</form>
```

Wrap the POST form in `{% if mode %}` and start it with
`<input type="hidden" name="mode" value="{{ mode }}">`. Render fields by mode:
divider `vcc, r1, r2, rc, re`; fixed `vcc, rb, rc`; emitter `vcc, rb, re, rc`.
Always render `beta` and `vbe`. RB labels/units mirror the resistor rows
(`rb`/`rb_unit`, options kΩ/Ω). Keep existing divider input rows unchanged.

Wrap the Circuit card in `{% if mode == 'divider' %}`. In the results heading,
append `— {{ mode_name }}`. Keep the table and divider region badge (wrap the
badge in `{% if mode == 'divider' %}`). Add above the cross-check:

```html
{% if result.warning %}
<div class="status status-warning">
  <strong>⚠️ Model limit</strong>
  <span>{{ result.warning }}</span>
</div>
{% endif %}
```

Wrap the cross-check block in `{% if mode == 'divider' %}`. Keep the existing
cutoff text and SPICE rows untouched inside it.

- [ ] **Step 5: Add the new styles**

In `style.css` add `.mode-switch` as a flex row with label, growing select, and
an outline button `.load-mode` using `--teal`; add `.status-warning` with
`--warn-bg`/`--warn-ink` and border `#f0d3a8`.

- [ ] **Step 6: Verify the app with the Flask test client**

Run:

```powershell
$env:PYTHONIOENCODING="utf-8"
@'
from bjt_ce_bias.app import app
c = app.test_client()
def html(r): return r.get_data(as_text=True)
d = html(c.get("/"))
assert "Lab 03: BJT DC Bias Web App" in d and 'name="r1"' in d and 'name="mode"' in d
f = html(c.get("/?mode=fixed"))
assert 'name="rb"' in f and 'name="r1"' not in f and 'id="schematic"' not in f
e = html(c.get("/?mode=emitter"))
assert 'name="rb"' in e and 'name="re"' in e and 'name="r1"' not in e
a1 = html(c.post("/", data={"vcc":"12","r1":"100","r2":"22","rc":"2.2","re":"1",
    "beta":"100","vbe":"0.7","r1_unit":"kohm","r2_unit":"kohm","rc_unit":"kohm","re_unit":"kohm"}))
assert "1.230" in a1 and "8.052" in a1 and 'id="schematic"' in a1
assert "Voltage Divider Bias" in a1
cut = html(c.post("/", data={"vcc":"12","r1":"100","r2":"1","rc":"4.7","re":"1",
    "beta":"100","vbe":"0.7","r1_unit":"kohm","r2_unit":"kohm","rc_unit":"kohm","re_unit":"kohm"}))
assert "forward-active model may not apply" in cut
assert "the transistor is off" in cut and "Nodal KCL solve" not in cut
sat = html(c.post("/", data={"vcc":"12","r1":"100","r2":"22","rc":"10","re":"1",
    "beta":"100","vbe":"0.7","r1_unit":"kohm","r2_unit":"kohm","rc_unit":"kohm","re_unit":"kohm"}))
assert "region-saturation" in sat and "forward-active model may not apply" in sat
a2 = html(c.post("/", data={"mode":"fixed","vcc":"12","rb":"1000","rc":"2.2",
    "beta":"100","vbe":"0.7","rb_unit":"kohm","rc_unit":"kohm"}))
assert "1.130" in a2 and "9.514" in a2 and "Fixed Bias" in a2
assert 'name="r1"' not in a2 and 'id="schematic"' not in a2
a3 = html(c.post("/", data={"mode":"emitter","vcc":"12","rb":"1000","re":"1",
    "rc":"2.2","beta":"100","vbe":"0.7","rb_unit":"kohm","re_unit":"kohm","rc_unit":"kohm"}))
assert "1.026" in a3 and "8.705" in a3 and 'name="r1"' not in a3
a4 = html(c.post("/", data={"mode":"emitter","vcc":"12","rb":"1000","re":"2",
    "rc":"2.2","beta":"100","vbe":"0.7","rb_unit":"kohm","re_unit":"kohm","rc_unit":"kohm"}))
assert "0.940" in a4 and "8.033" in a4
a5 = html(c.post("/", data={"mode":"fixed","vcc":"12","rb":"0","rc":"2.2",
    "beta":"100","vbe":"0.7","rb_unit":"kohm","rc_unit":"kohm"}))
assert "must be greater than 0" in a5 and "DC Bias Results" in a5
assert "results-table" not in a5 and 'value="0"' in a5
assert c.get("/?mode=bogus").status_code == 400
assert c.post("/", data={"mode":"bogus"}).status_code == 400
print("app OK")
'@ | .venv\Scripts\python -
```

Expected: `app OK`.

- [ ] **Step 7: Run the full suite and commit**

Run: `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`
Expected: 37 tests OK.

```bash
git add bjt_ce_bias/app.py bjt_ce_bias/templates/index.html bjt_ce_bias/static/style.css bjt_ce_bias/tests/test_app.py
git commit -m "feat: add bias mode selector and per-mode forms"
```

---

### Task 3: Browser validation A1–A5 and evidence document

**Files:**
- Create: `docs/validation.md`
- Create: `docs/evidence/lab03-emitter.png` (screenshot)

**Interfaces:**
- Consumes: running app from Task 2 at `http://127.0.0.1:5000`.
- Produces: documented A1–A5 table, screenshot path, method line.

- [ ] **Step 1: Start the app**

Run in the background:
`$env:PYTHONIOENCODING="utf-8"; .venv\Scripts\python -m bjt_ce_bias.app`
Expected: server listening on `http://127.0.0.1:5000`.

- [ ] **Step 2: Validate A1–A5 in OpenCode Browser**

Load the `browser` skill first. Open `http://127.0.0.1:5000` and run:

- A1 Divider: R1=100, R2=22, RC=2.2, RE=1, β=100, VBE=0.70, all kΩ.
  Expect IC 1.230 mA, VCE 8.052 V, Active badge, cross-check rows present.
- A2 Fixed: RB=1000 kΩ, RC=2.2 kΩ, β=100, VBE=0.70.
  Expect IC 1.130 mA, VCE 9.514 V, no RE field, no circuit card.
- A3 Emitter: RB=1000 kΩ, RE=1 kΩ, RC=2.2 kΩ.
  Expect IC 1.026 mA, VCE 8.705 V, no R1/R2 fields.
- A4 Emitter: same as A3 with RE=2 kΩ.
  Expect IC 0.940 mA, VCE 8.033 V; IC lower than A3.
- A5 Fixed: RB=0. Expect field error for RB, no results table, page still
  rendered.

Capture a screenshot of the A3 results with the browser screenshot tool and
save it as `docs/evidence/lab03-emitter.png`. Record every observed value.

- [ ] **Step 3: Write `docs/validation.md`**

Include: method (`OpenCode Browser`), app URL, code commit under test
(`git rev-parse --short HEAD`), the shared inputs, and a table with columns
ID / Mode / Inputs / Expected IC / Expected VCE / Observed IC / Observed VCE /
Units / Status. Add the A5 row as "field error, no results" and note the A3→A4
direction. Add a short "Independent expected values" derivation for each row
(show `IB`, then `IC`, `VE`, `VC`, `VCE`) and the screenshot link. Add an
"AI assistance and student checks" section naming which parts were generated
with the agent (code, tests, docs) and which the student personally verified
(reading the equations against the lab sheet, running the tests, and repeating
the A1–A5 checks in the browser).

- [ ] **Step 4: Stop the server and commit**

```bash
git add docs/validation.md docs/evidence/lab03-emitter.png
git commit -m "docs: add Lab 03 A1-A5 browser validation"
```

---

### Task 4: README updates, final verification, push

**Files:**
- Modify: `README.md`
- Modify: `bjt_ce_bias/README.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: run instructions for the three modes and the validation pointer.

- [ ] **Step 1: Update the READMEs**

In both READMEs document: three modes, per-mode fields, `VCE_SAT = 0.2` warning
rule, run command `.venv\Scripts\python -m bjt_ce_bias.app`, test command, and a
link to `docs/validation.md` plus the design/plan paths. Keep existing Lab 02
run instructions valid.

- [ ] **Step 2: Run the full suite one last time**

Run: `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`
Expected: 37 tests OK.

- [ ] **Step 3: Review the complete diff**

Run: `git status --short`, `git diff`, `git diff --staged`.
Expected: only the Lab 03 files changed; no `.venv`, screenshots unrelated,
or temp files staged.

- [ ] **Step 4: Commit and push**

```bash
git add README.md bjt_ce_bias/README.md
git commit -m "docs: document Lab 03 bias modes"
git push origin main
git rev-parse HEAD
git status -sb
```

Expected: push succeeds, status shows `## main...origin/main` with no ahead/behind.

- [ ] **Step 5: Report**

Report in Thai: GitHub URL
`https://github.com/Tarkab67/Gitlab-for-class`, the final commit SHA, the A1–A5
pass summary, the validation document path, and which parts were AI-generated
versus checked by the student.
