from main import ask

questions = [
    'What is the operating temperature of the RD982S?',
    'What voltage does the HR652 require?',
    'What does error code H5 mean?',
    'What does alarm E1 mean?',
    'How to ground the repeater?',
    'duplexer installation steps',
    'What does the LED indicator show on the HR652?',
]

for q in questions:
    r = ask(q)
    top = r['chunks'][0] if r['chunks'] else None
    score = top.payload.get('rerank_score', 0) if top else 0
    sec = top.payload['section'][:32] if top else 'none'
    print(f'[{score:.3f}] {sec:34} | {q[:40]}')
