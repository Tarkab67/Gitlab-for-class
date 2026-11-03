def analyze_dc(voltage_v, resistance_ohm):
    if resistance_ohm <= 0:
        raise ValueError("Resistance must be positive")

    current_a = voltage_v / resistance_ohm
    power_w = voltage_v * current_a
    return {"current_a": current_a, "power_w": power_w}


if __name__ == "__main__":
    try:
        voltage_v = float(input("กรอกแรงดันไฟฟ้า (V): "))
        resistance_ohm = float(input("กรอกความต้านทาน (Ω): "))
        result = analyze_dc(voltage_v, resistance_ohm)
        print(f"กระแส: {result['current_a']:.2f} A")
        print(f"กำลัง: {result['power_w']:.2f} W")
    except ValueError as e:
        print(f"เกิดข้อผิดพลาด: {e}")