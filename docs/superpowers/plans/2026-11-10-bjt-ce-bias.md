# BJT Common-Emitter DC Bias Web App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Flask app that computes and cross-checks the DC operating point of a BJT common-emitter (voltage-divider) bias circuit, matching the approved mockup.

**Architecture:** One pure-Python engineering module (`bjt.py`) owns parsing, validation, the Thevenin closed form, and a nodal cross-check. `spice.py` builds an ngspice netlist and parses the `.op` result. A thin Flask layer (`app.py`) validates, calls the pure modules, and renders one Jinja page. Tests are `unittest`, split by module.

**Tech Stack:** Python 3.12, Flask, stdlib only otherwise; `unittest`; portable ngspice (optional at runtime).

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-design.md`

## Global Constraints

- Python 3.12; Flask only; everything else stdlib. Venv at `.venv/` in the repo root (gitignored).
- Tests: `unittest`. Run from repo root: `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`.
- Run from repo root: `.venv\Scripts\python -m bjt_ce_bias.app` → `http://127.0.0.1:5000`.
- All math in SI (V, Ω, A). Formatting happens outside the math module.
- `VCE_SAT = 0.3`. Saturation when `VCE < 0.3` (strict). Cutoff when `IB <= 0`. Active otherwise.
- Defaults: `VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, beta=100, VBE=0.7`.
- Closed form: `VBB=VCC*R2/(R1+R2)`, `RB=R1*R2/(R1+R2)`, `IB=(VBB-VBE)/(RB+(beta+1)*RE)`, `IC=beta*IB`, `IE=(beta+1)*IB`, `VE=IE*RE`, `VB=VE+VBE`, `VC=VCC-IC*RC`, `VCE=VC-VE`.
- Nodal cross-check tolerance: `1e-9` relative. SPICE tolerance: `15 %` relative on `IC` and `VCE`, region must match.
- No JS, no CSS framework. Page background `#f1f3f5`, cards white with `#d7dde3` border, primary teal `#00796b`.
- Do not modify `electrical.py`, `test_electrical.py`, or the root README body (append one pointer section only).
- Never pass user input to a shell. SPICE runs with `subprocess.run([...], timeout=10)`.

## Review Focus

Failure modes the spec implies but the happy-path tests do not cover. Each gets a test in the owning task:

1. **Non-finite numeric input** (`nan`, `inf`, `1e400`) — must be rejected with a field error, never produce `inf`/`nan` results. (Task 1)
2. **Extreme but legal magnitudes** (`1 mΩ`, `1 GΩ`) — must return finite values and a region, never crash or divide by zero. (Task 2)
3. **Unit-select scaling** (`100` with `kΩ` vs `Ω`) — `kΩ` multiplies by 1000 exactly once; re-rendering after an error must keep the chosen unit. (Tasks 1, 5)
4. **SPICE absent, slow, or unparsable** — page must still render, show "SPICE not available", and never 500 or hang past the timeout. (Tasks 7, 8)
5. **`VCE` exactly at the saturation boundary** — `0.3` is active, `0.299999` is saturation. (Task 2)

---

### Task 1: Project scaffold and input parsing

**Files:**
- Create: `bjt_ce_bias/__init__.py`, `bjt_ce_bias/bjt.py`, `bjt_ce_bias/tests/__init__.py`, `bjt_ce_bias/tests/test_bjt.py`, `bjt_ce_bias/requirements.txt`
- Modify: `.gitignore` (add `.tools/`)

**Interfaces:**
- Consumes: nothing.
- Produces: `BiasInputs(vcc, r1, r2, rc, re, beta, vbe)` frozen dataclass; `parse_inputs(raw: Mapping[str, str]) -> tuple[BiasInputs | None, dict[str, str]]`. `raw` keys: `vcc, r1, r2, rc, re, beta, vbe` and unit keys `r1_unit, r2_unit, rc_unit, re_unit` with values `"ohm"` or `"kohm"` (missing → `"kohm"`). Error dict is keyed by the same field names.

