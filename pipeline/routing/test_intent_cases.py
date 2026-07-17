"""Router intent test cases — the behavioral spec for the intent classifier.

Each case: (question, expected_intent). Independent of RAG (no retrieval, no
generation). Includes hard cases: typos, ambiguous boundaries, and traps
(words like "difference"/"two" that do NOT imply product comparison).

Intents: standard, procedural, comparison, troubleshooting.
"""

INTENT_CASES = [
    # ── procedural: how-to, no symptom ──
    ("how do I install the RD98XS", "procedural"),
    ("how do I mount the HR652 on a wall", "procedural"),
    ("how do I turn on the HR652", "procedural"),
    ("how do I clean the repeater", "procedural"),
    ("steps to install the RD98XS", "procedural"),
    ("how do I replace the duplexer", "procedural"),
    ("how do I install it and verify it works", "procedural"),  # multi-part

    # ── troubleshooting: symptom/problem present ──
    ("what does alarm E3 mean", "troubleshooting"),
    ("the red light is flashing, should I worry", "troubleshooting"),
    ("my repeater won't turn on", "troubleshooting"),
    ("the repeater keeps beeping", "troubleshooting"),
    ("there is no transmission", "troubleshooting"),
    ("poor coverage on the HR652", "troubleshooting"),
    ("fan failure alarm on RD98XS", "troubleshooting"),
    ("what should I check for alarm E3", "troubleshooting"),
    ("why is the alarm indicator red", "troubleshooting"),
    ("HR652 won't turn on", "troubleshooting"),  # boundary vs procedural

    # ── comparison: compare two/multiple products ──
    ("compare RD98XS and HR652", "comparison"),
    ("RD98XS vs HR652", "comparison"),
    ("what is the difference between RD98XS and HR652", "comparison"),
    ("how do the two repeaters differ", "comparison"),
    ("which one is better, RD98XS or HR652", "comparison"),
    ("do both come with the same accessories", "comparison"),
    ("compare the cleaning instructions", "comparison"),
    ("compare alarm codes of RD98XS and HR652", "comparison"),
    ("which repeater should I choose", "comparison"),
    ("compair RD98XS and HR652", "comparison"),          # typo
    ("diffrence between the repeaters", "comparison"),    # typo

    # ── standard: factual QA, capability, existence, yes/no ──
    ("what is the output power of the HR652", "standard"),
    ("what items come with the RD98XS", "standard"),
    ("what connectors are on the back of the RD98XS", "standard"),
    ("can I use alcohol to clean the HR652", "standard"),   # yes/no
    ("is the RD98XS waterproof", "standard"),               # capability
    ("does the HR652 have wifi", "standard"),               # existence
    ("what is the operating voltage", "standard"),
    ("who manufactures these repeaters", "standard"),

    # ── TRAPS: look like one intent, are another ──
    # "difference" but single-product, not a product comparison:
    ("what is the difference between high and low power on the HR652", "standard"),
    # "two" but not a comparison:
    ("what are the two antenna connectors on the RD98XS", "standard"),
    # "both" referring to timeslots, not products:
    ("do both timeslots transmit at once", "standard"),
]
