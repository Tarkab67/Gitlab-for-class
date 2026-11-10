# Lab 02: BJT DC Bias Web App

A minimal Flask app for the ENG29 2121 lab: enter the voltage-divider
common-emitter bias values and get the DC operating point, checked three ways.

- **Closed form** — Thevenin equivalent of the divider, exact (not the
  `β·RE ≥ 10·R2` shortcut).
- **Nodal solve** — independent 6×6 KCL system solved with Gaussian
  elimination; must match the closed form to `1e-9` relative.
- **SPICE** — real ngspice `.op` run when a binary is available; `IC` and
  `VCE` must agree within 15 % because ngspice solves the junction equation
  (`VBE ≈ 0.66 V`) while the closed form fixes `VBE = 0.7 V`.

Inputs: `VCC`, `R1`, `R2`, `RC`, `RE`, `β`, `VBE`. Resistors accept Ω or kΩ.
Outputs: `VB`, `VE`, `VC`, `VCE`, `IB`, `IC`, `IE`, plus an active /
saturation / cutoff verdict.

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

## Optional: ngspice

The SPICE check is optional; without it the page shows
"SPICE not available (optional)" and the other two methods still run.

To enable it, drop a portable ngspice build under `.tools/` (gitignored):

```powershell
mkdir .tools
tar -xf ngspice-47_64.7z -C .tools
# binary ends up at .tools/Spice64/bin/ngspice_con.exe
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
VCE = 9.294 - 1.242                      = 8.052 V   (active, > 0.3 V)
```

Region rules: `IB ≤ 0` → cutoff (`IB = IC = IE = 0`, `VCE = VCC`);
`VCE < 0.3 V` → saturation; otherwise active.

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
