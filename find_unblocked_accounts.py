"""
find_unblocked_accounts.py — Find accounts that are 100% active & not blocked under Clause 6
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

clean_accounts = []

print(f"Auditing {len(files)} session files for Clause 6 block status...")

for fpath in files:
    phone = os.path.basename(fpath).replace(".session_","").replace(".json","")
    try:
        cookies = json.load(open(fpath))
        if not cookies or len(json.dumps(cookies)) < 100: continue
        S.cookies.clear()
        for c in cookies: S.cookies.set(c["name"], c["value"])

        # Check /me
        r = S.get(BASE + "/api/thunder-trail/me", timeout=5)
        if r.status_code == 401:
            ref = S.post(BASE + "/api/auth/refresh", timeout=5)
            if ref.status_code == 200:
                cookie_list = [{"name": c.name, "value": c.value} for c in S.cookies]
                json.dump(cookie_list, open(fpath, "w"), indent=2)
                r = S.get(BASE + "/api/thunder-trail/me", timeout=5)

        if r.status_code != 200: continue
        me = r.json().get("data", {})
        if me.get("is_blocked") or me.get("is_locked"): continue
        plays = me.get("plays_remaining", 0)
        if plays <= 0: continue

        # Test session create to verify Clause 6 status
        sr = S.post(BASE + "/api/thunder-trail/sessions", json={}, timeout=6)
        if sr.status_code in (200, 201):
            clean_accounts.append((phone, me.get("username", "N/A"), plays, me.get("best_score", 0)))
            print(f"✅ UNBLOCKED CLEAN: {phone} ({me.get('username')}) plays={plays} best={me.get('best_score')}")
        else:
            err_text = sr.text[:100]
            if "Clause 6" in err_text:
                print(f"🚫 CLAUSE 6 BLOCKED: {phone}")
            else:
                print(f"⚠️ SESSION FAIL: {phone} -> {err_text}")
    except Exception as e:
        pass

print(f"\n==========================================================")
print(f"  TOTAL UNBLOCKED CLEAN ACCOUNTS READY: {len(clean_accounts)}")
print(f"==========================================================")

if clean_accounts:
    json.dump(clean_accounts, open(os.path.join(HERE, "clean_unblocked_sessions.json"), "w"), indent=2)
    print(f"Saved {len(clean_accounts)} clean accounts to clean_unblocked_sessions.json")
