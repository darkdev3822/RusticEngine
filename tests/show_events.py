"""Pretty-print rustic-agent JSON-line events from stdin."""
import sys, json
txt = ''
for l in sys.stdin:
    try:
        v = json.loads(l)
    except Exception:
        print('RAW', l.strip()); continue
    t = v['type']
    if t == 'text':
        txt += v['delta']; continue
    if txt.strip():
        print('TEXT:', txt.strip()[:900]); txt = ''
    print('  >', t, v.get('summary', ''), v.get('ok', ''), v.get('message', ''))
if txt.strip():
    print('TEXT:', txt.strip()[:1200])
