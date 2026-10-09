import json, os, requests

BASE = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))

# Test on 1 account: 6201594939
phone = "6201594939"

s = requests.Session()
s.headers.update({
    "Content-Type": "application/json",
    "Origin": BASE,
    "Referer": f"{BASE}/game",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"
})

fpath = os.path.join(HERE, f".session_{phone}.json")
for c in json.load(open(fpath)):
    s.cookies.set(c["name"], c["value"])

print(f"Creating game session for {phone}...")
r = s.post(BASE + "/api/thunder-trail/sessions", json={}, timeout=10)
print("Session status:", r.status_code)
d = r.json()
print("Session payload:", json.dumps(d, indent=2))
