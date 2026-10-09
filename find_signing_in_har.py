import json, os, sys, re

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HAR_PATH = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)\thunder-zone.coke2home.com.har"
data = json.load(open(HAR_PATH, "r", encoding="utf-8"))
entries = data.get("log", {}).get("entries", [])

print("Searching JS files in HAR for WebSocket and MAC signing code...")
for e in entries:
    req = e.get("request", {})
    res = e.get("response", {})
    url = req.get("url", "")
    if ".js" in url:
        text = res.get("content", {}).get("text", "")
        if "thunder-trails/ws" in text or "socket_ticket" in text:
            print(f"\nFOUND GAME ENGINE JS: {url} (Size: {len(text)})")
            for kw in ["thunder-trails/ws", "socket_ticket", "frame_key", "hello", "swipe", "mac"]:
                pos = 0
                while True:
                    pos = text.find(kw, pos)
                    if pos == -1: break
                    print(f"  [{kw}]:\n{text[max(0, pos-120):min(len(res.get('content',{}).get('text','')), pos+350)]}\n")
                    pos += len(kw) + 150
