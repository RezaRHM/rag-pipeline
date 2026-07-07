from query.query_analyzer import analyze_query
for q in ['What voltage does the HR652 require?',
          'What does the LED indicator show on the HR652?']:
    r = analyze_query(q)
    print(f'{r["product"]!r} | {q[:40]}')