- [ ] **Step 1: Create the venv and install Flask**

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --quiet "flask" 
.venv\Scripts\python -c "import flask; print(flask.__version__)"
```

Record the printed version in `bjt_ce_bias/requirements.txt` as `flask==<version>`.

- [ ] **Step 2: Write the failing test**

```python
# bjt_ce_bias/tests/test_bjt.py
import math
import unittest

from bjt_ce_bias.bjt import BiasInputs, parse_inputs

GOOD = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "beta": "100", "vbe": "0.70",
    "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm", "re_unit": "kohm",
}


class TestParseInputs(unittest.TestCase):
    def test_parses_scaled_si_values(self):
        inputs, errors = parse_inputs(GOOD)
        self.assertEqual(errors, {})
        self.assertAlmostEqual(inputs.r1, 100_000.0)
        self.assertAlmostEqual(inputs.rc, 2_200.0)
        self.assertAlmostEqual(inputs.vbe, 0.70)

    def test_ohm_unit_is_not_scaled(self):
        inputs, errors = parse_inputs({**GOOD, "r1": "100", "r1_unit": "ohm"})
        self.assertEqual(errors, {})
        self.assertAlmostEqual(inputs.r1, 100.0)

    def test_rejects_non_finite(self):
        for bad in ("nan", "inf", "-inf", "1e400", ""):
            with self.subTest(bad=bad):
                inputs, errors = parse_inputs({**GOOD, "vcc": bad})
                self.assertIsNone(inputs)
                self.assertIn("vcc", errors)

    def test_rejects_out_of_range_values(self):
        cases = {"vcc": "0", "r1": "-5", "beta": "1", "vbe": "1.5"}
        for field, bad in cases.items():
            with self.subTest(field=field):
                inputs, errors = parse_inputs({**GOOD, field: bad})
                self.assertIsNone(inputs)
                self.assertIn(field, errors)

    def test_reports_every_bad_field_at_once(self):
        inputs, errors = parse_inputs({**GOOD, "vcc": "abc", "re": "0"})
        self.assertIsNone(inputs)
        self.assertEqual(set(errors), {"vcc", "re"})
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_bjt -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bjt_ce_bias'` / `parse_inputs`.

- [ ] **Step 4: Implement `parse_inputs` in `bjt_ce_bias/bjt.py`**

Use `float()`, then `math.isfinite`. Resistor unit map: `{"ohm": 1.0, "kohm": 1e3}`, default `kohm`. Collect errors per field; return `(None, errors)` if any. Messages:
`"must be a number"`, `"VCC must be greater than 0 V"`, `"<field> must be greater than 0 Ω"`, `"beta must be greater than 1"`, `"VBE must be between 0 and 1 V"`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_bjt -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```powershell
git add .gitignore bjt_ce_bias/__init__.py bjt_ce_bias/bjt.py bjt_ce_bias/tests bjt_ce_bias/requirements.txt
git commit -m "feat(bjt): scaffold package and input parsing with validation"
```

---

### Task 2: Closed-form operating point and region rules

**Files:**
- Modify: `bjt_ce_bias/bjt.py`
- Test: `bjt_ce_bias/tests/test_bjt.py`

**Interfaces:**
- Consumes: `BiasInputs` from Task 1.
- Produces: `BiasResult(vb, ve, vc, vce, ib, ic, ie, region, message)` frozen dataclass; `solve_bias(inputs: BiasInputs) -> BiasResult`; `classify_vce(vce: float) -> str` returning `"active" | "saturation"`; `region_message(region: str, vce: float) -> str`. `VCE_SAT = 0.3`.

- [ ] **Step 1: Write the failing tests**

