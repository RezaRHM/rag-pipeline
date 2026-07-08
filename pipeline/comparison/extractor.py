"""
comparison/extractor.py
─────────────────────────────────────────────────────────
Structured extraction for one product using only that product's context.

Flow:
LLM → robust JSON parse → hybrid evidence validation → envelope or None.

Hybrid validation:
- exact supporting_quote is strong evidence when present
- quote is optional
- directly verifiable values/items are checked lexically against cited chunks
- semantic fields use deterministic field-specific lexical anchors
- unsupported documented/confirmed claims are demoted to unclear
- no retry; parse failure returns None for free-form fallback
─────────────────────────────────────────────────────────
"""

import json
import re
from typing import Dict, List, Optional

import requests

import config
from comparison.schemas import (
    STATUS_FEATURES,
    STATUS_SPEC,
    STATUS_TRISTATE,
    build_schema_prompt_spec,
    expected_field_names,
)


SEMANTIC_ANCHORS = {
    "duplexer_procedure": [
        ("install", "duplexer"),
        ("secure", "duplexer"),
        ("mount", "duplexer"),
    ],
    "wall_mounting": [
        ("install", "wall"),
        ("mount", "wall"),
        ("bracket", "wall"),
    ],
    "rack_or_cabinet_mounting": [
        ("rack",),
        ("cabinet",),
    ],
    "fixing_plate": [
        ("fixing plate",),
    ],
    "grounding": [
        ("ground screw",),
        ("grounding",),
        ("ground",),
    ],
    "individual_call": [
        ("individual call",),
    ],
    "group_call": [
        ("group call",),
    ],
    "broadcast_call": [
        ("broadcast call",),
    ],
    "pstn_call": [
        ("pstn call",),
        ("pstn",),
    ],
}

FASTENER_TERMS = (
    "screw",
    "bolt",
    "nut",
    "washer",
    "anchor",
    "peg",
    "stud",
    "rivet",
)

TOOL_TERMS = (
    "screwdriver",
    "spanner",
    "wrench",
    "drill",
    "pliers",
    "hammer",
    "driver",
)
def _is_fastener_item(item: str) -> bool:
    """
    Keep fastening hardware only.
    Reject tools such as screwdrivers, spanners, drills, and wrenches.
    """
    if not isinstance(item, str):
        return False

    text = item.strip().lower()

    if not text:
        return False

    if any(tool in text for tool in TOOL_TERMS):
        return False

    return any(term in text for term in FASTENER_TERMS)

def _extract_json(raw: str) -> Optional[dict]:
    """Extract nested JSON safely, without regex matching balanced braces."""
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, TypeError):
        pass

    cleaned = re.sub(
        r"```(?:json)?",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip()

    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, TypeError):
        pass

    decoder = json.JSONDecoder()
    idx = cleaned.find("{")

    if idx != -1:
        try:
            obj, _ = decoder.raw_decode(cleaned[idx:])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            pass

    return None


def _normalize_quote_text(text: str) -> str:
    """Normalize whitespace only, preserving lexical content."""
    if not isinstance(text, str):
        return ""

    return " ".join(text.split()).lower()


def _normalize_lexical(text: str) -> str:
    """
    Normalize formatting noise for deterministic lexical checks.

    Example:
      M 2.5 x 5
      M2.5x5

    both normalize to comparable alphanumeric sequences.
    """
    if not isinstance(text, str):
        return ""

    return re.sub(
        r"[^a-z0-9]+",
        "",
        text.lower(),
    )


def _normalize_status(value, allowed: set) -> str:
    if not isinstance(value, str):
        return "unclear"

    normalized = value.strip().lower()

    return (
        normalized
        if normalized in allowed
        else "unclear"
    )


def _valid_evidence(
    evidence,
    allowed_ids: set,
) -> List[str]:
    """Keep only exact, valid section IDs."""
    if not isinstance(evidence, list):
        return []

    valid = []
    seen = set()

    for item in evidence:
        if not isinstance(item, str):
            continue

        eid = item.strip().upper()

        if eid in allowed_ids and eid not in seen:
            valid.append(eid)
            seen.add(eid)

    return valid


