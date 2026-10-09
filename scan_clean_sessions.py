import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import requests, json, glob, os

files = glob.glob(".session_*.json")
print(f"Scanning {len(files)} session files...")

playable_sessions = []
blocked_sessions = []
winner_sessions = []

for f in files:
    phone = os.path.basename(f).replace(".session_", "").replace(".json", "")
    try:
        cookies = json.load(open(f))
    except:
        continue
    
    cookie_dict = {}
    for c in cookies:
        cookie_dict[c["name"]] = c["value"]
    
    s = requests.Session()
    for k, v in cookie_dict.items():
        s.cookies.set(k, v)
    
    s.headers.update({
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,hi;q=0.8",
        "content-type": "application/json",
        "origin": "https://thunder-zone.coke2home.com",
        "referer": "https://thunder-zone.coke2home.com/game?skipWin=1",
        "sec-ch-ua": '"Chromium";v="154", "Google Chrome";v="154", "Not A(Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36",
        "x-botd": "human"
    })
    
    try:
        r = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me", timeout=5)
        if r.status_code == 401:
            ref = s.post("https://thunder-zone.coke2home.com/api/auth/refresh", timeout=5)
            if ref.status_code == 200:
                for c in s.cookies:
                    cookie_dict[c.name] = c.value
                json.dump([{"name": k, "value": v} for k, v in cookie_dict.items()], open(f, "w"), indent=2)
                r = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me", timeout=5)
        
        if r.status_code == 200:
            d = r.json().get("data", {})
            username = d.get("username")
            plays = d.get("plays_remaining", 0)
            is_winner = d.get("is_winner", False)
            is_blocked = d.get("is_blocked", False)
            is_locked = d.get("is_locked", False)
            
            if is_blocked:
                blocked_sessions.append((phone, username, "blocked"))
                print(f"[BLOCKED] {phone} ({username}) -> Clause 6 T&C")
            elif is_winner:
                winner_sessions.append((phone, username, f"winner | plays: {plays}"))
                print(f"[WINNER]  {phone} ({username}) -> Winner! Plays: {plays}")
            elif is_locked:
                print(f"[LOCKED]  {phone} ({username})")
            elif plays > 0:
                playable_sessions.append((phone, plays, username))
                print(f"[READY]   {phone} ({username}) -> Plays: {plays}")
            else:
                print(f"[0 PLAYS] {phone} ({username})")
        else:
            print(f"[FAILED]  {phone} -> /me failed: {r.status_code}")
    except Exception as e:
        print(f"[ERROR]   {phone} -> {e}")

print(f"\n================ SUMMARY ================")
print(f"READY & Playable: {len(playable_sessions)}")
print(f"Winners: {len(winner_sessions)}")
print(f"Blocked: {len(blocked_sessions)}")

with open("playable_clean_sessions.json", "w") as out:
    json.dump(playable_sessions, out, indent=2)
