from db.connection import get_qdrant
import config

qdrant = get_qdrant()
results, _ = qdrant.scroll(
    collection_name=config.QDRANT_COLLECTION,
    scroll_filter=None, limit=1200, with_payload=True
)
children = [r for r in results if r.payload.get('chunk_level') == 'child']

image_noise = sum(1 for c in children if '<!-- image -->' in c.payload.get('text',''))
tiny = sum(1 for c in children if len(c.payload.get('text','').split()) <= 4)

print(f'Total children: {len(children)}')
print(f'With <!-- image -->: {image_noise}')
print(f'Tiny (<=4 words): {tiny}')