def _cited_texts(
    evidence_ids: List[str],
    text_by_id: Dict[str, str],
) -> List[str]:
    return [
        text_by_id[eid]
        for eid in evidence_ids
        if (
            eid in text_by_id
            and isinstance(text_by_id[eid], str)
        )
    ]


def _quote_supports(
    quote,
    evidence_ids: List[str],
    text_by_id: Dict[str, str],
) -> bool:
    """
    Quote must be a normalized exact substring of at least one cited chunk.

    Very short quotes are rejected because they are weak provenance.
    """
    if not isinstance(quote, str) or not quote.strip():
        return False

    q_norm = _normalize_quote_text(quote)

    if len(q_norm) < 10:
        return False

    return any(
        q_norm in _normalize_quote_text(text)
        for text in _cited_texts(
            evidence_ids,
            text_by_id,
        )
    )


def _value_supports(
    value,
    evidence_ids: List[str],
    text_by_id: Dict[str, str],
) -> bool:
    """
    Deterministic lexical verification for values/items.

    This intentionally does not perform semantic similarity or fuzzy matching.
    """
    if not isinstance(value, str) or not value.strip():
        return False

    value_norm = _normalize_lexical(value)

    if not value_norm:
        return False

    return any(
        value_norm in _normalize_lexical(text)
        for text in _cited_texts(
            evidence_ids,
            text_by_id,
        )
    )


def _anchors_support(
    field_name: str,
    evidence_ids: List[str],
    text_by_id: Dict[str, str],
) -> bool:
    """
    Verify semantic fields with deterministic lexical anchor groups.

    All terms in one anchor group must occur in the same cited chunk.
    This avoids combining unrelated terms across separate evidence chunks.
    """
    anchor_groups = SEMANTIC_ANCHORS.get(
        field_name,
        [],
    )

    if not anchor_groups:
        return False

    cited = [
        text.lower()
        for text in _cited_texts(
            evidence_ids,
            text_by_id,
        )
    ]

    for text in cited:
        for group in anchor_groups:
            if all(
                term.lower() in text
                for term in group
            ):
                return True

    return False


def _clean_optional_quote(
    quote,
    evidence_ids: List[str],
    text_by_id: Dict[str, str],
):
    """
    Preserve a quote only when it validates exactly.

    Invalid/missing quotes do not automatically demote a field because
    lexical/anchor verification may still support the claim.
    """
    if _quote_supports(
        quote,
        evidence_ids,
        text_by_id,
    ):
        return quote.strip()

    return None


def _resolve_evidence_ids(
    envelope: dict,
    section_by_id: dict,
) -> None:
    """Resolve validated E1/E2 IDs to human-readable section names."""
    for field in envelope.get("fields", {}).values():
        if isinstance(field, dict) and "evidence" in field:
            field["evidence"] = [
                section_by_id.get(eid, eid)
                for eid in field["evidence"]
            ]


