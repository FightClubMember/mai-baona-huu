import glob, json, os, requests, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)"
other_dirs = [
    r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (3)",
    r"C:\Users\Himanshu Kumar\OneDrive\Desktop\h build bot",
    r"C:\Users\Himanshu Kumar\OneDrive\Desktop\test"
]

all_files = glob.glob(os.path.join(HERE, ".session_*.json"))
for d in other_dirs:
    if os.path.exists(d):
        all_files.extend(glob.glob(os.path.join(d, ".session_*.json")))
        all_files.extend(glob.glob(os.path.join(d, ".cookies_*.json")))

# Unique by phone
phone_map = {}
for f in all_files:
    p = os.path.basename(f).replace(".session_", "").replace(".cookies_", "").replace(".json", "")
    p_clean = "".join(c for c in p if c.isdigit())[-10:]
    if len(p_clean) == 10 and p_clean not in phone_map:
        phone_map[p_clean] = f

print(f"Total unique session files found: {len(phone_map)}")

def check_one(phone, fpath):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://thunder-zone.coke2home.com",
        "Referer": "https://thunder-zone.coke2home.com/game",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"
    })
    try:
        cookies = json.load(open(fpath))
        for c in cookies:
            s.cookies.set(c["name"], c["value"])
        r = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me", timeout=5)
        if r.status_code == 401:
            ref = s.post("https://thunder-zone.coke2home.com/api/auth/refresh", timeout=5)
            if ref.status_code == 200:
                cookie_list = [{"name": c.name, "value": c.value} for c in s.cookies]
                json.dump(cookie_list, open(os.path.join(HERE, f".session_{phone}.json"), "w"), indent=2)
                r = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me", timeout=5)
        if r.status_code == 200 and r.json().get("success"):
            d = r.json().get("data", {})
            if not d.get("is_blocked") and not d.get("is_locked") and d.get("plays_remaining", 0) > 0:
                # Copy active session to New folder (2) if it came from another folder
                dest = os.path.join(HERE, f".session_{phone}.json")
                if fpath != dest:
                    json.dump([{"name": c.name, "value": c.value} for c in s.cookies], open(dest, "w"), indent=2)
                print(f"🔥 ACTIVE: {phone} ({d.get('username')}) plays={d.get('plays_remaining')} best={d.get('best_score')}")
                return (phone, d.get("username"), d.get("plays_remaining"), d.get("best_score", 0))
    except Exception:
        pass
    return None

active = []
with ThreadPoolExecutor(max_workers=20) as ex:
    futures = {ex.submit(check_one, p, f): p for p, f in phone_map.items()}
    for f in as_completed(futures):
        res = f.result()
        if res:
            active.append(res)

print(f"\n==========================================================")
print(f"  TOTAL ACTIVE READY ACCOUNTS: {len(active)}")
print(f"==========================================================")

if active:
    json.dump(active, open(os.path.join(HERE, "valid_active_sessions.json"), "w"), indent=2)
    print("Saved to valid_active_sessions.json")
