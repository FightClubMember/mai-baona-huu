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
        print(f"Total WebSocket messages in browser game: {len(msgs)}")
        print("\nFirst 10 messages:")
        for m in msgs[:10]:
            print(f"[{m.get('type')}] {m.get('data')}")
            
        print("\nLast 15 messages:")
        for m in msgs[-15:]:
            print(f"[{m.get('type')}] {m.get('data')}")