def _validate(
    parsed: dict,
    aspect: str,
    question: str,
    product: str,
    allowed_ids: set,
    text_by_id: Dict[str, str],
) -> Optional[dict]:
    """
    Validate envelope and fields.

    Rules:
    - missing field → unclear
    - unknown extra fields are dropped
    - documented/confirmed claims require evidence plus either:
      exact quote, lexical value support, or field-specific anchors
    - not_documented never becomes a claim that the product lacks something
    """
    if not isinstance(parsed, dict):
        return None

    fields_in = parsed.get("fields")

    if not isinstance(fields_in, dict):
        return None

    expected = expected_field_names(
        aspect,
        question,
    )

    clean_fields = {}

    for name in expected:
        raw_field = fields_in.get(name)
        missing = not isinstance(raw_field, dict)

        # ── fasteners ─────────────────────────────────────
        if name == "fasteners":
            if missing:
                clean_fields[name] = {
                    "items": [],
                    "status": "unclear",
                    "evidence": [],
                    "supporting_quote": None,
                }
                continue

            status = _normalize_status(
                raw_field.get("status"),
                STATUS_TRISTATE,
            )

            evidence = _valid_evidence(
                raw_field.get("evidence"),
                allowed_ids,
            )

            quote = _clean_optional_quote(
                raw_field.get("supporting_quote"),
                evidence,
                text_by_id,
            )

            raw_items = raw_field.get("items", [])

            items = (
                [
                    str(item).strip()
                    for item in raw_items
                    if str(item).strip()
                ]
                if isinstance(raw_items, list)
                else []
            )

            verified_items = [
                item
                for item in items
                if (
                    _is_fastener_item(item)
                    and _value_supports(
                        item,
                        evidence,
                        text_by_id,
                    )
                )
            ]

            if status == "not_documented":
                verified_items = []
                quote = None

            elif status == "documented":
                if not evidence or not verified_items:
                    status = "unclear"
                    verified_items = []
                    quote = None

            clean_fields[name] = {
                "items": verified_items,
                "status": status,
                "evidence": evidence,
                "supporting_quote": quote,
            }

            continue

        # ── cover / housing ───────────────────────────────
        if name == "cover_or_housing_removed":
            if missing:
                clean_fields[name] = {
                    "value": None,
                    "status": "unclear",
                    "evidence": [],
                    "supporting_quote": None,
                }
                continue

            status = _normalize_status(
                raw_field.get("status"),
                STATUS_SPEC,
            )

            evidence = _valid_evidence(
                raw_field.get("evidence"),
                allowed_ids,
            )

            quote = _clean_optional_quote(
                raw_field.get("supporting_quote"),
                evidence,
                text_by_id,
            )

            value = raw_field.get("value")

            value = (
                value.strip()
                if (
                    isinstance(value, str)
                    and value.strip()
                )
                else None
            )

            if status == "not_documented":
                value = None
                quote = None

            elif status == "documented":
                supported = (
                    bool(evidence)
                    and (
                        quote is not None
                        or _value_supports(
                            value,
                            evidence,
                            text_by_id,
                        )
                    )
                )

                if not supported:
                    status = "unclear"
                    value = None
                    quote = None

            clean_fields[name] = {
                "value": value,
                "status": status,
                "evidence": evidence,
                "supporting_quote": quote,
            }

            continue

        # ── specifications ────────────────────────────────
        if aspect == "specifications":
            if missing:
                clean_fields[name] = {
                    "value": None,
                    "source_term": None,
                    "status": "unclear",
                    "evidence": [],
                    "supporting_quote": None,
                }
                continue

            status = _normalize_status(
                raw_field.get("status"),
                STATUS_SPEC,
            )

            evidence = _valid_evidence(
                raw_field.get("evidence"),
                allowed_ids,
            )

            quote = _clean_optional_quote(
                raw_field.get("supporting_quote"),
                evidence,
                text_by_id,
            )

            value = raw_field.get("value")

            value = (
                value.strip()
                if (
                    isinstance(value, str)
                    and value.strip()
                )
                else None
            )

            source_term = raw_field.get("source_term")

            source_term = (
                source_term.strip()
                if (
                    isinstance(source_term, str)
                    and source_term.strip()
                )
                else None
            )

            if status == "not_documented":
                value = None
                source_term = None
                quote = None

            elif status == "documented":
                supported = (
                    bool(evidence)
                    and (
                        quote is not None
                        or _value_supports(
                            value,
                            evidence,
                            text_by_id,
                        )
                    )
                )

                if not supported:
                    status = "unclear"
                    value = None
                    source_term = None
                    quote = None

                elif (
                    source_term
                    and not _value_supports(
                        source_term,
                        evidence,
                        text_by_id,
                    )
                ):
                    source_term = None

            clean_fields[name] = {
                "value": value,
                "source_term": source_term,
                "status": status,
                "evidence": evidence,
                "supporting_quote": quote,
            }

            continue

        # ── installation / features semantic fields ───────
        allowed_status = (
            STATUS_FEATURES
            if aspect == "features"
            else STATUS_TRISTATE
        )

        if missing:
            clean_fields[name] = {
                "status": "unclear",
                "evidence": [],
                "supporting_quote": None,
            }
            continue

        status = _normalize_status(
            raw_field.get("status"),
            allowed_status,
        )

        evidence = _valid_evidence(
            raw_field.get("evidence"),
            allowed_ids,
        )

        quote = _clean_optional_quote(
            raw_field.get("supporting_quote"),
            evidence,
            text_by_id,
        )

        if status in ("documented", "confirmed"):
            supported = (
                bool(evidence)
                and (
                    quote is not None
                    or _anchors_support(
                        name,
                        evidence,
                        text_by_id,
                    )
                )
            )

            if not supported:
                status = "unclear"
                quote = None

        elif status == "not_documented":
            quote = None

        else:
            quote = None

        clean_fields[name] = {
            "status": status,
            "evidence": evidence,
            "supporting_quote": quote,
        }

    return {
        "product": product,
        "aspect": aspect,
        "fields": clean_fields,
    }


