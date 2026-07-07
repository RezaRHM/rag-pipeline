"""
language/language_detector.py
─────────────────────────────────────────────────────────
تشخیص زبان سوال کاربر — برای اینکه بدونیم:
  ۱. LLM باید به چه زبانی جواب بده
  ۲. آیا نیاز به query expansion داریم (اصطلاحات انگلیسی
     فنی رو به سوال غیرانگلیسی اضافه کنیم یا نه)
─────────────────────────────────────────────────────────
"""

from langdetect import detect, DetectorFactory, LangDetectException

# نتیجه‌ها رو deterministic می‌کنه (وگرنه هر بار ممکنه فرق کنه)
DetectorFactory.seed = 0


LANGUAGE_NAMES = {
    "en": "English",
    "fa": "Persian",
    "nl": "Dutch",
    "de": "German",
    "fr": "French",
    "ar": "Arabic",
}


def detect_language(text: str) -> dict:
    """
    زبان متن رو تشخیص می‌ده.

    برمی‌گردونه: {"code": "en", "name": "English"}
    اگه نتونست تشخیص بده (مثلاً متن خیلی کوتاهه)،
    پیش‌فرض رو انگلیسی در نظر می‌گیره.
    """
    try:
        code = detect(text)
    except LangDetectException:
        code = "en"

    name = LANGUAGE_NAMES.get(code, code)

    return {"code": code, "name": name}