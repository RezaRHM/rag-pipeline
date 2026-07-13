import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.connection import get_postgres
import main as M
from retrieval.retriever import hybrid_search, add_heading_parents

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

# monkeypatch add_heading_parents تا ببینیم ورودی/خروجی
orig = M.add_heading_parents
def traced(final_chunks, heading_hits, **kw):
    print(f"\n--- add_heading_parents ---")
    print(f"kwargs: {kw}")
    print(f"final_chunks IN ({len(final_chunks)}): {[c.payload.get('section','?')[:20] for c in final_chunks]}")
    print(f"heading_hits ({len(heading_hits)}):")
    for h in heading_hits:
        print(f"   [{float(h.score):.3f}] {h.payload.get('section','?')[:26]}")
    result = orig(final_chunks, heading_hits, **kw)
    print(f"final_chunks OUT ({len(result)}): {[c.payload.get('section','?')[:20] for c in result]}")
    return result
M.add_heading_parents = traced

clear()
r = M.process_query("RD98XS box contents?")
print(f"\nFINAL: {[c.payload.get('section','?')[:22] for c in r['chunks']]}")
