import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hashlib
from db.connection import get_postgres
from main import ask

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

CASES = {
    "Q1":  ("RD98XS LEDs?",
            lambda a: "timeslot" in a.lower() and "green" in a.lower()),
    "Q8":  ("What are the exact steps to install the RD98XS repeater in a rack or cabinet?",
            lambda a: "not explicitly" not in a.lower() and "1." in a),
    "Q18": ("Can the HR652 be used as a 5G base station backup link?",
            lambda a: "does not contain" in a.lower()),
}

for name, (q, ok) in CASES.items():
    print(f"\n{'='*58}\n{name}: {q[:48]}\n{'='*58}", flush=True)
    hashes, outcomes = [], []
    for i in range(5):
        clear()
        r = ask(q)
        ans = r["answer"]
        h = hashlib.md5(ans.encode()).hexdigest()[:8]
        good = ok(ans)
        hashes.append(h); outcomes.append(good)
        print(f"  {i+1}. hash={h} | product={r['detected_product']} | "
              f"type={r['query_type']} | {'PASS' if good else 'FAIL'}", flush=True)

    same_answer = len(set(hashes)) == 1
    print(f"\n  outcomes: {sum(outcomes)}/5 PASS", flush=True)
    print(f"  identical answers: {'✓ YES (deterministic)' if same_answer else '✗ NO — ' + str(len(set(hashes))) + ' distinct'}", flush=True)