```python
from bjt_ce_bias.bjt import VCE_SAT, BiasInputs, classify_vce, solve_bias

DEFAULTS = BiasInputs(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3, re=1e3, beta=100.0, vbe=0.7)


class TestSolveBias(unittest.TestCase):
    def test_known_active_point(self):
        r = solve_bias(DEFAULTS)
        self.assertAlmostEqual(r.ib, 12.2985e-6, delta=1e-12)
        self.assertAlmostEqual(r.ic, 1.22985e-3, delta=1e-10)
        self.assertAlmostEqual(r.ie, 1.24215e-3, delta=1e-10)
        self.assertAlmostEqual(r.ve, 1.24215, delta=1e-6)
        self.assertAlmostEqual(r.vb, 1.94215, delta=1e-6)
        self.assertAlmostEqual(r.vc, 9.29433, delta=1e-5)
        self.assertAlmostEqual(r.vce, 8.05218, delta=1e-5)
        self.assertEqual(r.region, "active")

    def test_cutoff_when_divider_cannot_bias(self):
        r = solve_bias(BiasInputs(vcc=12.0, r1=100e3, r2=1e3, rc=4.7e3, re=1e3, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "cutoff")
        self.assertEqual((r.ib, r.ic, r.ie), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(r.vce, 12.0)

    def test_saturation_when_vce_below_threshold(self):
        r = solve_bias(BiasInputs(vcc=12.0, r1=100e3, r2=22e3, rc=10e3, re=1e3, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "saturation")
        self.assertLess(r.vce, VCE_SAT)

    def test_extreme_magnitudes_stay_finite(self):
        for r1, re_ in ((1e-3, 1e-3), (1e9, 1e9), (1e9, 1.0)):
            with self.subTest(r1=r1, re=re_):
                r = solve_bias(BiasInputs(12.0, r1, 22e3, 2.2e3, re_, 100.0, 0.7))
                for value in (r.vb, r.ve, r.vc, r.vce, r.ib, r.ic, r.ie):
                    self.assertTrue(math.isfinite(value))

    def test_huge_beta_is_handled(self):
        r = solve_bias(BiasInputs(12.0, 100e3, 22e3, 2.2e3, 1e3, 1e6, 0.7))
        self.assertIn(r.region, {"active", "saturation", "cutoff"})
        self.assertTrue(math.isfinite(r.ic))

    def test_saturation_boundary_is_strict(self):
        self.assertEqual(classify_vce(0.3), "active")
        self.assertEqual(classify_vce(0.2999999), "saturation")
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_bjt -v`
Expected: FAIL — `ImportError: cannot import name 'solve_bias'`.

- [ ] **Step 3: Implement `solve_bias`, `classify_vce`, `region_message`**

Cutoff branch: when `IB <= 0`, return zeros with `ve=vb=vc=vce=vcc` and message `"Cutoff: the divider cannot forward-bias the base (transistor off)."`. Otherwise compute the closed form; saturation when `classify_vce(vce) == "saturation"` with message `"Saturation: VCE is below 0.3 V; the linear model overstates IC."`. Active message: `"Active region approximation OK: VCE = {vce:.2f} V > 0.3 V."`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_bjt -v`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```powershell
git add bjt_ce_bias/bjt.py bjt_ce_bias/tests/test_bjt.py
git commit -m "feat(bjt): closed-form operating point and region classification"
```

---

### Task 3: Independent nodal cross-check

**Files:**
- Modify: `bjt_ce_bias/bjt.py`
- Test: `bjt_ce_bias/tests/test_bjt.py`

**Interfaces:**
- Consumes: `BiasInputs`, `BiasResult`, `solve_bias`.
- Produces: `nodal_solve(inputs: BiasInputs) -> BiasResult`; `cross_check(closed: BiasResult, nodal: BiasResult, rel_tol: float = 1e-9) -> tuple[bool, float]` returning `(agree, max_relative_difference)` over `ib, ic, ie, vce`.

- [ ] **Step 1: Write the failing tests**

```python
from bjt_ce_bias.bjt import cross_check, nodal_solve, solve_bias


