import os
import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HERE = os.path.abspath(os.path.dirname(__file__))

def check_session(phone):
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://thunder-zone.coke2home.com",
    })
    
    try:
        with open(os.path.join(HERE, f".session_{phone}.json")) as f:
            cookies = json.load(f)
            for c in cookies:
                s.cookies.set(c["name"], c["value"], domain="thunder-zone.coke2home.com", path="/")
    except:
        return -1

    try:
        r = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me", timeout=10)
        if r.status_code == 200:
            return r.json().get("data", {}).get("plays_remaining", 0)
        elif r.status_code == 401:
            ref = s.post("https://thunder-zone.coke2home.com/api/auth/refresh", timeout=10)
            if ref.status_code == 200:
                r2 = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me", timeout=10)
                if r2.status_code == 200:
                    return r2.json().get("data", {}).get("plays_remaining", 0)
        elif r.status_code == 403:
            return -2
    except Exception as e:
        print(f"Error for {phone}: {e}")
    return -1

sessions = [f for f in os.listdir(HERE) if f.startswith(".session_") and f.endswith(".json")]
valid_with_plays = []
print(f"Scanning {len(sessions)} sessions (no proxy)...")
for sess in sessions:
    phone = sess.replace(".session_", "").replace(".json", "")
    plays = check_session(phone)
    if plays > 0:
        print(f"[SUCCESS] {phone} has {plays} plays left!")
        valid_with_plays.append((phone, plays))
    elif plays == 0:
        print(f"[EMPTY] {phone} has 0 plays left.")
    elif plays == -2:
        print(f"[BANNED 403] {phone}")
    else:
        print(f"[INVALID] {phone}")

print(f"\nFound {len(valid_with_plays)} sessions with plays left.")
with open("available_plays.json", "w") as f:
    json.dump(valid_with_plays, f)
