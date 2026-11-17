# Lab 03: BJT DC Bias Web App

A minimal Flask app for the ENG29 2121 labs: choose one of three NPN
common-emitter DC bias topologies, enter that mode's values, and get the
operating point. The voltage-divider mode keeps the Lab 02 results and its
three-way check.

## Modes

| Mode | Inputs | Base current |
|------|--------|--------------|
| Voltage Divider | `VCC`, `R1`, `R2`, `RC`, `RE`, `β`, `VBE` | `IB = (VTH − VBE) / (RTH + (β+1)RE)` |
| Fixed | `VCC`, `RB`, `RC`, `β`, `VBE` | `IB = (VCC − VBE) / RB`, `VE = 0` |
| Emitter | `VCC`, `RB`, `RC`, `RE`, `β`, `VBE` | `IB = (VCC − VBE) / (RB + (β+1)RE)` |

All modes: `IC = β·IB`, `IE = (β+1)·IB`, `VE = IE·RE`, `VB = VE + VBE`,
`VC = VCC − IC·RC`, `VCE = VC − VE`. Resistors accept Ω or kΩ. Outputs are
`VB`, `VE`, `VC`, `VCE`, `IB`, `IC`, `IE` with units.

The mode selector reloads the form so only the needed fields appear (no
JavaScript). The equations live in `bjt.py`; the template never computes them.
The Circuit card is drawn for all three modes with the values entered: Fixed
shows `RB` from VCC to base, `RC` to the collector and the emitter tied to
ground; Emitter adds `RE` from emitter to ground; Divider keeps its Lab 02
diagram. A rejected field falls back to its default only in the diagram while
the form keeps the typed value.

## Voltage-divider independent checks (Lab 02)

- **Closed form** — Thevenin equivalent of the divider, exact (not the
  `β·RE ≥ 10·R2` shortcut).
- **Nodal solve** — independent 6×6 KCL system solved with Gaussian
  elimination; must match the closed form to `1e-9` relative.
- **SPICE** — real ngspice `.op` run when a binary is available; `IC` and
  `VCE` must agree within 15 % because ngspice solves the junction equation
  (`VBE ≈ 0.66 V`) while the closed form fixes `VBE = 0.7 V`.

The nodal/SPICE panel is shown for the voltage-divider mode only. Fixed and
emitter bias show the results and the model-limit warning.

## Model-limit warning

For every mode, if `IB ≤ 0` or `VCE ≤ 0.2 V` the page keeps the raw
forward-active numbers and adds a warning that the model may not apply.
It does not re-solve cutoff or saturation. (`VCE_SAT = 0.2 V`.)

At the divider limit the region badge and the Lab 02 cross-check wording are
still shown; the cross-check is not re-solved in cutoff.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r bjt_ce_bias/requirements.txt
```

## Run

```powershell
.venv\Scripts\python -m bjt_ce_bias.app
```

Then open http://127.0.0.1:5000 and press **Calculate DC Bias**.

## Test

```powershell
.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v
```

37 tests. Browser validation of A1–A5 is recorded in
[`../docs/validation.md`](../docs/validation.md).

Repository: <https://github.com/Tarkab67/Gitlab-for-class> (branch `main`).
Validated code commit: `1a2e354`.

**AI assistance:** the code, tests, and docs were generated with an AI agent
(DeepSeek V4.1 Flash in OpenCode) and must be checked by the student against
the Lab 03 sheet before submission. The student checks are listed in the
validation document.

## Optional: ngspice

The SPICE check is optional; without it the page shows
"SPICE not available (optional)" and the other two methods still run.

To enable it, drop a portable ngspice build under `.tools/` (gitignored):

```powershell
mkdir .tools
tar -xf ngspice-47_64.7z -C .tools\ngspice
# Windows 10+ tar (bsdtar) reads .7z; alternatively use 7-Zip.
# Binary: .tools\ngspice\Spice64\bin\ngspice_con.exe
```

Lookup order: `NGSPICE_BIN` environment variable → `ngspice` on `PATH` →
`.tools/**/ngspice_con.exe`.

## Worked hand calculation (default values)

Defaults: `VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`,
`RE = 1 kΩ`, `β = 100`, `VBE = 0.7 V`.

```
VBB = 12 * 22k / (100k + 22k)             = 2.164 V
RB  = 100k || 22k                        = 18.03 kΩ
IB  = (2.164 - 0.7) / (18.03k + 101 * 1k) = 12.30 µA
IC  = 100 * 12.30 µA                     = 1.230 mA
IE  = 101 * 12.30 µA                     = 1.242 mA
VE  = 1.242 mA * 1k                      = 1.242 V
VB  = 1.242 + 0.7                        = 1.942 V
VC  = 12 - 1.230 mA * 2.2k               = 9.294 V
VCE = 9.294 - 1.242                      = 8.052 V   (active, > 0.2 V)
```

Region rules in the Lab 02 helper `solve_bias`: `IB ≤ 0` → cutoff
(`IB = IC = IE = 0`, `VCE = VCC`); `VCE < 0.2 V` → saturation; otherwise
active. The web page displays the raw forward-active values (no zeroing) and
adds the model-limit warning when `IB ≤ 0` or `VCE ≤ 0.2 V`.

## Layout

```
bjt_ce_bias/
  bjt.py           # pure math: parsing, closed form, nodal solve, region
  formatting.py    # SI -> display strings
  spice.py         # netlist, ngspice runner, parser, agreement check
  app.py           # Flask routes
  templates/       # index.html (three cards + inline SVG schematic)
  static/          # style.css
  tests/           # unittest suites
```
