import sys, os, json, glob, requests
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception: pass

files = glob.glob(".session_*.json")
print(f"Checking {len(files)} sessions concurrently...", flush=True)

playable = []
blocked = []
winners = []
zero_plays = []
failed = []

def check_one(f):
    phone = os.path.basename(f).replace(".session_", "").replace(".json", "")
    try:
        cookies = json.load(open(f))
    except:
        return ("err", phone, "invalid json")
    
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
        "user-agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36",
        "x-botd": "human"
    })
    
    try:
        r = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me", timeout=6)
        if r.status_code == 401:
            ref = s.post("https://thunder-zone.coke2home.com/api/auth/refresh", timeout=6)
            if ref.status_code == 200:
                for c in s.cookies:
                    cookie_dict[c.name] = c.value
                json.dump([{"name": k, "value": v} for k, v in cookie_dict.items()], open(f, "w"), indent=2)
                r = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me", timeout=6)
        
        if r.status_code == 200:
            d = r.json().get("data", {})
            username = d.get("username", "N/A")
            plays = d.get("plays_remaining", 0)
            is_winner = d.get("is_winner", False)
            is_blocked = d.get("is_blocked", False)
            
            if is_blocked:
                return ("blocked", phone, username)
            elif is_winner:
                return ("winner", phone, username, plays)
            elif plays > 0:
                return ("ready", phone, plays, username)
            else:
                return ("zero", phone, username)
        else:
            return ("fail", phone, r.status_code)
    except Exception as e:
        return ("err", phone, str(e))

with ThreadPoolExecutor(max_workers=10) as ex:
    results = list(ex.map(check_one, files))

for res in results:
    tag = res[0]
    if tag == "ready":
        _, p, pl, un = res
        playable.append((p, pl, un))
        print(f"[READY]   {p} ({un}) -> {pl} plays left", flush=True)
    elif tag == "blocked":
        _, p, un = res
        blocked.append((p, un))
        print(f"[BLOCKED] {p} ({un})", flush=True)
    elif tag == "winner":
        _, p, un, pl = res
        winners.append((p, un, pl))
        print(f"[WINNER]  {p} ({un}) -> {pl} plays", flush=True)
    elif tag == "zero":
        _, p, un = res
        zero_plays.append((p, un))
    else:
        failed.append(res)

print(f"\n================ SUMMARY ================", flush=True)
print(f"READY & Unblocked: {len(playable)}", flush=True)
print(f"Winners: {len(winners)}", flush=True)
print(f"Blocked: {len(blocked)}", flush=True)
print(f"0 Plays Remaining: {len(zero_plays)}", flush=True)
print(f"Failed / Expired: {len(failed)}", flush=True)

with open("playable_clean_sessions.json", "w") as out:
    json.dump(playable, out, indent=2)
print("Saved to playable_clean_sessions.json", flush=True)
