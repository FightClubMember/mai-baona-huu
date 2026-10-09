"""
refresh_existing_sessions.py — Use stored refresh_token in .session_*.json to get fresh active access_token
"""
import json, os, glob, requests, sys

BASE = "https://thunder-zone.coke2home.com"
HERE = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)"
files = sorted(glob.glob(os.path.join(HERE, ".session_*.json")))

S = requests.Session()
S.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36",
    "Origin": BASE, "Referer": BASE + "/"
})

refreshed = []

print(f"Testing token refresh on {len(files)} existing session files...")

for fpath in files:
    phone = os.path.basename(fpath).replace(".session_","").replace(".json","")
    try:
        cookies = json.load(open(fpath))
        if not cookies or len(json.dumps(cookies)) < 100: continue
        S.cookies.clear()
        for c in cookies: S.cookies.set(c["name"], c["value"])

        # Try refresh
        ref = S.post(BASE + "/api/auth/refresh", timeout=5)
        if ref.status_code == 200:
            cookie_list = [{"name": c.name, "value": c.value} for c in S.cookies]
            json.dump(cookie_list, open(fpath, "w"), indent=2)

        # Check auth
        r = S.get(BASE + "/api/thunder-trail/me", timeout=5)
        if r.status_code == 200 and r.json().get("success"):
            d = r.json().get("data", {})
            plays = d.get("plays_remaining", 0)
            is_locked = d.get("is_locked", False)
            is_blocked = d.get("is_blocked", False)
            username = d.get("username", "N/A")
            score = d.get("best_score", 0)
            if not is_locked and not is_blocked and plays > 0:
                refreshed.append((phone, username, plays, score))
                print(f"🔥 REFRESH SUCCESS: {phone} ({username}) plays={plays} best={score}")
            else:
                print(f"⚠️ NO PLAYS/BLOCKED: {phone} plays={plays} locked={is_locked} blocked={is_blocked}")
        else:
            print(f"❌ EXPIRED: {phone}")
    except Exception:
        pass

print(f"\n==========================================================")
print(f"  TOTAL REFRESHED ACTIVE ACCOUNTS: {len(refreshed)}")
print(f"==========================================================")

if refreshed:
    json.dump(refreshed, open(os.path.join(HERE, "refreshed_active_sessions.json"), "w"), indent=2)
    print(f"Saved {len(refreshed)} refreshed active accounts to refreshed_active_sessions.json")
