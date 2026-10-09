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
        reveals = {}
        for m in msgs:
            d = json.loads(m.get('data','{}'))
            t = d.get('t')
            p = d.get('p',{})
            if t == 'reveal':
                reveals[p.get('box_id')] = m.get('time')
            elif t == 'swipe':
                bid = p.get('box_id')
                if bid in reveals:
                    diff_ms = (m.get('time') - reveals[bid]) * 1000
                    print(f"Box #{bid} Reveal -> Swipe Real Human Latency: {diff_ms:.1f}ms")
