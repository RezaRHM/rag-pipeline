from db.connection import get_qdrant
import config

qdrant = get_qdrant()
results, _ = qdrant.scroll(
    collection_name=config.QDRANT_COLLECTION,
    scroll_filter=None, limit=1200, with_payload=True
)

print('=== Children with "temperature" in RD98XS ===')
found = 0
for r in results:
    if r.payload.get('chunk_level') == 'child':
        text = r.payload.get('text', '').lower()
        product = r.payload.get('product', '')
        if 'temperature' in text and 'RD98' in product:
            print(f'  [{r.payload[\"section\"][:30]}] {r.payload[\"text\"][:75]}')
            found += 1

print(f'\nFound: {found}')

# چک کن آیا section 3.1 اصلاً هست
print('\n=== Is 3.1 Installation Requirements still there? ===')
for r in results:
    if '3.1 Installation' in r.payload.get('section','') and 'RD98' in r.payload.get('product',''):
        print(f'  [{r.payload[\"chunk_level\"]}] {r.payload[\"section\"]}: {r.payload[\"text\"][:70]}')