class TestNodalSolve(unittest.TestCase):
    def test_matches_closed_form_on_active_case(self):
        closed = solve_bias(DEFAULTS)
        nodal = nodal_solve(DEFAULTS)
        agree, diff = cross_check(closed, nodal)
        self.assertTrue(agree)
        self.assertLess(diff, 1e-9)

    def test_nodal_solution_satisfies_kcl(self):
        nodal = nodal_solve(DEFAULTS)
        i_r1 = (12.0 - nodal.vb) / 100e3
        i_r2 = nodal.vb / 22e3
        self.assertAlmostEqual(i_r1 - i_r2, nodal.ib, delta=1e-12)
        self.assertAlmostEqual((12.0 - nodal.vc) / 2.2e3, nodal.ic, delta=1e-12)
        self.assertAlmostEqual(nodal.ve / 1e3, nodal.ie, delta=1e-12)

    def test_detects_a_wrong_solution(self):
        closed = solve_bias(DEFAULTS)
        nodal = nodal_solve(DEFAULTS)
        broken = BiasResult(**{**nodal.__dict__, "ic": nodal.ic * 1.01})
        agree, diff = cross_check(closed, broken)
        self.assertFalse(agree)
        self.assertGreater(diff, 1e-4)
```

Add `from bjt_ce_bias.bjt import BiasResult` to the imports.

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_bjt -v`
Expected: FAIL — `cannot import name 'nodal_solve'`.

- [ ] **Step 3: Implement the 6×6 solve**

Build the matrix from the spec's equations (1)–(6) with unknowns `[IB, IC, IE, VB, VC, VE]`, solve with Gaussian elimination and partial pivoting (stdlib `list[list[float]]`, no numpy). Return a `BiasResult` with `region=""` and `message="nodal"`. `cross_check` compares `ib, ic, ie, vce` using `abs(a-b)/max(abs(a), abs(b), 1e-30)` and returns the maximum.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_bjt -v`
Expected: PASS (14 tests).

- [ ] **Step 5: Commit**

```powershell
git add bjt_ce_bias/bjt.py bjt_ce_bias/tests/test_bjt.py
git commit -m "feat(bjt): independent nodal solver and cross-check"
```

---

### Task 4: Flask shell, layout and CSS

**Files:**
- Create: `bjt_ce_bias/app.py`, `bjt_ce_bias/templates/index.html`, `bjt_ce_bias/static/style.css`, `bjt_ce_bias/formatting.py`
- Test: `bjt_ce_bias/tests/test_app.py`

**Interfaces:**
- Consumes: `parse_inputs`, `solve_bias`, `BiasInputs`.
- Produces: `app` (Flask instance) with route `GET /` and `POST /`; `format_quantity(quantity: str, value_si: float) -> tuple[str, str]` returning `(display, unit)` — `("1.230", "mA")`, `("12.30", "µA")`, `("8.052", "V")`, `("100.0", "kΩ")`.

- [ ] **Step 1: Write the failing test**

```python
# bjt_ce_bias/tests/test_app.py
import unittest

from bjt_ce_bias.app import app
from bjt_ce_bias.formatting import format_quantity


class TestPageShell(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_renders_three_cards_and_form(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("Lab 02: BJT DC Bias Web App", html)
        self.assertIn("Input Parameters", html)
        self.assertIn("Circuit", html)
        self.assertIn("DC Bias Results", html)
        for field in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{field}"', html)
        self.assertIn("style.css", html)

    def test_format_quantity_units(self):
        self.assertEqual(format_quantity("ic", 1.22985e-3), ("1.230", "mA"))
        self.assertEqual(format_quantity("ib", 12.2985e-6), ("12.30", "µA"))
        self.assertEqual(format_quantity("vce", 8.05218), ("8.052", "V"))
        self.assertEqual(format_quantity("rc", 2200.0), ("2.2", "kΩ"))
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_app -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bjt_ce_bias.app'`.

- [ ] **Step 3: Implement the shell**

