import json, os, sys, requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

BASE = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))

def check_leaderboard_directly(phone="6261642928"):
    fpath = os.path.join(HERE, f".session_{phone}.json")
    if not os.path.exists(fpath):
        print(f"Session file not found for {phone}")
        return

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
        for c in cookies: S.cookies.set(c["name"], c["value"])

        # Auth check
        me_resp = S.get(BASE + "/api/thunder-trail/me", timeout=10)
        if me_resp.status_code == 401:
            ref = S.post(BASE + "/api/auth/refresh", timeout=10)
            if ref.status_code == 200:
                cookie_list = [{"name": c.name, "value": c.value} for c in S.cookies]
                json.dump(cookie_list, open(fpath, "w"), indent=2)
                me_resp = S.get(BASE + "/api/thunder-trail/me", timeout=10)

        print(f"[Auth Status] {me_resp.status_code} | User: {me_resp.json().get('data',{}).get('username')}")

        # Sub-leaderboard check
        lb_resp = S.get(BASE + "/api/thunder-trail/sub-leaderboard", timeout=10)
        print(f"[Leaderboard Status] {lb_resp.status_code}")
        if lb_resp.status_code == 200 and lb_resp.json().get("success"):
            d = lb_resp.json().get("data", {})
            entries = d.get("entries") or []
            print("\n" + "="*55)
            print("  LIVE SUB-LEADERBOARD TOP 25 PLACEMENTS")
            print("="*55)
            for idx, e in enumerate(entries[:25], 1):
                me_flag = " <=== YOU" if e.get("is_me") else ""
                print(f"  #{e.get('rank', idx):>2} | User: {e.get('username','N/A'):<16} | Score: {e.get('score')}{me_flag}")
            print("-"*55)
            print(f"  Your Current Rank  : {d.get('me_rank')}")
            print(f"  Your Current Score : {d.get('me_score')}")
            print("="*55)
        else:
            print(f"Leaderboard fetch error: {lb_resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "9201021048"
    check_leaderboard_directly(p)
