# Lab 03 — Multi-mode BJT DC Bias (design)

- Date: 2026-11-17
- Builds on: Lab 02 app (`bjt_ce_bias/`, commit `2ff4f1a`)
- Lab sheet: `C:\Users\B6839239\Downloads\ENG29_2121_Lab03_BJT_Bias_Web_App.html`

## Intent

Extend the existing Flask app so it calculates three NPN common-emitter DC
bias topologies from one page: **Fixed Bias**, **Emitter Bias (single
supply)**, and the existing **Voltage Divider Bias**. The divider path must
keep producing exactly the same numbers as Lab 02 for the same inputs (A1).
Equations stay in Python, never in the template. The lab is validated through
a real browser (A1–A5), not new unit tests.

## Goals

- Mode selector; only the fields that the chosen mode needs are rendered.
- Per-mode validation (missing, non-numeric, non-finite, ≤ 0 → field error).
- Unknown mode → explicit error, never silently treated as divider.
- Results show `VB, VE, VC, VCE, IB, IC, IE` with units and the mode name.
- Warning (not a re-solve) when `IB ≤ 0` or `VCE ≤ 0.2 V`: the forward-active
  model may not apply; cutoff/saturation are not calculated.
- `docs/validation.md` with A1–A5, expected values computed independently,
  observed values, method (`OpenCode Browser`), statuses, and screenshots.
- README update, commit, push.

## Non-goals

- AC/transient, load line, SPICE for the new modes (Lab 03 says not yet).
- New unit tests or Playwright scripts (lab sheet: existing tests kept, no new
  `unittest`). Existing 37 tests must stay green after the threshold update.
- JavaScript for mode switching.

## Anti-goals

- Equations duplicated in `app.py` or `index.html`.
- Old results silently shown as if they belonged to the new submission.
- Turning a model-limit case into a fake cutoff/saturation solution.

## Constraints

- Stack stays Flask + Jinja + stdlib math, same package layout.
- Windows, venv `.venv`, tests: `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`.
- Divider numeric output must equal Lab 02 (A1: IC 1.2299 mA, VCE 8.0522 V).

## Approaches considered (UI)

- **A. Separate GET mode form + POST calculate form (chosen).** A small GET
  form with a mode dropdown and a "Load mode" button re-renders the input card
  with only that mode's fields; a second form POSTs the values. No JS, clean
  validation, matches the lab's "load the form again" wording. Cost: one extra
  click when switching modes.
- **B. One form with all fields, irrelevant ones disabled.** One click to
  submit, but the card is noisy and error states must re-render the correct
  mode. Rejected as less clear for a lab demo.

## Decisions (executor)

- **Threshold:** `VCE_SAT = 0.2` for every mode, per the Lab 03 sheet. The Lab 02
  boundary test and saturation message are updated from 0.3 V to 0.2 V; divider
  numbers do not change (A1 VCE is 8.05 V, far from the boundary).
- **Result contract:** the mode dispatcher returns a dict with shared keys
  `mode, vb_v, ve_v, vc_v, vce_v, ib_a, ic_ma, ie_ma, warning`. Divider keeps
  `solve_bias() -> BiasResult` for the Lab 02 tests and the SPICE/nodal panel;
  a new `solve_bias_forward()` computes the same forward-active formulas without
  the cutoff zeroing, so the displayed dict and the cross-check cannot drift.
- **Divider at the model limit (decided):** the results table always shows the
  raw forward-active values from `solve_bias_forward()` — no zeroing to
  `IB=IC=IE=0`, no invented cutoff/saturation solution — and the amber model
  warning is shown alongside. The divider region badge stays, computed from
  those same raw values (`IB ≤ 0` → cutoff, `VCE < 0.2 V` → saturation). The
  cross-check panel keeps its Lab 02 wording ("n/a — the transistor is off")
  for non-positive `IB`; it is not re-solved. This preserves
  `test_cutoff_shows_crosscheck_not_applicable` (it only asserts that text and
  the absence of "Nodal KCL solve").
- **Circuit card (decided):** shown unchanged for divider; hidden entirely for
  Fixed and Emitter. No new SVGs this week (out of the lab scope).
- **Page identity (decided):** title and `<h1>` become
  "Lab 03: BJT DC Bias Web App", subtitle "ENG29 2121 – Common Emitter
  (Fixed, Emitter, Voltage Divider Bias)". The single assertion in
  `tests/test_app.py` is updated to match; the suite count stays 37.
- **A1 baseline (decided):** no pre-change capture needed. The Lab 02 values
  are already pinned in commit `2ff4f1a` and in this document; post-change A1
  is compared against IC 1.2299 mA / VCE 8.0522 V.
- **Cross-check panel:** unchanged for divider (nodal + SPICE). New modes show
  results + warning only; the panel is omitted there, per the lab scope.
