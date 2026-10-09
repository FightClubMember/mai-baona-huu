import requests, re

BASE = "https://thunder-zone.coke2home.com"
headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"}

chunks = [
    "/_next/static/chunks/0vzuv7gvwt3qm.js",
    "/_next/static/chunks/3kg-i7a_08uf_.js",
    "/_next/static/chunks/2iprnspzp3xfm.js",
    "/_next/static/chunks/396mtptnw5lal.js",
    "/_next/static/chunks/0al3_g0f943vi.js",
    "/_next/static/chunks/2ywaesjr_v25c.js",
    "/_next/static/chunks/2-soe6ohulry3.js",
    "/_next/static/chunks/3j-84hlbcq1wo.js",
    "/_next/static/chunks/44kw6_zn8mxd7.js",
    "/_next/static/chunks/21iry_25cpmlq.js",
    "/_next/static/chunks/44ohy06m7ygm-.js",
    "/_next/static/chunks/0cz1d0mv5g_q7.js",
    "/_next/static/chunks/0eous8iilairc.js"
]

keywords = ["socket_ticket", "frame_key", "live_mode", "drip_enc", "thunder-trail", "WebSocket", "socket.io", "wss://", "heartbeat"]

for chunk in chunks:
    try:
        r = requests.get(BASE + chunk, headers=headers, timeout=10)
        if r.status_code == 200:
            found = [k for k in keywords if k in r.text]
            if found:
                print(f"File {chunk} matches: {found}")
                for k in found:
                    idx = r.text.find(k)
                    start = max(0, idx - 150)
                    end = min(len(r.text), idx + 250)
                    print(f"  [{k} context]: {r.text[start:end]}\n")
    except Exception as e:
        print(f"Err on {chunk}: {e}")
