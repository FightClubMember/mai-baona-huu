import requests, re, os, sys

BASE = "https://thunder-zone.coke2home.com"
headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"}

# Fetch the root HTML and all potential script/module URLs
r = requests.get(BASE + "/game", headers=headers)
scripts = set(re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', r.text))

# Also check for inline scripts in HTML
print(f"Total script files in HTML: {len(scripts)}")
inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"Total inline scripts in HTML: {len(inline_scripts)}")

for i, s in enumerate(inline_scripts):
    for kw in ["socket", "ws", "trail", "game", "session", "frame"]:
        if kw in s.lower():
            print(f"Inline script {i} contains '{kw}':\n{s[:300]}\n")

# Check all chunks
for s in scripts:
    url = s if s.startswith("http") else BASE + s
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            for kw in ["socket_ticket", "frame_key", "live_mode", "thunder-trail/sessions"]:
                if kw in res.text:
                    print(f"🔥 Found '{kw}' in {s}")
                    idx = 0
                    while True:
                        idx = res.text.find(kw, idx)
                        if idx == -1: break
                        print(f"  --> {res.text[max(0, idx-100):min(len(res.text), idx+300)]}\n")
                        idx += len(kw) + 50
    except Exception as e:
        print(f"Err {s}: {e}")
