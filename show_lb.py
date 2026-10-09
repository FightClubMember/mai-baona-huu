import json, os, requests, sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
phone = "6201594939"

s = requests.Session()
s.headers.update({
    "Content-Type": "application/json",
    "Origin": "https://thunder-zone.coke2home.com",
    "Referer": "https://thunder-zone.coke2home.com/game",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"
})

for c in json.load(open(os.path.join(HERE, f".session_{phone}.json"))):
    s.cookies.set(c["name"], c["value"])

r = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/sub-leaderboard")
d = r.json().get("data", {})
entries = d.get("entries", [])

print("\n" + "=" * 50)
print("LIVE COKE THUNDER TRAIL TOP STANDINGS")
print("=" * 50)
for e in entries[:25]:
    print(f"Rank #{e.get('rank'):<3} | User: {e.get('username'):<14} | Score: {e.get('score')} pts")
print("=" * 50)
