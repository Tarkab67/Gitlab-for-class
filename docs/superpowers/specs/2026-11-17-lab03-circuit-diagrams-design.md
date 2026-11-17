# Lab 03 — Circuit diagrams for Fixed and Emitter bias (design)

- Date: 2026-11-17
- Builds on: `docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`
- Supersedes: the "Circuit card (decided)" bullet that hid the card for Fixed
  and Emitter
- Size: small change (short design, no builder check)

## Intent

Show a circuit diagram for every bias mode, not only Voltage Divider. Each
diagram is drawn from the same values the user submitted, so the picture and
the form never disagree.

## Goals

- Add a Fixed-bias SVG and an Emitter-bias SVG in the same visual style as the
  existing divider schematic.
- Show live values: `VCC`, `RB`, `RC`, `RE` (where the mode has one), and `β`,
  formatted like the divider (`V`, `kΩ`, plain β).
- Keep the card visible for all three modes.
- Reuse the divider error behaviour: a rejected field falls back to its default
  in the diagram while the form keeps the typed value.

## Non-goals

- No new equations, no change to results, no JavaScript, no new dependencies.
- No load line, no AC/transient, no bypass capacitors.
- No screenshots or validation rerun beyond a browser sanity check (A1–A5
  results are unchanged).
- No new `unittest` file; the existing 37 tests stay green.

## Approaches

1. **Three SVG blocks + mode-aware schematic context (chosen).** Add two SVG
   blocks beside the divider block, guarded by `mode`. Generalize the schematic
   label builder and the per-field fallback to take the mode. Pros: matches the
   existing markup and styling, easy to read, no new machinery. Cons: some SVG
   geometry is repeated.
2. **One parametrized SVG macro with optional parts.** Pros: less repetition.
   Cons: conditional geometry is harder to review and easy to misplace; the
   gain is small for two diagrams.
3. **Static image files without live values.** Rejected: the user chose live
   values, and static images would drift from the form.

## Design

- `app.py`
  - `SCHEMATIC_FIELDS = {"divider": ("vcc", "r1", "r2", "rc", "re"),
    "fixed": ("vcc", "rb", "rc"), "emitter": ("vcc", "rb", "rc", "re")}`.
  - `_schematic(inputs, fields)` formats only the fields that mode draws, then
    adds `beta`.
  - `PARSERS = {"divider": parse_inputs, "fixed": parse_fixed,
    "emitter": parse_emitter}`.
  - `_schematic_inputs(mode, form, errors)` keeps valid typed values, replaces
    rejected fields with `DEFAULT_FORM`, and falls back to the mode defaults if
    parsing still fails. Divider behaviour is unchanged.
  - `_render` builds `schematic` for every mode; the divider still adds the
    nodal/SPICE verdict context.
  - `index` computes `schematic_inputs` for every mode and passes the submitted
    `inputs` to `_render`, so a successful POST draws the real values.
- `templates/index.html`
  - Circuit card rendered for every mode.
  - Divider keeps `id="schematic"`; new ids are `schematic-fixed` and
    `schematic-emitter`.
  - Fixed diagram: VCC rail, `RB` from rail to base, `RC` from rail to
    collector, emitter tied directly to ground, `β` label.
  - Emitter diagram: VCC rail, `RB` from rail to base, `RC` from rail to
    collector, `RE` from emitter to ground, `β` label.
  - Same classes (`wire`, `part`, `lbl`, `val`, `arrow`) and viewBox as the
    divider.
- `static/style.css`: no change expected; reuse existing schematic styles.
- Docs: append the new decision to the Lab 03 design doc and note in
  `bjt_ce_bias/README.md` that the circuit card is drawn for every mode.

## Verification

- Existing suite: 37 tests OK.
- Scripted test client: each mode's page contains only its own schematic id
  and the current values; divider still renders `id="schematic"`;
  `?mode=fixed` and `?mode=emitter` contain their values; `RB = 0` shows the
  fallback value in the diagram while the input keeps `0`.
- Browser: open Fixed and Emitter, confirm the topology, values, and that the
  diagram updates after a successful calculate.
- Commit and push to `main`; report the new SHA.
