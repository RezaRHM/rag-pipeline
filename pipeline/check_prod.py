from db.connection import get_qdrant
import config

qdrant = get_qdrant()
results, _ = qdrant.scroll(
    collection_name=config.QDRANT_COLLECTION,
    scroll_filter=None, limit=1200, with_payload=True
)

products = {}
for r in results:
    p = r.payload.get('product', 'NONE')
    products[p] = products.get(p, 0) + 1

print('Products in index:')
for p, count in products.items():
    print(f'  {count:4} | {p}')

print('\n3.1 Installation sections:')
for r in results:
    if '3.1 Installation' in r.payload.get('section', ''):
        lvl = r.payload['chunk_level']
        prod = r.payload['product']
        txt = r.payload['text'][:50]
        print(f'  [{lvl}] product={prod} | {txt}')
