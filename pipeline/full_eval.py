from main import ask
import json

questions = [
    ('Q1',  'RD98XS LEDs?'),
    ('Q2',  'Alarm meaning?'),
    ('Q3',  'Power issue'),
    ('Q4',  'How do I install it and check if the antenna connection is correct?'),
    ('Q5',  'The repeater has an alarm and the LED is flashing, what should I check first?'),
    ('Q6',  'What are the exact operating temperature and storage temperature ranges for the RD98XS?'),
    ('Q7',  'What does each front-panel LED state mean on the HR652?'),
    ('Q8',  'What are the exact steps to install the RD98XS repeater in a rack or cabinet?'),
    ('Q9',  'Which alarm conditions can be triggered by abnormal voltage, overheating, or fan failure on the RD98XS?'),
    ('Q10', 'What voltage or power supply requirements are listed for the HR652 repeater?'),
    ('Q11', 'What are the main installation differences between the RD98XS and HR652 repeaters?'),
    ('Q12', 'Which repeater is more suitable for a compact indoor site in the Netherlands, RD98XS or HR652?'),
    ('Q13', 'Do both RD98XS and HR652 support the same DMR features listed in the Hytera professional catalog?'),
    ('Q14', 'Which accessories or optional components from the catalog are relevant for deploying these repeaters?'),
    ('Q15', 'Compare the troubleshooting guidance for no transmission or poor coverage between RD98XS and HR652.'),
    ('Q16', 'How do I configure AES-256 encryption keys on the RD98XS using the CPS software?'),
    ('Q17', 'What is the alarm code E47 on the Hytera RD99XS repeater?'),
    ('Q18', 'Can the HR652 be used as a 5G base station backup link?'),
    ('Q19', 'What is the default admin password for the RD98XS web interface?'),
    ('Q20', 'How do I waterproof the RD98XS for permanent outdoor pole mounting in heavy rain?'),
]

results = []
for qid, q in questions:
    print(f'\n{"="*70}', flush=True)
    print(f'{qid}: {q}', flush=True)
    print("="*70, flush=True)
    try:
        r = ask(q)
        ans = r['answer']
        qtype = r.get('query_type', '?')
    except Exception as e:
        ans = f'ERROR: {e}'
        qtype = 'error'
    print(f'[type={qtype}]', flush=True)
    print(ans, flush=True)

    results.append({'id': qid, 'type': qtype, 'question': q, 'answer': ans})
    # incremental save — اگه وسط کار قطع شد، نتیجه‌ها بمونن
    with open('evaluation/full_eval_hierarchical.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

print(f'\n\nDONE. Saved {len(results)} results.', flush=True)
