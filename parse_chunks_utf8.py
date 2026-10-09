import requests, re, os, sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

BASE = "https://thunder-zone.coke2home.com"
headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"}

r = requests.get(BASE + "/game", headers=headers)
scripts = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', r.text)

keywords = ["socket_ticket", "frame_key", "live_mode", "WebSocket", "socket.io", "wss:", "ws:", "new WebSocket", "heartbeat", "/api/thunder-trail"]

for s in set(scripts):
    url = s if s.startswith("http") else BASE + s
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            found = [k for k in keywords if k in res.text]
            if found:
                print(f"\n==================================================")
                print(f"File: {s} | Matches: {found}")
                print(f"==================================================")
                for kw in found:
                    idx = 0
                    while True:
                        idx = res.text.find(kw, idx)
                        if idx == -1: break
                        snippet = res.text[max(0, idx-100):min(len(res.text), idx+250)]
                        print(f"---> [{kw}]:\n{snippet}\n")
                        idx += len(kw) + 50
    except Exception as e:
        print(f"Err {s}: {e}")
