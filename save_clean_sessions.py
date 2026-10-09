import json, os, glob, requests

HERE = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)"
files = glob.glob(os.path.join(HERE, ".session_*.json"))

s = requests.Session()
s.headers.update({
    "Content-Type": "application/json",
    "Origin": "https://thunder-zone.coke2home.com",
    "Referer": "https://thunder-zone.coke2home.com/game",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"
})

clean = []
for f in files:
    phone = os.path.basename(f).replace(".session_", "").replace(".json", "")
    try:
        cookies = json.load(open(f))
        s.cookies.clear()
        for c in cookies: s.cookies.set(c["name"], c["value"])
        r = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me", timeout=3)
        if r.status_code == 200:
            d = r.json().get("data", {})
            if not d.get("is_blocked") and not d.get("is_locked") and d.get("plays_remaining", 0) > 0:
                clean.append([phone, d.get("plays_remaining"), d.get("username")])
    except Exception:
        pass

print(f"Total pure clean playable accounts saved: {len(clean)}")
json.dump(clean, open(os.path.join(HERE, "clean_unblocked_sessions.json"), "w"), indent=2)
