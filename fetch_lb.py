import json, os, glob, requests

BASE = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))
files = glob.glob(os.path.join(HERE, ".session_*.json"))

S = requests.Session()
S.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": BASE,
    "Referer": f"{BASE}/game",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
})

fetched = False
for fpath in files:
    try:
        cookies = json.load(open(fpath))
        if not cookies: continue
        S.cookies.clear()
        for c in cookies: S.cookies.set(c["name"], c["value"])
        
        me_resp = S.get(BASE + "/api/thunder-trail/me", timeout=8)
        if me_resp.status_code == 401:
            ref = S.post(BASE + "/api/auth/refresh", timeout=8)
            if ref.status_code == 200:
                cookie_list = [{"name": c.name, "value": c.value} for c in S.cookies]
                json.dump(cookie_list, open(fpath, "w"), indent=2)
                me_resp = S.get(BASE + "/api/thunder-trail/me", timeout=8)

        if me_resp.status_code == 200:
            lb_resp = S.get(BASE + "/api/thunder-trail/sub-leaderboard", timeout=8)
            if lb_resp.status_code == 200 and lb_resp.json().get("success"):
                d = lb_resp.json().get("data", {})
                entries = d.get("entries") or []
                print("=" * 65)
                print("🏆 LIVE SUB-LEADERBOARD TOP 25 STANDINGS")
                print("=" * 65)
                print(f"  {'Rank':>5} | {'Username':<18} | {'Score':>8}")
                print("  " + "-" * 50)
                for idx, e in enumerate(entries[:25], 1):
                    me_flag = " <=== YOUR ACCOUNT" if e.get("is_me") else ""
                    rank_num = e.get("rank", idx)
                    uname = e.get("username", "N/A")
                    sc = e.get("score")
                    print(f"  #{rank_num:>4} | {uname:<18} | {sc:>8}{me_flag}")
                print("=" * 65)
                print(f"  Your Current Rank  : #{d.get('me_rank')}")
                print(f"  Your Current Score : {d.get('me_score')}")
                print("=" * 65)
                fetched = True
                break
    except Exception as e:
        pass

if not fetched:
    print("Could not fetch leaderboard using active session files.")
