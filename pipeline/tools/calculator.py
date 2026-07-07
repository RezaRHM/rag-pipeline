"""
tools/calculator.py
─────────────────────────────────────────────────────────
محاسبات فنی رو انجام میده — LLM نباید اعداد رو حدس بزنه.

این ماژول از context اعداد رو استخراج میکنه و محاسبه
واقعی انجام میده.
─────────────────────────────────────────────────────────
"""

import re
import math


def calculate_power_dbm_to_watts(dbm: float) -> float:
    """dBm به وات تبدیل میکنه"""
    return 10 ** ((dbm - 30) / 10)


def calculate_watts_to_dbm(watts: float) -> float:
    """وات به dBm تبدیل میکنه"""
    return 10 * math.log10(watts) + 30


def calculate_cable_loss(power_watts: float, loss_db: float) -> float:
    """توان بعد از ضرر کابل رو حساب میکنه"""
    loss_factor = 10 ** (-loss_db / 10)
    return power_watts * loss_factor


def extract_numbers_from_text(text: str) -> list:
    """اعداد و واحدهاشون رو از متن استخراج میکنه"""
    pattern = r"(\d+(?:\.\d+)?)\s*(watts?|W|dBm|dB|MHz|GHz|V|A|°C|°F|kg|m)?"
    matches = re.findall(pattern, text, re.IGNORECASE)
    return [{"value": float(m[0]), "unit": m[1]} for m in matches if m[0]]


def safe_calculate(expression: str) -> dict:
    """
    یه expression ریاضی ساده رو امن محاسبه میکنه.
    فقط عملیات پایه مجازه (نه eval مستقیم).
    """
    allowed = set("0123456789+-*/()., ")
    if not all(c in allowed for c in expression):
        return {"success": False, "error": "invalid_characters"}

    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return {"success": True, "result": float(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}