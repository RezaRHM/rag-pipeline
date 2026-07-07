"""
security/document_scanner.py
─────────────────────────────────────────────────────────
سند رو قبل از index شدن اسکن میکنه —
فایل معتبره؟ محتوای مشکوک داره؟

این یه لایه سبک و سریعه بدون LLM call.
─────────────────────────────────────────────────────────
"""

from pathlib import Path

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE_MB = 50

SUSPICIOUS_PATTERNS = [
    "javascript:",
    "<script",
    "eval(",
    "exec(",
    "base64_decode",
]


def scan_document(file_path: Path, text_content: str = None) -> dict:
    """
    فایل رو اسکن میکنه.

    برمیگردونه:
      safe: True/False
      reason: توضیح اگه unsafe بود
    """
    if not file_path.exists():
        return {"safe": False, "reason": "file_not_found"}

    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return {"safe": False, "reason": f"unsupported_extension: {file_path.suffix}"}

    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return {"safe": False, "reason": f"file_too_large: {size_mb:.1f}MB"}

    if text_content:
        content_lower = text_content.lower()
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern in content_lower:
                return {"safe": False, "reason": f"suspicious_content: {pattern}"}

    return {"safe": True, "reason": None}