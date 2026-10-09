import json, os, sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HAR_PATH = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)\thunder-zone.coke2home.com.har"

print(f"Reading HAR file ({os.path.getsize(HAR_PATH) / 1024 / 1024:.2f} MB)...")
data = json.load(open(HAR_PATH, "r", encoding="utf-8"))

entries = data.get("log", {}).get("entries", [])
print(f"Total entries in HAR: {len(entries)}")

api_entries = []
ws_entries = []

for e in entries:
    req = e.get("request", {})
    res = e.get("response", {})
    url = req.get("url", "")
    method = req.get("method", "")
    status = res.get("status", 0)
    
    # Check for webSocket
    if "_webSocketMessages" in e or "ws" in url or "socket" in url:
        ws_entries.append((url, e.get("_webSocketMessages", [])))
    
    if "api/thunder-trail" in url or "api/auth" in url or "coke2home" in url:
        body = req.get("postData", {}).get("text", "")
        res_body = res.get("content", {}).get("text", "")
        api_entries.append({
            "method": method,
            "url": url,
            "status": status,
            "request_body": body[:300] if body else None,
            "response_body": res_body[:300] if res_body else None
        })

print("\n========================================================")
print(f"🔥 FOUND {len(api_entries)} COKE API REQUESTS IN HAR:")
print("========================================================")
for a in api_entries:
    print(f"[{a['method']}] {a['url']} -> HTTP {a['status']}")
    if a['request_body']:
        print(f"   REQ: {a['request_body']}")
    if a['response_body']:
        print(f"   RES: {a['response_body']}")
    print("-" * 50)

print("\n========================================================")
print(f"🔥 FOUND {len(ws_entries)} WEBSOCKET ENTRIES IN HAR:")
print("========================================================")
for url, msgs in ws_entries:
    print(f"WS URL: {url} | Messages: {len(msgs)}")
    for m in msgs[:10]:
        print(f"  -> {m}")
