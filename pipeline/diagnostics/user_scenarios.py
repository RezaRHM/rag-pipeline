"""Realistic user scenarios — how an actual support user would ask."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.connection import get_postgres
from main import ask

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

SCENARIOS = [
    # ── تلگرافی / عجول ──
    ("telegraphic", "HR652 power?"),
    ("telegraphic", "RD98XS reset"),
    ("telegraphic", "alarm E3 meaning"),
    ("telegraphic", "how to install RD98XS"),

    # ── محاوره‌ای / طبیعی ──
    ("conversational", "hey, my repeater is beeping and I don't know why"),
    ("conversational", "can you tell me what comes in the box when I buy an RD98XS?"),
    ("conversational", "I just got the HR652, how do I turn it on?"),
    ("conversational", "the red light is flashing on my RD98XS, should I be worried?"),

    # ── مبهم / بدون محصول ──
    ("ambiguous", "how do I install this?"),
    ("ambiguous", "my repeater won't turn on"),
    ("ambiguous", "what does the red light mean?"),
    ("ambiguous", "how do I clean it?"),

    # ── سوال واقعی مشخص ──
    ("specific", "What is the output power of the HR652?"),
    ("specific", "What items come with the RD98XS?"),
    ("specific", "What connectors are on the back of the RD98XS?"),
    ("specific", "Can I use alcohol to clean the HR652?"),

    # ── چیز ناموجود (باید رد کنه) ──
    ("unsupported", "how do I connect the RD98XS to wifi?"),
    ("unsupported", "what's the bluetooth pairing code for the HR652?"),
    ("unsupported", "what is the RD98XS output power in watts?"),
    ("unsupported", "how much does the HR652 weigh?"),

    # ── محصول جعلی ──
    ("fake_product", "what is alarm E5 on the RD99XS?"),
    ("fake_product", "how do I set up the HR999?"),

    # ── خارج از حوزه ──
    ("out_of_scope", "what's the weather today?"),
    ("out_of_scope", "who manufactures these repeaters?"),
    ("out_of_scope", "how much does an RD98XS cost?"),

    # ── مقایسه ──
    ("comparison", "which is better, RD98XS or HR652?"),
    ("comparison", "what's the difference between the two repeaters?"),
    ("comparison", "do both come with the same accessories?"),

    # ── چندبخشی / پیچیده ──
    ("complex", "how do I install the RD98XS and check it's working?"),
    ("complex", "what tools do I need and how do I mount the HR652?"),
]

if __name__ == "__main__":
    print(f"Running {len(SCENARIOS)} scenarios...\n")
    for i, (category, q) in enumerate(SCENARIOS, 1):
        clear()
        t = time.time()
        r = ask(q)
        dt = time.time() - t
        print("═" * 74)
        print(f"[{i}/{len(SCENARIOS)}] {category.upper()}")
        print(f"Q: {q}")
        print(f"[type={r.get('query_type')} | product={r.get('detected_product')} | {dt:.0f}s]")
        print("─" * 74)
        print(r.get("answer", "(no answer)").strip())
        print()
