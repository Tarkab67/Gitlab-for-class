def analyze_dc(voltage_v, resistance_ohm):
    if resistance_ohm == 0:
        raise ValueError("ความต้านทานต้องไม่เป็น 0")
    if voltage_v < 0 or resistance_ohm < 0:
        raise ValueError("แรงดันและความต้านทานต้องเป็นค่าบวก")

    current_a = voltage_v / resistance_ohm
    power_w = voltage_v * current_a
    return {"current_a": current_a, "power_w": power_w}


def _read_float(prompt_text):
    while True:
        try:
            return float(input(prompt_text))
        except ValueError:
            print("กรุณากรอกตัวเลขที่ถูกต้อง")


if __name__ == "__main__":
    try:
        voltage_v = float(input("กรอกแรงดันไฟฟ้า (V): "))
        resistance_ohm = float(input("กรอกความต้านทาน (Ω): "))
        result = analyze_dc(voltage_v, resistance_ohm)
        print(f"กระแส: {result['current_a']:.2f} A")
        print(f"กำลัง: {result['power_w']:.2f} W")
    except ValueError as e:
        print(f"เกิดข้อผิดพลาด: {e}")