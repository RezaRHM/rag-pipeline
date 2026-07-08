"""
language/language_detector.py
─────────────────────────────────────────────────────────
تشخیص زبان سوال کاربر — برای اینکه بدونیم:
  ۱. LLM باید به چه زبانی جواب بده
  ۲. آیا نیاز به query expansion داریم

نکته: langdetect برای متن‌های کوتاه غیرقابل‌اعتماده
(مثلاً "Power issue" رو آلمانی تشخیص می‌ده). پس اول
یه محافظ ASCII می‌ذاریم: اگه متن اکثراً ASCII بود،
قطعاً انگلیسیه.
─────────────────────────────────────────────────────────
"""

from langdetect import detect, DetectorFactory, LangDetectException

DetectorFactory.seed = 0


LANGUAGE_NAMES = {
    "en": "English",
    "fa": "Persian",
    "nl": "Dutch",
    "de": "German",
    "fr": "French",
    "ar": "Arabic",
}

# زبان‌هایی که واقعاً پشتیبانی می‌کنیم و corpus/کاربرها ممکنه استفاده کنن
# langdetect خیلی زبان‌های دیگه هم برمی‌گردونه که برای ما نویز هستن
SUPPORTED_CODES = {"en", "fa", "nl", "de", "fr", "ar"}


def _ascii_ratio(text: str) -> float:
    """نسبت کاراکترهای ASCII به کل (بدون فاصله)."""
    stripped = [c for c in text if not c.isspace()]
    if not stripped:
        return 1.0
    ascii_count = sum(1 for c in stripped if ord(c) < 128)
    return ascii_count / len(stripped)


def detect_language(text: str) -> dict:
    """
    زبان متن رو تشخیص می‌ده.

    منطق:
      ۱. اگه متن اکثراً ASCII ـه (>90%) → انگلیسی
         (زبان‌های غیرلاتین مثل فارسی/عربی کاراکتر non-ASCII دارن)
      ۲. وگرنه langdetect رو امتحان کن
      ۳. اگه langdetect یه زبان پشتیبانی‌نشده داد، به انگلیسی fallback کن
    """
    # محافظ ۱: متن اکثراً ASCII → انگلیسی
    # این باگ سوالات کوتاه انگلیسی رو حل می‌کنه
    if _ascii_ratio(text) > 0.9:
        return {"code": "en", "name": "English"}

    # محافظ ۲: langdetect برای متن غیر-ASCII
    try:
        code = detect(text)
    except LangDetectException:
        return {"code": "en", "name": "English"}

    # محافظ ۳: فقط زبان‌های پشتیبانی‌شده؛ بقیه → انگلیسی
    if code not in SUPPORTED_CODES:
        return {"code": "en", "name": "English"}

    name = LANGUAGE_NAMES.get(code, code)
    return {"code": code, "name": name}