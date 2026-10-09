import requests, re, json, sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

BASE = "https://thunder-zone.coke2home.com"
headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"}

r = requests.get(BASE + "/game", headers=headers)

# Extract all chunk paths mentioned in self.__next_f
chunks_in_next_f = set(re.findall(r'\/_next\/static\/chunks\/[a-zA-Z0-9_\-\.]+\.js', r.text))
print(f"Found {len(chunks_in_next_f)} chunks inside Next.js payload: {chunks_in_next_f}")

for c in sorted(chunks_in_next_f):
    try:
        res = requests.get(BASE + c, headers=headers)
        if res.status_code == 200:
            for kw in ["thunder-trail/sessions", "socket_ticket", "frame_key", "live_mode", "WebSocket", "wss://"]:
                if kw in res.text:
                    print(f"\n🔥 MATCH in {c} for '{kw}':")
                    idx = 0
                    while True:
                        idx = res.text.find(kw, idx)
                        if idx == -1: break
                        print(res.text[max(0, idx-150):min(len(res.text), idx+350)])
                        print("-" * 50)
                        idx += len(kw) + 50
    except Exception as e:
        print(f"Err {c}: {e}")
