import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from db.connection import get_postgres
from main import ask

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

def warm_ollama():
    """Keep the model resident so a mid-run eviction doesn't distort timings."""
    requests.post("http://localhost:11434/api/generate",
                  json={"model": "llama3.1:8b", "prompt": "ok",
                        "keep_alive": "120m", "stream": False}, timeout=300)

QUESTIONS = [
    ("Q1  standard",    "RD98XS LEDs?"),
    ("Q2  clarify",     "Alarm meaning?"),
    ("Q8  procedural",  "What are the exact steps to install the RD98XS repeater in a rack or cabinet?"),
    ("Q11 comparison",  "What are the installation differences between the RD98XS and HR652?"),
    ("Q12 use_case",    "Which one is more suitable for a compact indoor site, RD98XS or HR652?"),
    ("Q16 adversarial", "How do I configure AES-256 encryption keys on the RD98XS using the CPS software?"),
]

warm_ollama()
clear()
print("warming pipeline (loads BM25 + reranker)...", flush=True)
t = time.time(); ask("test warm up query")
print(f"  warm-up: {time.time()-t:.0f}s\n", flush=True)

results = []
for name, q in QUESTIONS:
    clear()
    t0 = time.time()
    r = ask(q)
    dt = time.time() - t0
    results.append((name, dt))
    print(f"{name:18} {dt:6.1f}s   type={r['query_type']}", flush=True)

print("\n" + "=" * 52)
avg = sum(r[1] for r in results) / len(results)
print(f"average: {avg:.1f}s   →  20 questions ≈ {avg*20/60:.0f} min")
print("\nslowest:")
for name, dt in sorted(results, key=lambda x: -x[1])[:3]:
    print(f"  {name:18} {dt:.0f}s")
