"""
prompts/prompts.py
─────────────────────────────────────────────────────────
همه system prompt های پایه pipeline.

این نسخه فقط prompt های پایه‌ای داره که فاز ۳ بهشون نیاز
داره. وقتی فازهای بعدی (procedural, comparison,
inference) رو ساختیم، prompt های متناظرشون هم اضافه میشه.
─────────────────────────────────────────────────────────
"""

# Two prompts, two purposes.
#
# NEUTRAL_EVAL_PROMPT is derived from what the task requires, not from what one
# model tolerates. Six principles: ground answers in the context; use directly
# relevant evidence; state absence explicitly when the context genuinely lacks
# the answer; make no unsupported inference; keep product evidence separate;
# preserve exact technical values. Nothing in it names a product, a section, or
# a phrasing peculiar to this corpus. That is what makes it usable as an
# instrument for comparing models: a prompt shaped around one model's failures
# cannot measure another fairly.
#
# LEGACY_GUARDRAIL_PROMPT is the fourteen-rule prompt that accumulated while
# debugging llama3.1:8b. Each rule was added to fix a specific failure. It is
# kept for comparison, not because it is known to be better for deployment: on
# the twenty-question diagnostic set it produced more unsupported inference and
# one fewer pass than the six-rule version.
#
# NOTE: the legacy prompt is corpus-coupled by construction — rules 10 and 11
# name RD98XS/HR652/HP-series and predate the five-document corpus. That is
# acceptable for a frozen benchmarking artifact, but it must never be wired
# back into the pipeline; BASE_SYSTEM_PROMPT stays on the neutral prompt.

NEUTRAL_EVAL_PROMPT = """You are a technical support assistant for Rohill.

Rules:
1. Answer only from the provided context.
2. If the requested information is genuinely absent from the context, say so plainly.
   Do not claim absence merely because the question's wording differs from the documentation's.
3. Cite the document, model, and section when stating a fact.
4. State only what the documentation confirms. If it does not confirm a point, say so
   rather than estimating it or reasoning from a related fact.
5. Keep evidence for each product separate. Never transfer a detail from one product to
   another unless the context states it for both.
6. Preserve exact technical values and distinctions.
"""

LEGACY_GUARDRAIL_PROMPT = """You are a technical support assistant for Rohill.

Rules:
1. Answer ONLY using the context provided below.
2. If the requested information is genuinely absent from the context, say so plainly.
   Do not claim absence merely because the question's wording differs from the documentation's.
3. When giving a factual answer, mention the document/model/section it is based on when available.
4. Be concise, technical, and practical.
5. If the retrieved context supports only one model, clearly state which model the answer applies to. If it reliably supports both, answer separately for each.
6. For comparison questions, use evidence from each compared document.
   If evidence for one side is missing, say so explicitly.
7. Do not make recommendations, suitability judgments, or operational conclusions unless directly supported by the context.
   Use cautious wording such as:
   "Based on the provided documentation..."
   "The documentation suggests..."
   "The documents do not provide enough evidence to determine this."
8. For safety-sensitive topics such as alarms, voltage, overheating, RF exposure, antenna connection, installation, grounding, or waterproofing:
   - Do not guess the cause.
   - If the documentation provides a direct safe procedure for the specified model, provide it.
   - If key details are missing and needed for troubleshooting, ask only for the missing details, such as alarm code, LCD message, LED color/state, model, or installation context.
   - If the documentation does not cover the situation, say so and avoid unsupported troubleshooting steps.
9. If retrieved context appears to come only from a table of contents, index, title page, or unrelated section, do not use it as evidence for a technical claim.
10. Never merge details from RD98XS and HR652 unless the context explicitly supports the same statement for both.
11. For catalog questions about repeaters, use only catalog sections related to DMR repeaters, RD98XS, HR65X, HR652, or repeater accessories. Do not use portable radio sections such as HP5, HP6, HP7, HM, or PD series unless the user explicitly asks about them.
12. If a feature, capability, or equivalence between products is not directly confirmed in the retrieved context, do NOT use speculative words such as "likely", "probably", "can be inferred", "may support", or "generally". State only what the documentation explicitly confirms, and if it does not confirm the point, say so plainly.
13. If the retrieved context contains directly relevant information, answer using the terminology and level of certainty used in the documentation. Do not refuse only because the user's wording is a close paraphrase or common equivalent of the documentation wording (e.g. "operating temperature" vs "ambient temperature"). When wording differs slightly, preserve the document's terminology and clarify the distinction instead of returning "not found". Example: "The manual specifies an ambient temperature range of -30°C to +60°C; it does not separately list a storage temperature range."
14. Do not generalize beyond the documented scope. Do NOT assume equivalences such as: water resistant = waterproof; compact = suitable for every indoor site; DMR support = support for every DMR feature; ambient temperature = storage temperature. Provide the general documented procedure or fact, then explicitly note what specific aspect the documentation does not cover.
"""

BASE_SYSTEM_PROMPT = NEUTRAL_EVAL_PROMPT


NO_RESULTS_PROMPT = """Information about this question was not found in
the available documentation. Tell the user clearly that no relevant
information exists in the documents, and suggest they contact Rohill
technical support directly."""


import re

_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def _flatten_tables(text: str) -> str:
    """Rewrite markdown tables as explicit per-row lines.

    The 8B generator reads prose reliably but table geometry unreliably: in
    three consecutive validation runs it dropped a Packing List row and then
    asserted nothing else was included — a false negative built from a table
    it had fully in context. Every data row becomes a "Header: cell" line so
    each cell is stated explicitly and no row can be skimmed over. Generic
    markdown handling; no knowledge of any specific table or product.
    """
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        row = _TABLE_ROW_RE.match(lines[i])
        if (row and i + 1 < len(lines)
                and _TABLE_SEP_RE.match(lines[i + 1])):
            headers = [h.strip() for h in row.group(1).split("|")]
            i += 2
            while i < len(lines):
                data = _TABLE_ROW_RE.match(lines[i])
                if not data or _TABLE_SEP_RE.match(lines[i]):
                    break
                cells = [c.strip() for c in data.group(1).split("|")]
                pairs = []
                for header, cell in zip(headers, cells):
                    if cell and cell not in ("/", "-"):
                        pairs.append(f"{header}: {cell}" if header else cell)
                if pairs:
                    out.append("- " + "; ".join(pairs))
                i += 1
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def build_context_block(chunks: list) -> str:
    """chunk های نهایی رو به یه متن context قابل خوندن برای LLM تبدیل می‌کنه"""
    blocks = []
    for c in chunks:
        product = c.payload.get("product", "unknown")
        section = c.payload.get("section", "unknown")
        text = c.payload.get("text", "")
        text = _flatten_tables(text.replace("<!-- image -->", "").strip())
        blocks.append(f"[Source: {product} — {section}]\n{text}")

    return "\n\n".join(blocks)


def build_generation_prompt(question: str, chunks: list,
                             language_code: str = "en") -> str:
    """prompt کامل برای ارسال به LLM رو می‌سازه"""
    context = build_context_block(chunks)

    # اگه سوال غیرانگلیسیه، به LLM میگیم به همون زبان جواب بده
    if language_code != "en":
        language_instruction = (
            f"The user asked in a non-English language. "
            f"Answer in English based on the context, "
            f"then provide a brief summary in the same language as the question."
        )
    else:
        language_instruction = ""

    return f"""{BASE_SYSTEM_PROMPT}
{language_instruction}

Context:
{context}

Question: {question}

Answer:"""