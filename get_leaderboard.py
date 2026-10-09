import glob, json, requests, os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://thunder-zone.coke2home.com"

def fetch_leaderboard():
    files = glob.glob(os.path.join(HERE, ".session_*.json"))
    print(f"Checking {len(files)} session files for active session...\n")

    S = requests.Session()
    S.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Origin": BASE,
        "Referer": f"{BASE}/game"
    })

    for fpath in files:
        try:
            cookies = json.load(open(fpath))
            if not cookies: continue
            S.cookies.clear()
            for c in cookies: S.cookies.set(c["name"], c["value"])
            
            r = S.get(BASE + "/api/thunder-trail/sub-leaderboard", timeout=5)
            if r.status_code == 401:
                ref = S.post(BASE + "/api/auth/refresh", timeout=5)
                if ref.status_code == 200:
                    cookie_list = [{"name": c.name, "value": c.value} for c in S.cookies]
                    json.dump(cookie_list, open(fpath, "w"), indent=2)
                    r = S.get(BASE + "/api/thunder-trail/sub-leaderboard", timeout=5)
            
            if r.status_code == 200 and r.json().get("success"):
                d = r.json().get("data", {})
                entries = d.get("entries") or []
                print("==========================================================")
                print("🏆 LIVE THUNDER TRAIL SUB-LEADERBOARD (TOP 25)")
                print("==========================================================")
                for idx, e in enumerate(entries[:25], 1):
                    rank = e.get("rank", idx)
                    username = e.get("username", "N/A")
                    score = e.get("score", 0)
                    print(f"  #{rank:>2}  |  User: {username:<16}  |  Score: {score}")
                print("==========================================================")
                print(f"Your Current Rank  : {d.get('me_rank')}")
                print(f"Your Current Score : {d.get('me_score')}")
                print("==========================================================")
                return True
        except Exception:
            pass
    print("Could not fetch leaderboard. All sessions expired.")
    return False

if __name__ == "__main__":
    fetch_leaderboard()
