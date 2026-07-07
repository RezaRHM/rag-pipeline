"""
query/synonyms.py
─────────────────────────────────────────────────────────
Domain-specific synonym dictionary برای radio equipment.
این map میکنه زبان کاربر رو به زبان مانوال‌های فنی.
─────────────────────────────────────────────────────────
"""

TECHNICAL_SYNONYMS = {
    "operating temperature": [
        "ambient temperature",
        "temperature range",
        "environmental temperature",
        "installation temperature",
        "operating conditions",
        "environmental conditions",
        "thermal specifications"
    ],
    "power supply": [
        "input voltage",
        "power input",
        "supply voltage",
        "DC input",
        "operating voltage",
        "voltage range"
    ],
    "transmit power": [
        "output power",
        "TX power",
        "RF output",
        "power level",
        "forward power"
    ],
    "dimensions": [
        "size",
        "mechanical dimensions",
        "outline dimensions",
        "form factor"
    ],
    "weight": [
        "net weight",
        "gross weight",
        "unit weight"
    ],
    "alarm": [
        "alarm indicator",
        "alert",
        "error",
        "fault",
        "warning indicator",
        "LED indicator"
    ],
    "error code": [
        "alarm code",
        "fault code",
        "LED display code",
        "seven segment code"
    ],
    "installation requirements": [
        "installation conditions",
        "environmental requirements",
        "site requirements",
        "mounting requirements"
    ],
    "turn off": [
        "power off",
        "shutdown",
        "switch off"
    ],
    "turn on": [
        "power on",
        "startup",
        "switch on"
    ],
    "frequency range": [
        "frequency band",
        "operating frequency",
        "RF frequency"
    ],
    "protection rating": [
        "IP rating",
        "ingress protection",
        "weatherproofing"
    ]
}


def expand_with_synonyms(query: str) -> list:
    """
    سوال رو میگیره و نسخه‌های synonym-expanded رو برمیگردونه.
    فقط اگه یه synonym match شد، نسخه‌های جایگزین رو اضافه میکنه.
    """
    query_lower = query.lower()
    expanded_queries = [query]  # همیشه query اصلی اول

    for term, synonyms in TECHNICAL_SYNONYMS.items():
        if term in query_lower:
            for synonym in synonyms:
                new_query = query_lower.replace(term, synonym)
                if new_query != query_lower:
                    expanded_queries.append(new_query)

        for synonym in synonyms:
            if synonym in query_lower:
                new_query = query_lower.replace(synonym, term)
                if new_query not in expanded_queries:
                    expanded_queries.append(new_query)

    return expanded_queries

PERSIAN_TO_ENGLISH = {
    "چراغ هشدار": "alarm indicator",
    "هشدار": "alarm",
    "چراغ قرمز": "red indicator",
    "قرمز": "red",
    "خطا": "error",
    "کد خطا": "error code",
    "نصب": "installation",
    "دما": "temperature",
    "دمای کاری": "operating temperature",
    "ولتاژ": "voltage",
    "برق": "power supply voltage",
    "آنتن": "antenna",
    "تکرارکننده": "repeater",
    "خاموش": "turn off power off",
    "روشن": "turn on power on",
    "ابزار": "tools",
    "زمین": "ground grounding",
    "فن": "fan cooling",
    "باتری": "battery",
    "فرکانس": "frequency",
    "توان": "power transmit power",
    "محدوده دما": "temperature range",
    "رطوبت": "humidity",
}


def expand_persian_query(question: str) -> list:
    """
    کلمات فارسی رو به معادل انگلیسی‌شون map میکنه.
    هر دو نسخه (فارسی + انگلیسی) رو برمیگردونه.
    """
    queries = [question]
    matched_english = []

    for persian_term, english_equiv in PERSIAN_TO_ENGLISH.items():
        if persian_term in question:
            matched_english.append(english_equiv)

    if matched_english:
        english_query = " ".join(matched_english)
        queries.append(english_query)

        for term in matched_english:
            for eng_key, synonyms in TECHNICAL_SYNONYMS.items():
                if eng_key in term:
                    for syn in synonyms[:2]:
                        if syn not in queries:
                            queries.append(syn)

    return queries