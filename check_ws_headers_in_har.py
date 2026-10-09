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
    req = e.get("request", {})
    if "thunder-trails/ws" in req.get("url", ""):
        print("🔥 EXACT WEBSOCKET REQUEST HEADERS FROM BROWSER:")
        for h in req.get("headers", []):
            print(f"  {h['name']}: {h['value']}")