`app.py`: `app = Flask(__name__)`; `GET /` renders `index.html` with default field values; `if __name__ == "__main__": app.run(debug=True)`. Template: header (chip glyph, title, subtitle, course badge) + three cards; the form has the seven fields with unit selects for the resistors; results card and cross-check blocks are empty placeholders with `id="results"`. CSS: the layout rules from the spec (3-column grid, `#f1f3f5` page, white cards, teal button, monospace values), one column under 960 px.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_app -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```powershell
git add bjt_ce_bias/app.py bjt_ce_bias/formatting.py bjt_ce_bias/templates bjt_ce_bias/static bjt_ce_bias/tests/test_app.py
git commit -m "feat(app): three-column Flask shell with matching CSS"
```

---

### Task 5: Results rendering, errors and region box

**Files:**
- Modify: `bjt_ce_bias/app.py`, `bjt_ce_bias/templates/index.html`
- Test: `bjt_ce_bias/tests/test_app.py`

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: `POST /` renders `results`, `region` (`active|saturation|cutoff`), `message`, `errors`, `form` (echoed raw values and units) into `index.html`.

- [ ] **Step 1: Write the failing tests**

```python
VALID_FORM = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "beta": "100", "vbe": "0.70",
    "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm", "re_unit": "kohm",
}


class TestResultsPage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_post_valid_renders_all_quantities(self):
        html = self.client.post("/", data=VALID_FORM).get_data(as_text=True)
        for label, value in (("VB", "1.942"), ("VE", "1.242"), ("VC", "9.294"),
                             ("VCE", "8.052"), ("IB", "12.30"), ("IC", "1.230"), ("IE", "1.242")):
            self.assertIn(label, html)
            self.assertIn(value, html)
        self.assertIn("Active region", html)
        self.assertIn("region-active", html)

    def test_post_invalid_shows_field_errors_and_keeps_input(self):
        bad = {**VALID_FORM, "vcc": "abc"}
        html = self.client.post("/", data=bad).get_data(as_text=True)
        self.assertIn("must be a number", html)
        self.assertIn('value="abc"', html)
        self.assertIn('value="kohm" selected', html)
        self.assertNotIn("region-active", html)

    def test_saturation_renders_warning_class(self):
        html = self.client.post("/", data={**VALID_FORM, "rc": "10"}).get_data(as_text=True)
        self.assertIn("region-saturation", html)
        self.assertIn("overstates IC", html)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_app -v`
Expected: FAIL — result labels missing from the response.

- [ ] **Step 3: Implement the POST path and template blocks**

`POST /`: `parse_inputs(request.form.to_dict())`; on errors re-render with `errors` and `form`; else `solve_bias` → pass `result` and per-row `(label, display, unit)` tuples to the template. Template: results table rows `VB, VE, VC, VCE, IB, IC, IE`; status box with class `region-{{ region }}`; warnings block. Escape all echoed values (Jinja autoescape).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_app -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```powershell
git add bjt_ce_bias/app.py bjt_ce_bias/templates/index.html bjt_ce_bias/tests/test_app.py
git commit -m "feat(app): render operating point, field errors and region box"
```

---

### Task 6: Live schematic SVG

**Files:**
- Modify: `bjt_ce_bias/templates/index.html`, `bjt_ce_bias/app.py`
- Test: `bjt_ce_bias/tests/test_app.py`

**Interfaces:**
- Consumes: `BiasInputs`, `BiasResult`.
- Produces: a `<svg id="schematic">` block whose text labels are `VCC`, `R1`, `R2`, `RC`, `RE`, `Q1`, `β` with the current values.

- [ ] **Step 1: Write the failing test**