def extract_structured(
    product: str,
    aspect: str,
    question: str,
    chunks: list,
) -> Optional[dict]:
    """Extract one structured envelope from one product's context."""
    if not chunks:
        return None

    section_by_id = {}
    text_by_id = {}
    context_parts = []

    for i, chunk in enumerate(chunks, 1):
        eid = f"E{i}"
        section = chunk.payload.get("section", "")
        text = chunk.payload.get("text", "")

        section_by_id[eid] = section
        text_by_id[eid] = text

        context_parts.append(
            f"[{eid}] Section: {section}\n{text}"
        )

    context = "\n\n".join(context_parts)

    allowed_ids = set(
        section_by_id.keys()
    )

    schema_desc = build_schema_prompt_spec(
        aspect,
        question,
    )

    prompt = f"""You are extracting structured data about {product} for a technical comparison.

Extract ONLY from the context below. Output STRICT JSON, no other text.

Rules:
- Use ONLY information explicitly present in the context for {product}.
- Read the FULL BODY TEXT, not only section headings. Relevant details may appear inside a broadly named section.
- "evidence" must contain only section IDs shown in brackets, e.g. ["E1"] or ["E1", "E2"]. Never invent an ID.
- Use "not_documented" only when the retrieved context lacks the information. This does NOT mean the product lacks the capability.
- Use "unclear" when the context is ambiguous.
- Never guess "supported" or "unsupported".
- Any "documented" or "confirmed" status must cite valid evidence IDs.
- "supporting_quote" is best-effort: when possible, copy an exact supporting sentence from the cited evidence. If you cannot provide one reliably, use null.
- For specs, preserve the exact document terminology in "source_term". Do not convert or paraphrase terms.
- Do not paraphrase specification values; copy them as written.

Output this exact JSON structure:
{{
  "product": "{product}",
  "aspect": "{aspect}",
  "fields": {{
{schema_desc}
  }}
}}

Context:
{context}

JSON:"""

    try:
        response = requests.post(
            f"{config.LITELLM_BASE_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": (
                    f"Bearer {config.LITELLM_API_KEY}"
                ),
            },
            json={
                "model": config.DEFAULT_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "temperature": 0,
            },
            timeout=config.LLM_TIMEOUT,
        )

        response.raise_for_status()

        raw = (
            response
            .json()["choices"][0]["message"]["content"]
        )

    except Exception:
        return None

    parsed = _extract_json(raw)

    if parsed is None:
        return None

    validated = _validate(
        parsed,
        aspect,
        question,
        product,
        allowed_ids,
        text_by_id,
    )

    if validated:
        _resolve_evidence_ids(
            validated,
            section_by_id,
        )

    return validated