# BJT Common-Emitter DC Bias — Design

- Course: ENG29 2121 (short lab)
- Date: 2026-11-10
- Revision: 2 (adds the mockup-matched UI and a SPICE cross-check)
- Status: proposed (awaiting approval)

## Intent and why

Deliver a real, runnable Flask web application that computes the DC operating
point of a BJT common-emitter bias network. The lab is graded on correct
engineering math, a working web app with clean separation of concerns, and
evidence that the result was independently checked.

The page must look and read like the reference mockup (`Lab 02: BJT DC Bias Web
App`), so the demo is presentable in class. Scope stays small enough to ship and
commit today.

## Goals

1. Accept seven inputs: `VCC`, `R1`, `R2`, `RC`, `RE`, `beta`, `VBE`, each with
   a unit selector where a unit applies (`V`, `kΩ`/`Ω`).
2. Report `VB`, `VE`, `VC`, `VCE`, `IB`, `IC`, `IE` with units, matching the
   mockup's result table.
3. Reject invalid input with field-level messages (no traceback, no 500).
4. Classify the operating region (active / saturation / cutoff) in a coloured
   status box like the mockup's "Active region approximation OK".
5. Cross-check the operating point two ways: an independent nodal solve and a
   real SPICE simulation (ngspice), shown side by side with the closed form.
6. Run at `http://127.0.0.1:5000` with one command.
7. Be testable without a browser; readable at projector distance.

## Non-goals

- No AC analysis, gain, small-signal model, or frequency response.
- No transient, noise, or temperature sweep.
- No load-line plot, no waveform chart.
- No circuit editor, netlist import, or other topologies (fixed bias, feedback).
- No FET, op-amps, or multi-stage circuits.
- No database, auth, sessions, deployment, Docker, or CI.
- No JS framework, no build step.

## Anti-goals

- Engineering math inside Flask routes (untestable).
- A "cross-check" that is the same algebra rewritten (proves nothing).
- Silent wrong answers: bad input accepted, or a valid-looking operating point
  reported in a region where the model does not hold, without a warning.
- A page that only works when SPICE happens to be installed.
- Calibrating the physics to the mockup's sample numbers (see "Note on the
  mockup numbers").

## Constraints

