import requests, re

BASE = "https://thunder-zone.coke2home.com"
headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"}

r = requests.get(BASE + "/game", headers=headers)
all_js = re.findall(r'/_next/static/[^\"]+\.js', r.text)

print(f"Found {len(all_js)} static js paths in HTML")

# Check manifest or search all js chunks
keywords = ["socket_ticket", "frame_key", "live_mode", "sessions", "heartbeat", "journey", "score"]

matched = {}
for path in set(all_js):
    try:
        res = requests.get(BASE + path, headers=headers, timeout=10)
        if res.status_code == 200:
            found = [k for k in keywords if k in res.text]
            if found:
                print(f"Chunk {path}: matches {found}")
                for k in ["socket_ticket", "frame_key", "live_mode", "/api/thunder-trail"]:
                    if k in res.text:
                        idx = 0
                        while True:
                            idx = res.text.find(k, idx)
                            if idx == -1: break
                            snippet = res.text[max(0, idx-100):min(len(res.text), idx+200)]
                            print(f"  --> [{k}]: {snippet}\n")
                            idx += len(k)
    except Exception as e:
        print(f"Error {path}: {e}")
