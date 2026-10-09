import glob, os, json, requests

BASE = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))

def fast_audit():
    session_files = [f for f in glob.glob(os.path.join(HERE, ".session_*.json")) if os.path.getsize(f) > 100]
    print(f"==================================================")
    print(f"  FAST SESSION AUDITOR - Checking {len(session_files)} Sessions")
    print(f"==================================================\n")

    valid_sessions = []
    
    for idx, fpath in enumerate(session_files, 1):
        phone = os.path.basename(fpath).replace(".session_", "").replace(".json", "")
        
        S = requests.Session()
        S.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Origin": BASE,
            "Referer": f"{BASE}/game"
        })

        try:
            cookies = json.load(open(fpath))
            for c in cookies:
                S.cookies.set(c["name"], c["value"])
        except Exception:
            continue

        # Check me auth
        try:
            r = S.get(BASE + "/api/thunder-trail/me", timeout=5)
            if r.status_code == 401:
                # Try refresh
                ref = S.post(BASE + "/api/auth/refresh", timeout=5)
                if ref.status_code == 200:
                    # Update file
                    cookie_list = [{"name": c.name, "value": c.value} for c in S.cookies]
                    json.dump(cookie_list, open(fpath, "w"), indent=2)
                    r = S.get(BASE + "/api/thunder-trail/me", timeout=5)

            if r.status_code == 200 and r.json().get("success"):
                d = r.json().get("data", {})
                is_blocked = d.get("is_blocked", False)
                plays_rem = d.get("plays_remaining", 0)
                username = d.get("username", "N/A")

                if is_blocked:
                    status_str = "BLOCKED"
                elif plays_rem > 0:
                    status_str = f"READY ({plays_rem} plays left)"
                    valid_sessions.append((phone, plays_rem, username))
                else:
                    status_str = "0 plays left"

                print(f"[{idx:>3}/{len(session_files)}] Mobile: {phone} | User: {username:<12} | Status: {status_str}")
            else:
                print(f"[{idx:>3}/{len(session_files)}] Mobile: {phone} | Session Expired / Invalid")
        except Exception as e:
            print(f"[{idx:>3}/{len(session_files)}] Mobile: {phone} | Error: {e}")

    print("\n==================================================")
    print(f"  AUDIT COMPLETE: Found {len(valid_sessions)} Valid Sessions With Plays Remaining")
    print("==================================================")
    for p, pl, un in valid_sessions:
        print(f"  -> Mobile: {p} | Plays: {pl} | User: {un}")

    with open(os.path.join(HERE, "valid_active_sessions.json"), "w") as out:
        json.dump(valid_sessions, out, indent=2)

if __name__ == "__main__":
    fast_audit()
