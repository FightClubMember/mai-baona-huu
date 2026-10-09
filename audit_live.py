import glob, json, os, requests

BASE = "https://thunder-zone.coke2home.com"
valid_accounts = []

for fpath in glob.glob(".session_*.json"):
    phone = fpath.replace(".session_", "").replace(".json", "")
    try:
        raw_cookies = json.load(open(fpath))
    except:
        continue
    cookie_dict = {c["name"]: c["value"] for c in raw_cookies if "name" in c and "value" in c}
    s = requests.Session()
    s.headers.update({
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,hi;q=0.8",
        "content-type": "application/json",
        "origin": BASE,
        "referer": f"{BASE}/game?skipWin=1",
        "user-agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36",
        "x-botd": "human"
    })
    for k, v in cookie_dict.items():
        s.cookies.set(k, v)

    try:
        r = s.get(BASE + "/api/thunder-trail/me", timeout=5)
        if r.status_code == 401:
            ref = s.post(BASE + "/api/auth/refresh", timeout=5)
            if ref.status_code == 200:
                for c in s.cookies:
                    cookie_dict[c.name] = c.value
                json.dump([{"name": k, "value": v} for k, v in cookie_dict.items()], open(fpath, "w"), indent=2)
                r = s.get(BASE + "/api/thunder-trail/me", timeout=5)
                
        if r.status_code == 200:
            d = r.json().get("data", {})
            if not d.get("is_blocked", False) and d.get("plays_remaining", 0) > 0:
                valid_accounts.append({
                    "phone": phone,
                    "username": d.get("username"),
                    "plays_left": d.get("plays_remaining"),
                    "high_score": d.get("high_score", 0)
                })
    except:
        pass

print(f"Total LIVE VERIFIED ACTIVE accounts with plays: {len(valid_accounts)}")
for a in valid_accounts:
    print(f"  {a['phone']} ({a['username']}) | Plays: {a['plays_left']} | Score: {a['high_score']}")

with open("live_verified_playable.json", "w") as f:
    json.dump(valid_accounts, f, indent=2)
