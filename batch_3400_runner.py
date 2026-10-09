import json, os, sys, time, glob
from concurrent.futures import ThreadPoolExecutor, as_completed
import hightier_engine

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))

def process_account(phone_info):
    phone, plays, username = phone_info
    if plays <= 0:
        return None
    print(f"Starting 3400+ Target Run for Mobile: {phone} ({username})", flush=True)
    try:
        score, is_bot = hightier_engine.run_hightier_engine(phone, target_duration=105.0)
        return {"phone": phone, "username": username, "score": score, "is_bot": is_bot}
    except Exception as e:
        print(f"Error on {phone}: {e}", flush=True)
        return None

def main():
    session_files = glob.glob(os.path.join(HERE, ".session_*.json"))
    print(f"Found {len(session_files)} session files. Auditing active sessions...", flush=True)
    
    valid_sessions = []
    import requests
    BASE = "https://thunder-zone.coke2home.com"
    S = requests.Session()
    S.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Origin": BASE,
        "Referer": f"{BASE}/game"
    })

    for fpath in session_files:
        phone = os.path.basename(fpath).replace(".session_", "").replace(".json", "")
        try:
            cookies = json.load(open(fpath))
            if not cookies: continue
            S.cookies.clear()
            for c in cookies: S.cookies.set(c["name"], c["value"])
            r = S.get(BASE + "/api/thunder-trail/me", timeout=5)
            if r.status_code == 401:
                ref = S.post(BASE + "/api/auth/refresh", timeout=5)
                if ref.status_code == 200:
                    cookie_list = [{"name": c.name, "value": c.value} for c in S.cookies]
                    json.dump(cookie_list, open(fpath, "w"), indent=2)
                    r = S.get(BASE + "/api/thunder-trail/me", timeout=5)
            if r.status_code == 200 and r.json().get("success"):
                d = r.json().get("data", {})
                if not d.get("is_blocked") and d.get("plays_remaining", 0) > 0:
                    valid_sessions.append((phone, d.get("plays_remaining"), d.get("username", "N/A")))
        except Exception:
            pass

    print(f"\n========================================================")
    print(f"  FOUND {len(valid_sessions)} ACTIVE SESSIONS FOR 3400+ RUN")
    print(f"========================================================\n", flush=True)

    results = []
    # Running 3 parallel workers for smooth execution and avoiding IP rate limits
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_account, item) for item in valid_sessions]
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    print(f"\n========================================================")
    print(f"  3400+ BATCH COMPLETED ({len(results)} accounts processed)")
    print(f"========================================================", flush=True)
    for r in results:
        print(f"  Mobile: {r['phone']} | Score: {r['score']} | is_bot: {r['is_bot']}")

if __name__ == "__main__":
    main()