```python
class TestSchematic(unittest.TestCase):
    def test_svg_shows_current_values(self):
        html = app.test_client().post("/", data=VALID_FORM).get_data(as_text=True)
        start = html.index('<svg id="schematic"')
        svg = html[start:html.index("</svg>", start)]
        for text in ("12 V", "100 kΩ", "22 kΩ", "2.2 kΩ", "1 kΩ", "β = 100", "Q1"):
            self.assertIn(text, svg)

    def test_svg_uses_typed_values(self):
        html = app.test_client().post("/", data={**VALID_FORM, "rc": "4.7"}).get_data(as_text=True)
        start = html.index('<svg id="schematic"')
        self.assertIn("4.7 kΩ", html[start:html.index("</svg>", start)])
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_app -v`
Expected: FAIL — no `<svg id="schematic">`.

- [ ] **Step 3: Add the inline SVG**

Draw rails, four resistors (zig-zag or IEC box), an NPN symbol with base arrow, `VCC` node, ground symbols; text labels fed by formatters. Keep it inline in `index.html`; no image files.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_app -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```powershell
git add bjt_ce_bias/templates/index.html bjt_ce_bias/tests/test_app.py
git commit -m "feat(app): inline schematic with live component values"
```

---

### Task 7: SPICE netlist and runner

**Files:**
- Create: `bjt_ce_bias/spice.py`, `bjt_ce_bias/tests/test_spice.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `BiasInputs`.
- Produces: `SpiceResult(vb, ve, vc, vce, ib, ic, ie, vbe)`; `find_ngspice() -> str | None`; `available() -> bool`; `build_netlist(inputs: BiasInputs) -> str`; `run_operating_point(inputs: BiasInputs, timeout_s: float = 10.0) -> SpiceResult | None`; `compare(closed: BiasResult, spice: SpiceResult, rel_tol: float = 0.15) -> tuple[bool, float]`.

- [ ] **Step 1: Write the failing test**

```python
# bjt_ce_bias/tests/test_spice.py
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
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_spice -v`
Expected: FAIL — `No module named 'bjt_ce_bias.spice'`.

- [ ] **Step 3: Install portable ngspice and implement `spice.py`**

Download the current ngspice Windows zip into `.tools/`, `Expand-Archive` it, and note the binary (`ngspice_con.exe`). Add `.tools/` to `.gitignore`. Implement netlist building (exact lines asserted above), discovery (`NGSPICE_BIN` → `shutil.which` → `.tools/**/ngspice_con.exe`), `subprocess.run([exe, "-b", netlist], timeout=timeout_s)` in a `tempfile.TemporaryDirectory`, and regex parsing of `v(b)`, `v(e)`, `v(c)`, `i(vcc)`; `ic = -i(vcc)`, `ie = ve/re`, `ib = ie - ic`, `vbe = vb - ve`. Return `None` on any failure.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_spice -v`
Expected: PASS, 4 tests (2 skipped only if ngspice could not be installed; record the skip reason if so).

- [ ] **Step 5: Commit**

```powershell
git add .gitignore bjt_ce_bias/spice.py bjt_ce_bias/tests/test_spice.py
git commit -m "feat(spice): ngspice netlist, runner and agreement check"
```

---

### Task 8: Cross-check block on the page

**Files:**
- Modify: `bjt_ce_bias/app.py`, `bjt_ce_bias/templates/index.html`
- Test: `bjt_ce_bias/tests/test_app.py`

**Interfaces:**
- Consumes: `nodal_solve`, `cross_check`, `spice.available`, `spice.run_operating_point`, `spice.compare`.
- Produces: template context keys `nodal`, `nodal_agrees`, `spice`, `spice_agrees`, `spice_available`.

- [ ] **Step 1: Write the failing test**

