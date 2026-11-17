# Lab 03 Circuit Diagrams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw a live-value circuit diagram for the Fixed and Emitter bias modes, matching the existing Voltage Divider diagram.

**Architecture:** `app.py` builds a per-mode schematic label dict from the submitted (or default) inputs using the existing parsers and `format_compact`. `index.html` renders one of three SVG blocks based on `mode`. No equations or results change.

**Tech Stack:** Python 3, Flask, Jinja2, existing CSS/SVG classes, existing venv and unittest suite.

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-circuit-diagrams-design.md`

## Global Constraints

- Equations stay in `bjt_ce_bias/bjt.py`; the template draws, never computes.
- No JavaScript, no new dependencies, no new `unittest` file; the 37 existing tests must pass.
- Divider output and ids must not change: it keeps `id="schematic"` and the same values.
- Fixed diagram: `RB` VCC→base, `RC` VCC→collector, emitter tied to ground, no `RE`.
- Emitter diagram: `RB` VCC→base, `RC` VCC→collector, `RE` emitter→ground.
- Values use `format_compact`: `V`, `kΩ`, and plain β, same as the divider.
- A rejected field falls back to its default only in the diagram; the form keeps the typed value.
- Use `$env:PYTHONIOENCODING="utf-8"` for commands that print `Ω`.

## Review Focus

- Divider page still renders exactly one `id="schematic"` with the same labels after the refactor.
- `RB = 0` on a Fixed POST: diagram shows the default `1000 kΩ`, input still shows `0`, no results table.
- Switching modes never leaves another mode's SVG or label on the page.
- A successful POST draws the submitted values, not the defaults.
- `kΩ` and `β` render correctly (no mojibake) in both new diagrams.

---

### Task 1: Per-mode schematic data and SVG blocks

**Files:**
- Modify: `bjt_ce_bias/app.py`
- Modify: `bjt_ce_bias/templates/index.html`

**Interfaces:**
- Consumes: `parse_inputs`, `parse_fixed`, `parse_emitter`, `format_compact`, `DEFAULT_FORM`.
- Produces:
  - `SCHEMATIC_FIELDS = {"divider": ("vcc", "r1", "r2", "rc", "re"), "fixed": ("vcc", "rb", "rc"), "emitter": ("vcc", "rb", "rc", "re")}`
  - `PARSERS = {"divider": parse_inputs, "fixed": parse_fixed, "emitter": parse_emitter}`
  - `_schematic(inputs, fields) -> dict[str, str]`
  - `_schematic_inputs(mode, form, errors) -> inputs`
  - template ids `schematic`, `schematic-fixed`, `schematic-emitter`

- [ ] **Step 1: Write the failing page check**

Run this scripted test-client check:

```powershell
$env:PYTHONIOENCODING="utf-8"
@'
from bjt_ce_bias.app import app
c = app.test_client()
def html(r): return r.get_data(as_text=True)
d = html(c.get("/"))
f = html(c.get("/?mode=fixed"))
e = html(c.get("/?mode=emitter"))
assert d.count('id="schematic"') == 1
assert 'id="schematic-fixed"' in f and "1000 kΩ" in f and "RB" in f
assert 'id="schematic-emitter"' in e and "1000 kΩ" in e and "RE" in e
assert 'id="schematic-fixed"' not in e and 'id="schematic-emitter"' not in f
assert 'id="schematic"' not in f
print("schematic cards OK")
'@ | .venv\Scripts\python -
```

Expected: FAIL because the new ids are absent.

- [ ] **Step 2: Generalize the schematic helpers in `app.py`**

Replace `_schematic(inputs)` with `_schematic(inputs, fields)` that formats only
`fields` plus `beta`. Add `SCHEMATIC_FIELDS` and `PARSERS` near `MODES`.
Replace `_schematic_inputs(form, errors)` with `_schematic_inputs(mode, form,
errors)`: keep valid typed values, replace rejected `DEFAULT_FORM` fields,
parse with `PARSERS[mode]`, fall back to the mode defaults if still invalid.

- [ ] **Step 3: Build the schematic for every mode in `_render` and `index`**

In `_render`, when `inputs is None`, parse `DEFAULT_FORM` with `PARSERS[mode]`;
always set `context["schematic"] = _schematic(inputs, SCHEMATIC_FIELDS[mode])`.
Keep `_verdict_context` for divider only.

In `index`, after parsing, set
`schematic_inputs = _schematic_inputs(mode, form, errors)` for every mode; pass
`schematic_inputs` on the error paths and the parsed `inputs` on success (not
just for divider).

- [ ] **Step 4: Add the two SVG blocks**

Change the circuit guard to render for all modes. Keep the divider block as-is
(`id="schematic"`, viewBox `0 0 340 300`). Add:

- Fixed: `id="schematic-fixed"`, aria-label "Fixed-bias common-emitter circuit";
  VCC rail and label; `RB` vertical from rail to the base node; base lead;
  the same Q1 NPN drawing and `β = {{ schematic.beta }}`; `RC` from rail to
  collector; emitter lead straight to a ground symbol at the bottom.
- Emitter: `id="schematic-emitter"`, aria-label "Emitter-bias common-emitter
  circuit"; VCC rail; `RB` to the base node; base lead; Q1; `RC`; `RE` from the
  emitter to ground, same shape as the divider's RE branch.

Reuse `wire`, `part`, `lbl`, `val`, `arrow`; keep the divider's coordinates for
shared parts so the diagrams line up visually.

- [ ] **Step 5: Run the page check**

Run the Step 1 script. Expected: `schematic cards OK`.

- [ ] **Step 6: Run the full suite**

Run: `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`
Expected: 37 tests OK.

- [ ] **Step 7: Check the error fallback**

```powershell
$env:PYTHONIOENCODING="utf-8"
@'
from bjt_ce_bias.app import app
c = app.test_client()
h = c.post("/", data={"mode":"fixed","vcc":"12","rb":"0","rc":"2.2","beta":"100",
    "vbe":"0.7","rb_unit":"kohm","rc_unit":"kohm"}).get_data(as_text=True)
