"""
comparison/schemas.py
─────────────────────────────────────────────────────────
Per-aspect schemas for structured comparison.

Design:
- field-level evidence uses section IDs (E1, E2, ...)
- no booleans for support/absence claims
- specifications are question-aware
- retrieval queries are schema-aware
─────────────────────────────────────────────────────────
"""

ASPECT_KEYWORDS = {
    "features": [
        "dmr feature", "features", "individual call", "group call",
        "broadcast call", "pstn call", "supported functions",
        "supported features", "capabilities", "function list", "feature set",
    ],
    "specifications": [
        "voltage", "power supply", "output power", "frequency",
        "temperature", "weight", "dimension", "specification",
        "spec", "rating", "wattage", "current",
    ],
    "installation": [
        "install", "mounting", "mount", "setup", "set up", "rack",
        "cabinet", "bracket", "screw", "wall", "deploy", "fixing",
    ],
}


def detect_aspect(question: str):
    q = question.lower()
    for aspect in ("features", "specifications", "installation"):
        if any(phrase in q for phrase in ASPECT_KEYWORDS[aspect]):
            return aspect
    return None


INSTALLATION_FIELD_NAMES = [
    "duplexer_procedure",
    "wall_mounting",
    "rack_or_cabinet_mounting",
    "fixing_plate",
    "grounding",
]

FEATURES_FIELD_NAMES = [
    "individual_call",
    "group_call",
    "broadcast_call",
    "pstn_call",
]

SPEC_FIELD_KEYWORDS = {
    "input_voltage": ["voltage", "power supply", "dc power", "current"],
    "output_power": ["output power", "transmit power", "wattage", "watt", "dbm"],
    "frequency": ["frequency", "band", "mhz", "uhf", "vhf"],
    "temperature": ["temperature", "thermal", "ambient", "operating condition"],
    "weight": ["weight", "mass", "kg"],
    "dimensions": ["dimension", "size", "height", "width", "depth"],
}


def relevant_spec_fields(question: str) -> list:
    q = question.lower()
    selected = [
        field
        for field, keywords in SPEC_FIELD_KEYWORDS.items()
        if any(keyword in q for keyword in keywords)
    ]
    return selected if selected else list(SPEC_FIELD_KEYWORDS.keys())


STATUS_TRISTATE = {"documented", "not_documented", "unclear"}
STATUS_FEATURES = {"confirmed", "not_documented", "unclear"}
STATUS_SPEC = {"documented", "not_documented", "unclear"}


def build_schema_prompt_spec(aspect: str, question: str) -> str:
    """
    Return a JSON-valid field specification to embed in the extractor prompt.
    supporting_quote is optional/best-effort; validator can use deterministic
    lexical checks when it is absent.
    """
    if aspect == "installation":
        fields_desc = ",\n".join([
            (
                f'    "{name}": {{'
                '"status": "documented | not_documented | unclear", '
                '"evidence": ["E1"], '
                '"supporting_quote": "exact sentence from cited evidence, or null"'
                "}"
            )
            for name in INSTALLATION_FIELD_NAMES
        ])

        fields_desc += (
            ',\n    "cover_or_housing_removed": {'
            '"value": "exact term e.g. \'top cover\' or \'rear housing\', or null", '
            '"status": "documented | not_documented | unclear", '
            '"evidence": ["E1"], '
            '"supporting_quote": "exact sentence or null"'
            "}"
        )

        fields_desc += (
            ',\n    "fasteners": {'
            '"items": ["ONLY fastening hardware explicitly named, e.g. '
            '\'M4 screws\', \'M6 expansion bolts\', \'pegs\', \'nuts\', '
            '\'washers\', \'anchors\'"], '
            '"status": "documented | not_documented | unclear", '
            '"evidence": ["E1"], '
            '"supporting_quote": "exact sentence or null"'
            "}"
        )
        
        

        return fields_desc

    if aspect == "features":
        return ",\n".join([
            (
                f'    "{name}": {{'
                '"status": "confirmed | not_documented | unclear", '
                '"evidence": ["E1"], '
                '"supporting_quote": "exact sentence from cited evidence, or null"'
                "}"
            )
            for name in FEATURES_FIELD_NAMES
        ])

    if aspect == "specifications":
        fields = relevant_spec_fields(question)

        return ",\n".join([
            (
                f'    "{name}": {{'
                '"value": "exact value/range or null", '
                '"source_term": "EXACT term from document, do not paraphrase", '
                '"status": "documented | not_documented | unclear", '
                '"evidence": ["E1"], '
                '"supporting_quote": "exact sentence or null"'
                "}"
            )
            for name in fields
        ])

    return ""


def expected_field_names(aspect: str, question: str) -> list:
    if aspect == "installation":
        return INSTALLATION_FIELD_NAMES + [
            "cover_or_housing_removed",
            "fasteners",
        ]

    if aspect == "features":
        return FEATURES_FIELD_NAMES

    if aspect == "specifications":
        return relevant_spec_fields(question)

    return []


# ── Schema-aware retrieval queries ───────────────────────

ASPECT_RETRIEVAL_QUERIES = {
    "installation": [
        "installation procedure steps",
        "duplexer installation",
        "wall mounting fixing plate bracket",
        "rack or cabinet mounting",
        "rear housing cover removal",
        "grounding screw",
        "fasteners screws bolts",
    ],
    "features": [
        "individual call group call",
        "broadcast call PSTN call",
        "DMR digital features supported functions",
    ],
}


SPEC_RETRIEVAL_BY_FIELD = {
    "input_voltage": "input voltage power supply DC",
    "output_power": "output power transmit power dBm",
    "frequency": "frequency band range MHz",
    "temperature": "operating temperature ambient",
    "weight": "weight mass",
    "dimensions": "dimensions size height width",
}


def get_retrieval_queries(aspect: str, question: str = "") -> list:
    """
    Return targeted retrieval queries.

    Specifications are question-aware: only fields relevant to the question
    generate retrieval queries. Installation/features use a fixed query set.
    """
    if aspect == "specifications":
        fields = relevant_spec_fields(question)

        return [
            SPEC_RETRIEVAL_BY_FIELD[field]
            for field in fields
            if field in SPEC_RETRIEVAL_BY_FIELD
        ]

    return ASPECT_RETRIEVAL_QUERIES.get(aspect, [])