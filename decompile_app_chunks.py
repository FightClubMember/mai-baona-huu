import requests, re, os, sys

BASE = "https://thunder-zone.coke2home.com"
headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"}

# The 4 main application chunks identified in Turbopack
app_chunks = [
    "/_next/static/chunks/0vzuv7gvwt3qm.js",
    "/_next/static/chunks/3kg-i7a_08uf_.js",
    "/_next/static/chunks/0eous8iilairc.js",
    "/_next/static/chunks/2iprnspzp3xfm.js"
]

for c in app_chunks:
    try:
        r = requests.get(BASE + c, headers=headers)
        if r.status_code == 200:
            print(f"\nChunk: {c} (Size: {len(r.text)} bytes)")
            apis = set(re.findall(r'\/api\/[a-zA-Z0-9_\-\/]+', r.text))
            print(f"  APIs: {apis}")
            
            for word in ["socket_ticket", "frame_key", "live_mode", "sessions", "heartbeat", "journey", "score"]:
                if word in r.text:
                    pos = 0
                    while True:
                        pos = r.text.find(word, pos)
                        if pos == -1: break
                        snip = r.text[max(0, pos-120):min(len(r.text), pos+300)]
                        print(f"  --> [{word}]:\n{snip}\n")
                        pos += len(word) + 80
    except Exception as e:
        print(f"Error {c}: {e}")
