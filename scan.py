import glob, os, json, nabab

def find_ready():
    session_files = [f for f in glob.glob(".session_*.json") if os.path.getsize(f) > 100]
    print(f"Checking {len(session_files)} saved session files...")
    
    for f in session_files:
        phone = os.path.basename(f).replace(".session_", "").replace(".json", "")
        if nabab.load_session(phone):
            try:
                res = nabab.api("GET", "/api/thunder-trail/me").json()
                if res.get("success"):
                    d = res.get("data", {})
                    plays = d.get("plays_remaining", 0)
                    if plays > 0:
                        print(f"[FOUND] Mobile: {phone} | Plays Left: {plays} | Username: {d.get('username')}")
                        return phone
            except Exception:
                pass
    print("No available sessions with plays left found.")
    return None

if __name__ == "__main__":
    find_ready()