```python
class TestCrossCheckBlock(unittest.TestCase):
    def test_nodal_row_rendered(self):
        html = app.test_client().post("/", data=VALID_FORM).get_data(as_text=True)
        self.assertIn("Nodal", html)
        self.assertIn("1.230", html)

    def test_spice_unavailable_is_graceful(self):
        from unittest.mock import patch
        with patch("bjt_ce_bias.app.spice.available", return_value=False):
            response = app.test_client().post("/", data=VALID_FORM)
            html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("SPICE not available", html)

    def test_spice_error_never_breaks_the_page(self):
        from unittest.mock import patch
        with patch("bjt_ce_bias.app.spice.available", return_value=True), \
             patch("bjt_ce_bias.app.spice.run_operating_point", side_effect=RuntimeError("boom")):
            response = app.test_client().post("/", data=VALID_FORM)
        self.assertEqual(response.status_code, 200)
        self.assertIn("SPICE check failed", response.get_data(as_text=True))
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_app -v`
Expected: FAIL — "Nodal" not in the page.

- [ ] **Step 3: Wire the checks into `POST /`**

Always compute the nodal result and `cross_check`. Call SPICE inside `try/except Exception`, guarded by `spice.available()`. Render: pass/fail marker per row, SPICE `VBE` shown next to the assumed `VBE`, and the muted unavailable line.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest bjt_ce_bias.tests.test_app -v`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```powershell
git add bjt_ce_bias/app.py bjt_ce_bias/templates/index.html bjt_ce_bias/tests/test_app.py
git commit -m "feat(app): nodal and SPICE cross-check panel"
```

---

### Task 9: README, hand calculation, full-suite verification and demo

**Files:**
- Create: `bjt_ce_bias/README.md`
- Modify: `README.md` (append a pointer section only)
- Test: full suite

**Interfaces:**
- Consumes: everything.
- Produces: runnable demo and documented hand calculation.

- [ ] **Step 1: Write `bjt_ce_bias/README.md`**

Sections: what it is; setup (`python -m venv .venv`, `.venv\Scripts\python -m pip install -r bjt_ce_bias/requirements.txt`); run; test; optional ngspice note; and the worked hand calculation for the defaults:

```
VBB = 12 * 22k / (100k + 22k)   = 2.164 V
RB  = 100k || 22k               = 18.03 kΩ
IB  = (2.164 - 0.7) / (18.03k + 101 * 1k) = 12.30 µA
IC  = 100 * 12.30 µA            = 1.230 mA
IE  = 101 * 12.30 µA            = 1.242 mA
VE  = 1.242 mA * 1k             = 1.242 V
VB  = 1.242 + 0.7               = 1.942 V
VC  = 12 - 1.230 mA * 2.2k      = 9.294 V
VCE = 9.294 - 1.242             = 8.052 V   (active, > 0.3 V)
```

- [ ] **Step 2: Append the root README pointer**

Three lines at the end: lab name, `bjt_ce_bias/` location, run command. Do not touch the existing text.

- [ ] **Step 3: Run the full suite**

Run: `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`
Expected: PASS, 0 failures, 0 errors (SPICE tests skipped only if ngspice is absent).

- [ ] **Step 4: Run the demo and confirm it responds**

Run in the background: `.venv\Scripts\python -m bjt_ce_bias.app`, then `Invoke-WebRequest http://127.0.0.1:5000 -UseBasicParsing` → `StatusCode 200` and the page contains `Lab 02`. Leave it running for the demo, then stop it.

- [ ] **Step 5: Commit**

```powershell
git add bjt_ce_bias/README.md README.md
git commit -m "docs: lab README with worked hand calculation"
```

---

## Plan self-review

- **Spec coverage:** UI/mockup (Tasks 4–6), seven inputs + units (1, 4), VB/VE/VC/VCE/IB/IC/IE (2, 5), validation (1, 5), region rules incl. cutoff/saturation/boundary (2), independent nodal (3), SPICE (7, 8), graceful SPICE absence (7, 8), tests (all), README + hand calculation (9), demo (9). No spec requirement is unassigned.
- **Review Focus:** non-finite (Task 1), extreme magnitudes (2), unit scaling + echo (1, 5), SPICE absent/error/timeout (7, 8), boundary (2). All pinned to tests.
- **Type consistency:** `BiasInputs`, `BiasResult`, `SpiceResult` fields and the `parse_inputs/cross_check/compare` signatures are used identically across tasks.
