import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_postgres
from main import ask

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

CASES = {
    "Q1": ("RD98XS LEDs?",
           lambda a: "timeslot" in a.lower() and "green" in a.lower()),
    "Q8": ("What are the exact steps to install the RD98XS repeater in a rack or cabinet?",
           lambda a: "not explicitly" not in a.lower() and "1." in a),
}

for name, (q, ok) in CASES.items():
    print(f"\n{'='*55}\n{name}: {q[:50]}\n{'='*55}")
    outcomes = []
    for i in range(5):
        clear()
        r = ask(q)
        good = ok(r["answer"])
        outcomes.append(good)
        print(f"  {i+1}. product={r['detected_product']} | "
              f"type={r['query_type']} | outcome={'PASS' if good else 'FAIL/refuse'}")
    print(f"\n  → {sum(outcomes)}/5 passed")
