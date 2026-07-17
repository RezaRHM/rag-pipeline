"""Deterministic text normalization for the intent classifier."""

import re
import unicodedata


# Product-like identifiers such as RD98XS, HR652, AX500, or NX400.
# Requiring at least two digits avoids treating short alarm codes (E3) as
# products. The expression is deliberately corpus-independent.
MODEL_TOKEN_RE = re.compile(
    r"\b[A-Za-z]{1,5}\d{2,4}[A-Za-z]{0,3}\b",
    re.IGNORECASE,
)
ALARM_CODE_RE = re.compile(
    r"\b(alarm|error|warning)\s+(?:code\s+)?([A-Za-z]{1,2}\d{1,3})\b",
    re.IGNORECASE,
)
# Model-shaped tokens that are actually technical standards / specifications,
# not product identifiers. Grouped by family so a new member extends its family
# instead of needing a new bespoke pattern:
#   IEC 60529 ingress protection : IP68, IP54, IPX4, IP6X
#   USB generations              : USB2, USB3
#   Ethernet cable categories    : CAT5, CAT6, CAT6A
#   AES key sizes                : AES128, AES256 (hyphenated "AES-256" does not
#                                  collide with MODEL_TOKEN_RE anyway)
#   Radio band shorthands        : UHF400, VHF150
# This list is small, universal and CORPUS-INDEPENDENT: it depends on technical
# standards, never on the product catalogue, so adding a product needs no edit
# here. Without it, e.g. IP68 in "Is the RD98XS IP68 rated?" matches
# MODEL_TOKEN_RE, looks like a second product, and falsely fires
# cue_multiple_models -> the query is misrouted as a comparison.
TECHNICAL_STANDARD_RE = re.compile(
    r"\b(?:"
    r"IP[0-9X]{2}"        # ingress protection
    r"|USB\d"             # USB generation
    r"|CAT\d[A-Z]?"       # ethernet cable category
    r"|AES\d{2,3}"        # AES key size
    r"|[UV]HF\d{2,4}"     # radio band shorthand
    r")\b",
    re.IGNORECASE,
)


def is_technical_token(token: str) -> bool:
    """True if the token is a known technical standard, not a product model.

    Shared negative signal: the intent normalizer uses it so such tokens are
    not counted as products, and the unknown-product gate uses it so they are
    never flagged as undocumented products.
    """
    return bool(TECHNICAL_STANDARD_RE.fullmatch(token.strip()))

COMPARISON_RE = re.compile(
    r"\b(compare|comparison|versus|vs|contrast|differ(?:ence|ences|ent)?|"
    r"side by side|against|better|preferable|superior|equivalent|identical|"
    r"same|both|each|pair|one .{0,30} other|first .{0,30} second)\b",
    re.IGNORECASE,
)
PROCEDURAL_RE = re.compile(
    r"\b(how (?:do|can|should|to)|steps?|procedure|process|instructions?|"
    r"guide|method|sequence|walk me through|show me how|setup|set up)\b",
    re.IGNORECASE,
)
TROUBLE_RE = re.compile(
    r"\b(alarm|error|fault|warning|fail(?:s|ed|ure|ing)?|won't|wont|cannot|"
    r"not detected|not recognized|no response|no sound|no audio|no signal|"
    r"stuck|frozen|overheat(?:s|ing)?|too hot|keeps|repeated|drops?|"
    r"disconnects?|corrupt(?:ed)?|refuses?|stopped|blinking|flashing)\b",
    re.IGNORECASE,
)
FACTUAL_RE = re.compile(
    r"^(what (?:is|are|does)|how (?:many|much)|does|is|can|who|which company|"
    r"list|name|state|identify|give|provide)\b",
    re.IGNORECASE,
)


def normalize_intent_text(text: str) -> str:
    """Abstract product identifiers while preserving intent-bearing syntax."""
    # Mask explicit alarm/error codes before counting product-shaped tokens.
    # Without this, E47 in "alarm E47 on RD99XS" looks like a second product
    # and creates a false comparison cue.
    text = ALARM_CODE_RE.sub(r"\1 ALARMCODE", text)
    text = TECHNICAL_STANDARD_RE.sub("TECHSTD", text)
    model_count = len(MODEL_TOKEN_RE.findall(text))
    cues = []
    if model_count == 1:
        cues.append("cue_one_model")
    elif model_count >= 2:
        cues.append("cue_multiple_models")
    if COMPARISON_RE.search(text):
        cues.append("cue_comparison_relation")
    if PROCEDURAL_RE.search(text):
        cues.append("cue_procedure_request")
    if TROUBLE_RE.search(text):
        cues.append("cue_fault_state")
    if FACTUAL_RE.search(text.strip()):
        cues.append("cue_factual_request")

    text = MODEL_TOKEN_RE.sub("MODEL", text)
    text = unicodedata.normalize("NFKD", text)
    normalized = "".join(
        c for c in text if not unicodedata.combining(c)
    ).lower()
    return " ".join([normalized, *cues])