- Python 3.12 (`python`), Flask; stdlib for math and tests; `unittest`
  (matches the repo's existing `test_electrical.py` convention).
- Project venv at the repo root: `.venv/` (already gitignored). Flask goes
  there only; system Python is untouched.
- SPICE: portable ngspice (no admin install), unpacked under `.tools/`
  (gitignored). `NGSPICE_BIN` overrides the lookup. Missing ngspice must
  degrade gracefully, never break the page.
- Do not modify `electrical.py`, `test_electrical.py`, or the root `README.md`
  body; add one short pointer section at the end of the root README.
- Server-rendered HTML, plain CSS, no client-side JS.

## UI design (matches the mockup)

Three columns under a header, collapsing to one column below ~960 px.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [chip] Lab 02: BJT DC Bias Web App                       ┌─────────────────┐ │
│        ENG29 2121 – Common Emitter (Voltage Divider Bias)│ </> Computer    │ │
│                                                          │ Programming for │ │
│                                                          │ EE              │ │
├─────────────────────┬──────────────────────────┬─────────────────────────────┤
│ ⚙ Input Parameters  │ 🔀 Circuit: CE Amplifier │ 📊 DC Bias Results          │
│                     │                          │                             │
│ VCC  [ 12.0 ][V ▾]  │        VCC ● 12 V        │  VB    2.20 V   (mono)      │
│ R1   [ 100.0 ][kΩ▾] │         │                │  VE    1.50 V               │
│ R2   [  22.0 ][kΩ▾] │        R1     RC         │  VC    8.70 V               │
│ RC   [   2.2 ][kΩ▾] │         │      │         │  VCE   7.20 V               │
│ RE   [   1.0 ][kΩ▾] │         ├──Q1──┤         │  IB   15.1 µA               │
│ β    [ 100.0 ][ — ] │         │  NPN │         │  IC    1.50 mA              │
│ VBE  [   0.70][V ▾] │        R2     RE         │  IE    1.51 mA              │
│                     │         │      │         │                             │
│ [ Calculate DC Bias ]│        ⏚      ⏚         │ ┌─────────────────────────┐ │
│                     │  (values track inputs)   │ │ ✅ Active region OK      │ │
│                     │                          │ │ VCE = 7.20 V > 0.3 V    │ │
│                     │                          │ └─────────────────────────┘ │
└─────────────────────┴──────────────────────────┴─────────────────────────────┘
```

Visual rules taken from the mockup:

- Page background light grey (`#f1f3f5`), white cards, 1 px `#d7dde3` border,
  ~10 px radius, subtle shadow.
- Primary teal (`#00796b`) for the calculate button and the header rule.
- Header: circuit-chip glyph, title 24 px semibold, subtitle 14 px muted, and a
  right-aligned rounded course badge with a `</>` glyph.
- Card headers: small glyph + 16 px semibold title, thin divider under it.
- Inputs: right-aligned numeric field, unit dropdown, one row per parameter,
  label with symbol and full name (`V_CC (Supply Voltage)`).
- Results: monospace right-aligned values with units, alternating row tint.
- Status box: green (active), amber (saturation), red (cutoff) with icon, title
  and the one-line justification (`VCE = … V > 0.3 V` or `< 0.3 V`).
- Below the results table, a compact "Cross-check" block: two extra rows for
  nodal and SPICE `IC` / `VCE` plus a pass/fail marker.

Schematic: one inline SVG in the template with Jinja-rendered labels (VCC, R1,
R2, RC, RE, Q1, β) so the picture always matches the current inputs and results.
No image files, no JS.

## Approaches considered

### App shape

1. **One page, POST to the same route** (chosen). Form, schematic and results in
   one template; the route validates, calls the pure module, re-renders. No JS,
   no client state, fully covered by Flask's test client.
2. **Two pages (form → results).** Extra template and a second request to carry
   seven numbers; no gain.
3. **JSON API + JS fetch.** Nicer partial updates, but adds an untested JS layer
   and a worse offline demo.

### Independent calculations

1. **Nodal analysis, 6×6 linear system, Gaussian elimination** (chosen in v1).
   Different derivation and different solver from the Thevenin closed form.
2. **SPICE (ngspice batch, `.op`)** (added, per your request). A genuinely
   different model — Ebers-Moll with exponential junctions — so it checks the
   numbers against a real simulator, not against our own assumptions.
3. **Fixed-point iteration on `IC`.** Independent but adds convergence cases for
   no gain; dropped.
4. **Recompute the closed form twice.** Rejected outright.

## Engineering model

Primary (Thevenin equivalent of the divider):

```
VBB = VCC * R2 / (R1 + R2)
RB  = R1 * R2 / (R1 + R2)
IB  = (VBB - VBE) / (RB + (beta + 1) * RE)
IC  = beta * IB
IE  = (beta + 1) * IB
VE  = IE * RE
VB  = VE + VBE
VC  = VCC - IC * RC
VCE = VC - VE
```

Independent nodal model (unknowns `IB, IC, IE, VB, VC, VE`):

```
(1) IC - beta*IB = 0
(2) IE - (beta+1)*IB = 0
(3) VB - VE = VBE
(4) (VCC - VB)/R1 - VB/R2 - IB = 0
(5) (VCC - VC)/RC - IC = 0
(6) VE/RE - IE = 0
```

Solved with Gaussian elimination and partial pivoting, stdlib only. Must agree
with the closed form within `1e-9` relative in the active region.

### Region rules (textbook, per your confirmation)

- **Cutoff** when `IB <= 0` (divider cannot forward-bias the junction).
  Reported: `IB = IC = IE = 0`, `VCE = VCC`. Labelled "transistor off"; the
  linear model is not valid, so `VBE` is not asserted and the cross-checks are
  reported as n/a.
- **Saturation** when `VCE < 0.3 V` (strict, `VCE,sat = 0.3 V`).
- **Active** otherwise (`VCE >= 0.3 V`).

In saturation the page shows the linear-model values plus a warning that the
real `VCE` sits near `0.3 V` and the linear result overstates `IC`. No clamping:
the app never invents a number it did not compute.

> The mockup's status line reads `> 0.2 V`. We agreed on the textbook 0.3 V, so
> the app says `> 0.3 V`. One constant to change if the course prefers 0.2 V.

## Validation rules

Per field: parse as float (reject empty, letters, `NaN`, `inf`), then:

| Field | Rule | Message |
|---|---|---|
| `VCC` | `> 0` | must be greater than 0 V |
| `R1`, `R2`, `RC`, `RE` | `> 0` (after unit scaling) | must be greater than 0 Ω |
| `beta` | `> 1` | must be greater than 1 |
| `VBE` | `0 <= VBE <= 1.0` | must be between 0 and 1 V |

Unit selectors: `V` for `VCC`/`VBE`; `Ω` and `kΩ` for the resistors. Scaling
happens in the parse layer, so the math module only ever sees SI. Errors are
per field and never produce a result. `VBB <= VBE` is not an input error; it is
reported as the cutoff operating point with a warning.

Rejected request values are echoed back into the form so the user does not
retype everything.

Defaults (an active point, close to the mockup): `VCC=12, R1=100k, R2=22k,
RC=2.2k, RE=1k, beta=100, VBE=0.7`.

### Note on the mockup numbers

The mockup shows `VB=2.20, VE=1.50, VC=8.70, VCE=7.20, IB=15.1 µA, IC=1.50 mA,
IE=1.51 mA` for `beta=100`. Those come from the **approximate** bias analysis
(assume the divider is unloaded: `VB ≈ VBB`, `IC ≈ IE`). The **exact** Thevenin
analysis of the same circuit gives `VB≈1.94, VE≈1.24, VC≈9.29, VCE≈8.05,
IB≈12.3 µA, IC≈1.23 mA, IE≈1.24 mA` — about 20 % lower current.

The textbook validity test for the approximation is `beta*RE >= 10*R2`; here
`100k < 220k`, so the approximation is **not** valid and the exact values are
the correct ones. The app therefore shows exact values (its numbers will differ
from the mockup for the same inputs). The drawing, layout, colours and wording
still match the mockup. Say the word if the course expects the approximate
method instead — it is a one-formula swap.

## SPICE cross-check

- `spice.py` builds a netlist in memory: `VCC` source, `R1/R2/RC/RE`, `Q1` with
  `.model QNPN NPN (BF=<beta> IS=1e-14 VAF=100)`, plus a `.control` block that
  runs `op` and prints `v(b) v(e) v(c) i(vcc)` (or writes a raw/log file).
- Runs `ngspice_con -b netlist.cir` in a temp directory with a 10 s timeout,
  never `shell=True`, and parses the printed operating point.
- Discovery order: `NGSPICE_BIN` env var → `shutil.which("ngspice")` →
  `.tools/ngspice*/**/ngspice_con.exe`. If none: `available=False`.
- UI: when available, the cross-check block shows SPICE `VBE`, `IC`, `VCE` and a
  verdict; when not, a muted line "SPICE not available (optional)" — the page
  and the other two methods are unaffected.
- **Agreement tolerance is not `1e-9` here**, because the models differ: our
  closed form fixes `VBE = 0.7 V` while SPICE solves the junction equation
  (`VBE ≈ 0.65 V` at this current, which raises `IC` by roughly 10 %). Verdict
  rule: `IC` and `VCE` within **15 % relative**, and the region must match.
  The panel shows both `VBE` values so the difference is explained, not hidden.
- Tests touching SPICE are `skipUnless(spice.available())`.

## Parts of the how

```
bjt_ce_bias/
  __init__.py
  bjt.py                 # pure engineering math, no Flask, no subprocess
  spice.py               # netlist builder + ngspice runner + parser
  app.py                 # Flask routes only
  templates/index.html   # header, 3 cards, inline SVG schematic
  static/style.css
  tests/__init__.py
  tests/test_bjt.py
  tests/test_spice.py    # skips without ngspice
  tests/test_app.py
  requirements.txt       # flask (pinned)
  README.md              # setup, run, test, worked hand calculation
```

- `bjt.py` — `BiasInputs` dataclass; `parse_inputs(raw) -> (inputs, errors)`;
  `solve_bias(inputs) -> BiasResult`; `nodal_solve(inputs) -> NodalResult`;
  `classify(result) -> Region + message`.
- `app.py` — `app = Flask(__name__)`, `GET /` default form, `POST /` validate →
  solve → nodal → spice → render. `if __name__ == "__main__": app.run(debug=True)`.
- Run from repo root: `.venv\Scripts\python -m bjt_ce_bias.app` → port 5000.
- Tests from repo root:
  `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`.

## Units and display

| Quantity | Unit | Display |
|---|---|---|
| `VCC`, `VBE`, `VB`, `VE`, `VC`, `VCE` | V | 3 decimals |
| `IB` | µA | 2 decimals (SI amps in tests) |
| `IC`, `IE` | mA | 3 decimals (SI amps in tests) |
| `R1, R2, RC, RE` | Ω input, `kΩ` shown | 1 decimal |
| `beta` | — | as entered |

Internally always SI (V, Ω, A). Formatting lives in a Jinja filter / helper,
never in the math module.

## Tests (acceptance)

1. Known active case → hand-computed `VB, VE, VC, VCE, IB, IC, IE`, `1e-9` rel.
2. `nodal_solve` agrees with `solve_bias` on the same case, `1e-9` rel.
3. Cutoff (`VBB <= VBE`) → region cutoff, zero currents, `VCE == VCC`.
4. Saturation (`VCE < 0.3`) → region saturation, warning present.
5. Boundary `VCE == 0.3` classified active (strict `<`).
6. Validation: non-numeric, empty, `<= 0`, `beta <= 1`, `VBE` outside `[0,1]`,
   and `kΩ` scaling each behave correctly.
7. `GET /` → 200; all seven inputs and the unit selects render.
8. `POST /` valid → 200, all seven quantities rendered, region box shown.
9. `POST /` invalid → 200, field errors rendered, no result values.
10. `POST /` when ngspice is unavailable → 200, "SPICE not available" shown.
11. SPICE test (skipped if absent): netlist runs, `IC`/`VCE` within 15 %,
    region matches the closed form.
12. Full suite green with the command above.

## Delivery

1. TDD per `test-driven-development`.
2. Localhost demo left running for the class; screenshots optional.
3. Commit on `main`, app + tests + design + requirements. Push if credentials
   allow.
4. Hand calculation for the default inputs in `bjt_ce_bias/README.md`:
   `VBB`, `RB`, `IB`, `IC`, `IE`, `VCE` to 4 significant figures.

## What is left to the builder

- Exact CSS values (spacing, badge sizes) within the rules above.
- Thai copy for labels/warnings (technical terms stay in English).
- Whether the header badge is a link to the course page (default: plain text).
- Pin of the Flask version (use whatever `pip` installs).
- How to unpack ngspice (`Expand-Archive` to `.tools/ngspice`) and the exact
  binary name for the downloaded build.

## Decisions made after the builder check

| Question | Decision |
|---|---|
| Which interpreter runs tests? | Repo-root `.venv`; every command uses `.venv\Scripts\python`. |
| Where is the app launched from? | Repo root, `-m bjt_ce_bias.app`; `__init__.py` in both dirs so `discover -t .` imports cleanly. |
| What counts as the independent check? | Nodal solve + SPICE + worked hand calculation, each labelled. |
