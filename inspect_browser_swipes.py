import json, os, sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HAR_PATH = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)\thunder-zone.coke2home.com.har"
data = json.load(open(HAR_PATH, "r", encoding="utf-8"))
entries = data.get("log", {}).get("entries", [])

for e in entries:
    if "_webSocketMessages" in e:
        msgs = e["_webSocketMessages"]
        swipes = []
        for m in msgs:
            if m.get('type') == 'send' and '"t":"swipe"' in m.get('data',''):
                swipes.append(json.loads(m.get('data')))
        
        print(f"Total swipes sent by real browser in HAR: {len(swipes)}")
        for idx, s in enumerate(swipes[:20]):
            ts = s.get('ts')
            p = s.get('p',{})
            print(f"Swipe #{idx+1}: Box={p.get('box_id')} | Dir={p.get('dir')} | ClientAtMs={p.get('client_at_ms')} | Ts={ts}")
