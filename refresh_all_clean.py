import json, os, glob, requests

HERE = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)"
files = glob.glob(os.path.join(HERE, ".session_*.json"))

s = requests.Session()
s.headers.update({
    "Content-Type": "application/json",
    "Origin": "https://thunder-zone.coke2home.com",
    "Referer": "https://thunder-zone.coke2home.com/game",
    "User-Agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 Chrome/154.0.0.0 Mobile Safari/537.36"
})

valid_list = []
print(f"Testing and refreshing active tokens across {len(files)} accounts...")

for f in files:
    phone = os.path.basename(f).replace(".session_", "").replace(".json", "")
    try:
        cookies = json.load(open(f))
        s.cookies.clear()
        for c in cookies: s.cookies.set(c["name"], c["value"])
        
        # Force refresh to ensure live fresh token
        ref = s.post("https://thunder-zone.coke2home.com/api/auth/refresh", timeout=5)
        if ref.status_code == 200:
            json.dump([{"name": c.name, "value": c.value} for c in s.cookies], open(f, "w"), indent=2)
            
        r = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me", timeout=5)
        if r.status_code == 200:
            d = r.json().get("data", {})
            if not d.get("is_blocked") and not d.get("is_locked") and d.get("plays_remaining", 0) > 0:
                valid_list.append([phone, d.get("plays_remaining"), d.get("username")])
                print(f"🔥 FRESH READY: {phone} ({d.get('username')}) plays={d.get('plays_remaining')}")
    except Exception:
        pass

print(f"\nTotal valid refreshed clean accounts: {len(valid_list)}")
json.dump(valid_list, open(os.path.join(HERE, "fresh_valid_sessions.json"), "w"), indent=2)
