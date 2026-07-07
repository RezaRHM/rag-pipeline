from db.connection import get_qdrant
import config

qdrant = get_qdrant()
results, _ = qdrant.scroll(
    collection_name=config.QDRANT_COLLECTION,
    scroll_filter=None,
    limit=1200,
    with_payload=True
)

children = [r for r in results if r.payload.get('chunk_level') == 'child']

print('=== Suspicious table-derived children ===')
count = 0
for c in children:
    text = c.payload.get('text', '')
    if ('<!-- image -->' in text or
        (len(text.split()) <= 5 and any(u in text.lower()
         for u in ['dbm', 'mhz', 'ip6', 'ip5', '°c', 'dc']))):
        print(f'  [{c.payload["section"][:30]}] {text[:70]}')
        count += 1
    if count >= 15:
        break
print(f'\nTotal suspicious shown: {count}')