assert 'value="0"' in h and "1000 kΩ" in h and "results-table" not in h
ok = c.post("/", data={"mode":"fixed","vcc":"12","rb":"470","rc":"2.2","beta":"100",
    "vbe":"0.7","rb_unit":"kohm","rc_unit":"kohm"}).get_data(as_text=True)
assert "470 kΩ" in ok and "2.2 kΩ" in ok
print("fallback OK")
'@ | .venv\Scripts\python -
```

Expected: `fallback OK`.

- [ ] **Step 8: Commit**

```bash
git add bjt_ce_bias/app.py bjt_ce_bias/templates/index.html
git commit -m "feat: draw fixed and emitter bias circuit diagrams"
```

---

### Task 2: Browser check, docs, final verification, push

**Files:**
- Modify: `bjt_ce_bias/README.md`
- Modify: `docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`

**Interfaces:**
- Consumes: the running app from Task 1.

- [ ] **Step 1: Browser check**

Start `.venv\Scripts\python -m bjt_ce_bias.app`, open
http://127.0.0.1:5000 in OpenCode Browser, load Fixed and Emitter, confirm the
topology and live values, then press Calculate and confirm the values update.
Divider must look unchanged.

- [ ] **Step 2: Update the docs**

In `bjt_ce_bias/README.md`, state that the circuit card is drawn for every mode
with the values entered. In the multi-bias design doc, append a line under the
circuit-card decision that the 2026-11-17 circuit-diagrams design supersedes it.

- [ ] **Step 3: Run the suite and review the diff**

Run the test command; expected 37 tests OK. Run `git status --short` and
`git diff`; only the intended files should change.

- [ ] **Step 4: Commit and push**

```bash
git add bjt_ce_bias/README.md docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md
git commit -m "docs: note circuit diagrams for all bias modes"
git push origin main
git rev-parse HEAD
git status -sb
```

Expected: push succeeds; `## main...origin/main` with no ahead/behind.