- **Browser method:** OpenCode Browser (allowed fallback), recorded as such in
  `docs/validation.md`.
- **Mode defaults:** divider `12 V, R1=100k, R2=22k, RC=2.2k, RE=1k, β=100,
  VBE=0.7`; fixed `RB=1000k, RC=2.2k`; emitter `RB=1000k, RE=1k, RC=2.2k`.

## Equations (forward active)

```
Fixed:   IB = (VCC - VBE) / RB
Emitter: IB = (VCC - VBE) / (RB + (beta + 1) RE)
Divider: IB = (VTH - VBE) / (RTH + (beta + 1) RE)
         VTH = VCC R2 / (R1 + R2),  RTH = R1 R2 / (R1 + R2)
All:     IC = beta IB,  IE = (beta + 1) IB
         VE = IE RE  (fixed: VE = 0)
         VB = VE + VBE,  VC = VCC - IC RC,  VCE = VC - VE
```

Ranges follow Lab 02: `VCC > 0`, resistors `> 0`, `beta > 1`,
`0 <= VBE <= 1`; resistors accept Ω or kΩ and are converted once at parse.

## Architecture / files

- `bjt_ce_bias/bjt.py`
  - `VCE_SAT = 0.2`; `region_message` wording updated.
  - `solve_bias_forward(BiasInputs) -> BiasResult` (no cutoff zeroing);
    `solve_bias()` keeps Lab 02 cutoff behaviour by wrapping it.
  - `FixedBiasInputs`, `EmitterBiasInputs`; `solve_fixed_bias()`,
    `solve_emitter_bias()` returning result dicts.
  - `solve_operating_point(mode, ...) -> dict` dispatcher (also used by the app).
  - `parse_fixed(raw)`, `parse_emitter(raw)`; shared `_parse_common` /
    `_parse_resistors`; existing `parse_inputs` for divider kept.
  - `warning_for(ib, vce) -> str | None`.
- `bjt_ce_bias/app.py`
  - `GET /?mode=...` renders the selected mode's form; invalid mode → error.
  - `POST /` reads hidden `mode` (missing → divider for backward compatibility
    with the Lab 02 tests), parses per mode, solves, renders.
  - Divider keeps the nodal/SPICE context; other modes get `None` context.
- `bjt_ce_bias/templates/index.html`
  - Title/`<h1>` renamed to Lab 03; mode GET form; conditional field blocks;
    result rows from the dict; amber model warning box; mode name in the
    results heading; divider region badge and cross-check unchanged; Circuit
    card rendered only for divider.
- `bjt_ce_bias/static/style.css`
  - `.mode-switch`, `.status-warning` (reuse amber tokens).
- `docs/validation.md` (new), `README.md` / `bjt_ce_bias/README.md` updates.

## Acceptance table (pre-computed before running)

Shared: VCC 12 V, RC 2.2 kΩ, β 100, VBE 0.70 V. Tolerance: IC ±0.01 mA,
VCE ±0.02 V.

| ID | Mode / inputs | Expected IC (mA) | Expected VCE (V) | Extra check |
|----|---------------|------------------|------------------|-------------|
| A1 | Divider, R1=100k, R2=22k, RE=1k | 1.2299 | 8.0522 | equals Lab 02 |
| A2 | Fixed, RB=1000k | 1.1300 | 9.5140 | RE not required |
| A3 | Emitter, RB=1000k, RE=1k | 1.0263 | 8.7055 | RE used |
| A4 | Emitter, same as A3, RE=2k | 0.9401 | 8.0328 | IC decreases vs A3 |
| A5 | Fixed, RB=0 | — | — | field error, page alive, no stale result |

Reference derivations (unrounded):

- A2: IB = 11.3/1e6 = 11.3 µA → IC = 1.13 mA; VC = 12 − 2.486 = 9.514 V.
- A3: IB = 11.3/(1e6 + 101k) = 10.2634 µA → IC = 1.02634 mA;
  VE = 1.03660 V; VC = 9.74205 V; VCE = 8.70545 V.
- A4: IB = 11.3/(1e6 + 202k) = 9.4010 µA → IC = 0.94010 mA;
  VE = 1.89900 V; VC = 9.93178 V; VCE = 8.03278 V.

## Verification

1. Existing 37 tests green after the 0.2 V threshold update.
2. Run Flask, check A1–A5 with OpenCode Browser, capture at least one
   screenshot, save observations in `docs/validation.md`.
3. Demonstrate A3→A4 direction (IC decreases when RE rises).
4. `git diff` review, commit, push.

## Risks

- Divider regression from the shared formula refactor → A1 pins the exact
  Lab 02 numbers and the full suite stays green.
- Threshold change ripples into the old boundary test → update only that test
  and the message; other tests untouched.
- Stale results after an invalid submit → error renders no result block.
