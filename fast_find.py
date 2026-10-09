import glob, os, json, requests

BASE = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))

def fast_find():
    files = sorted(glob.glob(os.path.join(HERE, ".session_*.json")), key=os.path.getmtime, reverse=True)
    print(f"Checking {len(files)} session files (newest first)...")
    
    S = requests.Session()
    S.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Origin": BASE,
        "Referer": f"{BASE}/game"
    })

    found = []
    for fpath in files:
        phone = os.path.basename(fpath).replace(".session_", "").replace(".json", "")
        try:
            cookies = json.load(open(fpath))
            if not cookies: continue
            S.cookies.clear()
            for c in cookies: S.cookies.set(c["name"], c["value"])
            
            r = S.get(BASE + "/api/thunder-trail/me", timeout=4)
            if r.status_code == 401:
                ref = S.post(BASE + "/api/auth/refresh", timeout=4)
                if ref.status_code == 200:
                    # Save refreshed session
                    cookie_list = [{"name": c.name, "value": c.value} for c in S.cookies]
                    json.dump(cookie_list, open(fpath, "w"), indent=2)
                    r = S.get(BASE + "/api/thunder-trail/me", timeout=4)
            
            if r.status_code == 200 and r.json().get("success"):
                d = r.json().get("data", {})
                if not d.get("is_blocked") and d.get("plays_remaining", 0) > 0:
                    print(f"READY SESSION FOUND: {phone} | Plays: {d.get('plays_remaining')} | User: {d.get('username')}")
                    found.append(phone)
                    if len(found) >= 5:
                        break
        except Exception:
            pass

    return found

if __name__ == "__main__":
    fast_find()
