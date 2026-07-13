
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_postgres

from main import process_query

import retrieval.retriever as R

def clear():

    pg = get_postgres(); cur = pg.cursor()

    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

# monkeypatch تا candidates را قبل و بعد merge ببینیم

orig_merge = R.merge_with_preserved

def traced_merge(reranked, candidates, **kw):

    print("\n--- inside merge_with_preserved ---")

    print(f"detected_product arg: {kw.get('detected_product')!r}")

    flagged = [c for c in candidates if c.payload.get("_guaranteed_top1")]

    print(f"candidates total: {len(candidates)}, flagged _guaranteed_top1: {len(flagged)}")

    for c in flagged:

        prod = c.payload.get("product","?")[:20]

        sec = c.payload.get("section","?")[:34]

        print(f"   FLAGGED: [{prod}] {sec}")

    pl = [c for c in candidates if "product layout" in c.payload.get("section","").lower()]

    print(f"Product Layout in candidates: {len(pl)}")

    for c in pl:

        print(f"   PL: flagged={c.payload.get('_guaranteed_top1', False)} "

              f"section={c.payload.get('section','?')[:30]}")

    rr_pl = [i for i,c in enumerate(reranked) if "product layout" in c.payload.get("section","").lower()]

    print(f"Product Layout in reranked: positions {rr_pl}")

    result = orig_merge(reranked, candidates, **kw)

    res_pl = [i for i,c in enumerate(result) if "product layout" in c.payload.get("section","").lower()]

    print(f"Product Layout in merged result: positions {res_pl}")

    print(f"merged result size: {len(result)}")

    return result

R.merge_with_preserved = traced_merge

import main

main.merge_with_preserved = traced_merge

clear()

r = process_query("What is on the front panel of the HR652?")

print("\n=== FINAL ===")

print(f"detected_product: {r.get('detected_product')!r}")

print(f"final sections: {[c.payload.get('section','?')[:26] for c in r['chunks']]}")

