# Gitlab-for-class
Lab Compro for EE 

DC Circuit Calculator (โปรแกรมคำนวณวงจรไฟฟ้ากระแสตรง)

คำอธิบาย: เครื่องมือคำนวณค่าทางไฟฟ้าสำหรับวงจรตัวต้านทานที่ต่อแบบอนุกรม ขนาน และผสม โดยผู้ใช้กรอกค่าแรงดันไฟฟ้าและความต้านทาน ระบบจะประมวลผลตามกฎของโอห์มและกฎของเคอร์ชฮอฟฟ์พร้อมแสดงผลลัพธ์ผ่านหน้าต่างแสดงผล

วัตถุประสงค์: เพื่อคำนวณค่ากระแสไฟฟ้า (Current) ความต่างศักย์ (Voltage) และกำลังไฟฟ้า (Power) รวมของวงจรตัวต้านทานได้อย่างถูกต้องและรวดเร็ว
## Lab 02/03: BJT DC Bias Web App (ENG29 2121)

Flask app: `bjt_ce_bias/` (calculation engine, Flask routes, tests, lab README).

Three NPN common-emitter DC modes: **Voltage Divider Bias** (Lab 02, unchanged
results), **Fixed Bias**, and **Emitter Bias**. Pick a mode and press
**Load mode**; the form shows only that mode's fields. The warning rule for all
modes is `VCE_SAT = 0.2 V`: if `IB ≤ 0` or `VCE ≤ 0.2 V`, the page reports that
the forward-active model may not apply and does not invent a cutoff/saturation
solution.

Run `.venv\Scripts\python -m bjt_ce_bias.app`, then open http://127.0.0.1:5000.

Test: `.venv\Scripts\python -m unittest discover -s bjt_ce_bias/tests -t . -v`
(37 tests).

Lab 03 evidence: [`docs/validation.md`](docs/validation.md) (A1–A5, OpenCode
Browser). Design and plan:
[`docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`](docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md)
and
[`docs/superpowers/plans/2026-11-17-lab03-multi-bias.md`](docs/superpowers/plans/2026-11-17-lab03-multi-bias.md).

Repository: <https://github.com/Tarkab67/Gitlab-for-class> (branch `main`).
The code commit validated in `docs/validation.md` is `1a2e354`; this delivery
metadata is a later docs-only commit.

**AI assistance:** an AI agent (DeepSeek V4.1 Flash in OpenCode) generated the
Lab 03 code, test adjustments, plan, README text, and validation document. The
student must personally verify before submission: read the three equation sets
against the Lab 03 sheet, run the 37-test command above, and repeat A1–A5 in
the browser. Details are in the "AI assistance and student checks" section of
[`docs/validation.md`](docs/validation.md).
