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

## Lab 03 — ผลทดสอบ A1–A5

ทดสอบใน OpenCode Browser ค่าร่วม: VCC = 12 V, RC = 2.2 kΩ, β = 100,
VBE = 0.70 V. ค่าคาดเคลื่อนที่ยอมรับ: IC ±0.01 mA, VCE ±0.02 V.

| ID | โหมด / ค่าที่กรอก | IC คาดหมาย (mA) | VCE คาดหมาย (V) | IC ที่เห็น (mA) | VCE ที่เห็น (V) | ผล |
|----|-------------------|------------------|------------------|-----------------|-----------------|-----|
| A1 | Voltage Divider — R1 100 kΩ, R2 22 kΩ, RE 1 kΩ | 1.2299 | 8.0522 | 1.230 | 8.052 | PASS |
| A2 | Fixed — RB 1000 kΩ (ไม่มีช่อง RE) | 1.1300 | 9.5140 | 1.130 | 9.514 | PASS |
| A3 | Emitter — RB 1000 kΩ, RE 1 kΩ | 1.0263 | 8.7055 | 1.026 | 8.705 | PASS |
| A4 | Emitter — RB 1000 kΩ, RE 2 kΩ | 0.9401 | 8.0328 | 0.940 | 8.033 | PASS |
| A5 | Fixed — RB 0 kΩ | — | — | field error | — | PASS |

A5: หน้าขึ้น `RB: RB must be greater than 0 Ω`, ยังเก็บค่า `0` ไว้ในฟอร์ม,
ไม่แสดงตารางผลลัพธ์ และหน้าไม่ล้ม (ไม่มีผลเก่าของ A2 ค้างอยู่)

ค่าที่วัดได้ครบทั้ง 7 ตัว (VB, VE, VC, VCE, IB, IC, IE) และการคำนวณด้วยมือ
อยู่ใน [`docs/validation.md`](docs/validation.md) (A1–A5, OpenCode Browser).
Design and plan:
[`docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`](docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md)
and
[`docs/superpowers/plans/2026-11-17-lab03-multi-bias.md`](docs/superpowers/plans/2026-11-17-lab03-multi-bias.md).

Repository: <https://github.com/Tarkab67/Gitlab-for-class> (branch `main`).
A1–A5 above were observed on `1a2e354`; later commits only add UI diagrams and
docs, so the results are unchanged. Current `main`: `3dc7584`.

**AI assistance:** an AI agent (DeepSeek V4.1 Flash in OpenCode) generated the
Lab 03 code, test adjustments, plan, README text, and validation document. The
student must personally verify before submission: read the three equation sets
against the Lab 03 sheet, run the 37-test command above, and repeat A1–A5 in
the browser. Details are in the "AI assistance and student checks" section of
[`docs/validation.md`](docs/validation.md).
