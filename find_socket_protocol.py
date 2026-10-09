import requests, re, os

BASE = "https://thunder-zone.coke2home.com"
headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"}

# 1. Fetch game page
r = requests.get(BASE + "/game", headers=headers)
print("Game page fetch:", r.status_code)

# 2. Extract all script URLs
scripts = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', r.text)
print(f"Found {len(scripts)} scripts in HTML")

# 3. Search for socket, websocket, and frame_key keywords
keywords = ["socket_ticket", "frame_key", "live_mode", "WebSocket", "socket.io", "wss:", "ws:", "new WebSocket", "io("]

found_chunks = []
for s in set(scripts):
    url = s if s.startswith("http") else BASE + s
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            matches = [k for k in keywords if k in res.text]
            if matches:
                print(f"🔥 Found matches in {s}: {matches}")
                found_chunks.append((s, res.text))
    except Exception as e:
        print(f"Err {s}: {e}")

# 4. Deep search in chunks
for name, content in found_chunks:
    print(f"\n==================================================")
    print(f"Inspecting: {name}")
    print(f"==================================================")
    for kw in ["socket_ticket", "frame_key", "live_mode", "WebSocket", "socket"]:
        pos = 0
        while True:
            pos = content.find(kw, pos)
            if pos == -1: break
            snippet = content[max(0, pos-150):min(len(content), pos+300)]
            print(f"---> [{kw}]:\n{snippet}\n")
            pos += len(kw)
