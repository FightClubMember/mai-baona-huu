import glob, json, requests

BASE = "https://thunder-zone.coke2home.com"
files = sorted(glob.glob(".session_*.json"))

print(f"Scanning all {len(files)} session files sequentially...", flush=True)

winners_found = []

for fpath in files:
    phone = fpath.replace(".session_", "").replace(".json", "")
    try:
        cookies = json.load(open(fpath))
        if not cookies: continue
        cookie_dict = {c["name"]: c["value"] for c in cookies if "name" in c and "value" in c}
        s = requests.Session()
        s.headers.update({
            "accept": "*/*",
            "content-type": "application/json",
            "origin": BASE,
            "referer": f"{BASE}/game",
            "user-agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"
        })
        for k, v in cookie_dict.items(): s.cookies.set(k, v)

        # 1. Check /api/thunder-trail/me
        r = s.get(BASE + "/api/thunder-trail/me", timeout=5)
        if r.status_code == 401:
            ref = s.post(BASE + "/api/auth/refresh", timeout=5)
            if ref.status_code == 200:
                for c in s.cookies: cookie_dict[c.name] = c.value
                json.dump([{"name": k, "value": v} for k, v in cookie_dict.items()], open(fpath, "w"), indent=2)
                r = s.get(BASE + "/api/thunder-trail/me", timeout=5)

        if r.status_code == 200:
            d = r.json().get("data", {})
            is_winner = d.get("is_winner", False)

            # 2. Check /api/thunder-trail/my-rewards
            r_rew = s.get(BASE + "/api/thunder-trail/my-rewards", timeout=5)
            rew_data = {}
            if r_rew.status_code == 200:
                rew_data = r_rew.json().get("data", {})

            has_rewards = rew_data.get("has_rewards", False)
            rewards = rew_data.get("rewards", [])

            if is_winner or has_rewards or len(rewards) > 0:
                username = d.get("username", "N/A")
                score = d.get("best_score", 0)
                print(f"🏆 WINNER FOUND: Phone={phone} | User={username} | Score={score} | Rewards={len(rewards)}", flush=True)
                winners_found.append({
                    "phone": phone,
                    "username": username,
                    "score": score,
                    "is_winner": is_winner,
                    "rewards": rewards
                })
    except Exception:
        pass

print(f"\n==========================================================", flush=True)
print(f"  TOTAL WINNER ACCOUNTS FOUND IN DISK SESSIONS: {len(winners_found)}", flush=True)
print(f"==========================================================", flush=True)

with open("all_winners_found.json", "w") as out:
    json.dump(winners_found, out, indent=2)
